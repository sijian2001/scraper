#!/usr/bin/env python3
"""
Yahoo Finance Japan ストップ安銘柄取得スクリプト
日々の値幅制限下限（ストップ安）に達した銘柄を取得・分析
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
import re
from typing import List, Dict, Optional
from datetime import datetime
import os


class StopLowScraper:
    def __init__(self):
        self.base_url = "https://finance.yahoo.co.jp/stocks/ranking/stopLow"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Referer': 'https://finance.yahoo.co.jp/',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_stop_low_stocks(self, pages: int = 5, market: str = "all", term: str = "daily") -> List[Dict]:
        """
        ストップ安銘柄を取得

        Args:
            pages: 取得するページ数
            market: 市場 (all, tokyo, mothers, jasdaq, etc.)
            term: 期間 (daily, weekly, monthly)

        Returns:
            ストップ安銘柄データのリスト
        """
        all_stocks = []

        for page in range(1, pages + 1):
            print(f"ページ {page}/{pages} を処理中...")

            page_stocks = self._scrape_page(page, market, term)

            if not page_stocks:
                print(f"ページ {page} にデータが見つかりません。取得を終了します。")
                break

            all_stocks.extend(page_stocks)
            print(f"ページ {page}: {len(page_stocks)} 銘柄を取得")

            # レート制限のため少し待機
            time.sleep(1)

        return all_stocks

    def _scrape_page(self, page: int, market: str, term: str) -> List[Dict]:
        """
        指定されたページからストップ安銘柄を取得

        Args:
            page: ページ番号
            market: 市場
            term: 期間

        Returns:
            ページの銘柄データリスト
        """
        params = {
            'market': market,
            'term': term,
            'page': page
        }

        try:
            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            return self._parse_stock_data(soup)

        except requests.RequestException as e:
            print(f"ページ {page} の取得でエラー: {e}")
            return []

    def _parse_stock_data(self, soup: BeautifulSoup) -> List[Dict]:
        """
        HTMLからストップ安銘柄データを抽出

        Args:
            soup: BeautifulSoupオブジェクト

        Returns:
            銘柄データのリスト
        """
        stocks = []

        # 複数のセレクタパターンを試行
        selectors = [
            'div[data-module="RankingResult"] table tr',
            'table.rankingTable tr',
            'table tr',
            'div.RankingResult table tr',
            '[data-ranking] tr'
        ]

        rows = []
        for selector in selectors:
            rows = soup.select(selector)
            if rows and len(rows) > 1:  # ヘッダー行以外にデータがある
                print(f"使用したセレクタ: {selector}")
                break

        if not rows:
            print("データ行が見つかりません")
            # デバッグ用: テーブルの存在確認
            all_tables = soup.find_all('table')
            print(f"見つかったテーブル数: {len(all_tables)}")
            return stocks

        # ヘッダー行をスキップしてデータ行を処理
        for i, row in enumerate(rows[1:], 1):
            try:
                stock_data = self._parse_stock_row(row, i)
                if stock_data:
                    stocks.append(stock_data)

                    # 最初の5つの結果をデバッグ出力
                    if i <= 5:
                        print(f"取得した銘柄 {i}: {stock_data}")

            except Exception as e:
                print(f"行 {i} の処理中にエラー: {e}")
                continue

        return stocks

    def _parse_stock_row(self, row, row_index: int) -> Optional[Dict]:
        """
        テーブル行から銘柄データを抽出

        Args:
            row: BeautifulSoupのtr要素
            row_index: 行のインデックス

        Returns:
            銘柄データ辞書またはNone
        """
        cells = row.find_all(['td', 'th'])
        if len(cells) < 3:
            return None

        # 順位を取得
        rank_text = cells[0].get_text(strip=True).replace('.', '')
        if not rank_text.isdigit():
            return None

        rank = int(rank_text)

        # 銘柄情報セル
        stock_cell = cells[1]
        link = stock_cell.find('a')

        if not link:
            return None

        stock_name = link.get_text(strip=True)
        href = link.get('href', '')

        # 銘柄コードを抽出
        stock_code = self._extract_stock_code(href, stock_cell, row_index)

        # 市場情報を取得
        market_span = stock_cell.find('span')
        market = market_span.get_text(strip=True) if market_span else "不明"

        # 価格・ストップ安関連データを取得
        price_data = self._extract_price_data(cells[2:])

        # URL構築
        stock_url = f"https://finance.yahoo.co.jp{href}" if href.startswith('/') else href

        return {
            'rank': rank,
            'stock_code': stock_code,
            'stock_name': stock_name,
            'market': market,
            'url': stock_url,
            'scrape_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            **price_data
        }

    def _extract_stock_code(self, href: str, stock_cell, row_index: int) -> str:
        """
        銘柄コードを抽出

        Args:
            href: リンクのhref属性
            stock_cell: 銘柄情報セル
            row_index: 行インデックス

        Returns:
            銘柄コード
        """
        # URLから銘柄コードを抽出
        code_match = re.search(r'code=([^&]+)', href)
        if not code_match:
            code_match = re.search(r'/quote/([^/?]+)', href)

        if code_match:
            return code_match.group(1).replace('.T', '')
        else:
            # セル内から直接コードを探す
            cell_text = stock_cell.get_text()
            code_match = re.search(r'(\d{4})', cell_text)
            return code_match.group(1) if code_match else f"UNKNOWN_{row_index}"

    def _extract_price_data(self, price_cells) -> Dict:
        """
        価格関連データを抽出

        Args:
            price_cells: 価格データを含むセルのリスト

        Returns:
            価格データ辞書
        """
        price_data = {}

        for j, cell in enumerate(price_cells):
            cell_text = cell.get_text(strip=True)

            if j == 0:
                price_data['current_price'] = cell_text
            elif j == 1:
                price_data['change_value'] = cell_text
            elif j == 2:
                price_data['change_rate'] = cell_text
            elif j == 3:
                price_data['volume'] = cell_text
            elif j == 4:
                price_data['additional_info'] = cell_text

        return price_data

    def save_to_csv(self, stocks: List[Dict], filename: str = "stop_low_stocks.csv") -> None:
        """
        ストップ安銘柄データをCSVファイルに保存

        Args:
            stocks: 銘柄データのリスト
            filename: 保存ファイル名
        """
        if not stocks:
            print("保存するデータがありません")
            return

        # workディレクトリが存在しない場合は作成
        os.makedirs("work", exist_ok=True)

        # workディレクトリ内にファイルを保存
        filepath = os.path.join("work", filename)

        df = pd.DataFrame(stocks)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"データを {filepath} に保存しました ({len(stocks)} 銘柄)")

    def print_summary(self, stocks: List[Dict]) -> None:
        """
        取得したストップ安銘柄の要約を表示

        Args:
            stocks: 銘柄データのリスト
        """
        if not stocks:
            print("データがありません")
            return

        print(f"\n=== ストップ安銘柄 取得結果 ===")
        print(f"総銘柄数: {len(stocks)}")
        print(f"取得日時: {stocks[0].get('scrape_date', 'N/A')}")

        # 市場別集計
        markets = {}
        for stock in stocks:
            market = stock.get('market', '不明')
            markets[market] = markets.get(market, 0) + 1

        print(f"\n市場別内訳:")
        for market, count in sorted(markets.items(), key=lambda x: x[1], reverse=True):
            print(f"  {market}: {count} 銘柄")

        print(f"\nストップ安銘柄一覧 (上位10銘柄):")
        for i, stock in enumerate(stocks[:10], 1):
            print(f"  {i:2d}. [{stock['stock_code']}] {stock['stock_name']} ({stock['market']})")
            if 'current_price' in stock:
                print(f"      現在値: {stock['current_price']}")
            if 'change_rate' in stock:
                print(f"      変化率: {stock['change_rate']}")

    def analyze_stop_low_patterns(self, stocks: List[Dict]) -> Dict:
        """
        ストップ安銘柄のパターン分析

        Args:
            stocks: 銘柄データのリスト

        Returns:
            分析結果辞書
        """
        if not stocks:
            return {}

        analysis = {
            'total_count': len(stocks),
            'market_distribution': {},
            'sector_patterns': {},
            'volume_analysis': {},
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # 市場別分析
        for stock in stocks:
            market = stock.get('market', '不明')
            analysis['market_distribution'][market] = analysis['market_distribution'].get(market, 0) + 1

        # ボリューム分析（データが利用可能な場合）
        volume_data = []
        for stock in stocks:
            volume_str = stock.get('volume', '').replace(',', '').replace('株', '')
            try:
                if volume_str.isdigit():
                    volume_data.append(int(volume_str))
            except:
                continue

        if volume_data:
            analysis['volume_analysis'] = {
                'average_volume': sum(volume_data) / len(volume_data),
                'max_volume': max(volume_data),
                'min_volume': min(volume_data),
                'sample_size': len(volume_data)
            }

        return analysis

    def print_analysis_report(self, analysis: Dict) -> None:
        """
        分析レポートを表示

        Args:
            analysis: 分析結果辞書
        """
        if not analysis:
            print("分析データがありません")
            return

        print(f"\n=== ストップ安銘柄 分析レポート ===")
        print(f"分析日時: {analysis.get('timestamp', 'N/A')}")
        print(f"対象銘柄数: {analysis.get('total_count', 0)}")

        # 市場別分析
        market_dist = analysis.get('market_distribution', {})
        if market_dist:
            print(f"\n市場別ストップ安発生状況:")
            for market, count in sorted(market_dist.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / analysis['total_count']) * 100
                print(f"  {market}: {count} 銘柄 ({percentage:.1f}%)")

        # ボリューム分析
        volume_analysis = analysis.get('volume_analysis', {})
        if volume_analysis:
            print(f"\n出来高分析:")
            print(f"  平均出来高: {volume_analysis['average_volume']:,.0f} 株")
            print(f"  最大出来高: {volume_analysis['max_volume']:,.0f} 株")
            print(f"  最小出来高: {volume_analysis['min_volume']:,.0f} 株")
            print(f"  サンプル数: {volume_analysis['sample_size']} 銘柄")


def main():
    """
    メイン実行関数
    """
    scraper = StopLowScraper()

    print("Yahoo Finance Japan ストップ安銘柄を取得中...")

    # ストップ安銘柄を取得
    stocks = scraper.get_stop_low_stocks(pages=3, market="all", term="daily")

    if stocks:
        # 結果表示
        scraper.print_summary(stocks)

        # CSVファイルに保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"stop_low_stocks_{timestamp}.csv"
        scraper.save_to_csv(stocks, filename)

        # 分析実行
        analysis = scraper.analyze_stop_low_patterns(stocks)
        scraper.print_analysis_report(analysis)

        print(f"\n取得完了: {len(stocks)} 銘柄のストップ安データを取得しました")
    else:
        print("ストップ安銘柄データの取得に失敗しました")
        print("注意: Yahoo Financeのページ構造が変更された可能性があります")


if __name__ == "__main__":
    main()