#!/usr/bin/env python3
"""
Yahoo Finance Japan 年初来高値更新銘柄取得スクリプト
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
import re
from typing import List, Dict, Optional


class YahooFinanceJapanScraper:
    def __init__(self):
        self.base_url = "https://finance.yahoo.co.jp/stocks/ranking/yearToDateHigh"
        self.api_base = "https://finance.yahoo.co.jp/_store_api/ranking"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
            'Referer': 'https://finance.yahoo.co.jp/',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_api_data(self, page: int = 1, market: str = "all", term: str = "daily") -> Optional[Dict]:
        """
        APIから株式ランキングデータを取得

        Args:
            page: ページ番号 (デフォルト: 1)
            market: 市場 (all, tokyo, mothers, jasdaq, etc.)
            term: 期間 (daily, weekly, monthly)

        Returns:
            JSONデータまたはNone
        """
        # APIエンドポイントを試行
        api_urls = [
            f"{self.api_base}/yearToDateHigh",
            f"https://finance.yahoo.co.jp/api/ranking/yearToDateHigh",
            f"https://finance.yahoo.co.jp/_api/ranking/yearToDateHigh"
        ]

        params = {
            'market': market,
            'term': term,
            'page': page,
            'size': 50
        }

        for api_url in api_urls:
            try:
                print(f"API URL: {api_url} を試行中...")
                response = self.session.get(api_url, params=params)
                print(f"ステータス: {response.status_code}")

                if response.status_code == 200:
                    try:
                        data = response.json()
                        print("JSONデータの取得に成功")
                        return data
                    except json.JSONDecodeError:
                        print("JSONデコードエラー - HTMLが返されている可能性があります")
                        print(f"レスポンス内容の先頭: {response.text[:200]}")
                        continue

            except requests.RequestException as e:
                print(f"リクエストエラー: {e}")
                continue

        return None

    def get_page_data(self, page: int = 1, market: str = "all", term: str = "daily") -> Optional[str]:
        """
        指定されたページのHTMLデータを取得

        Args:
            page: ページ番号 (デフォルト: 1)
            market: 市場 (all, tokyo, mothers, jasdaq, etc.)
            term: 期間 (daily, weekly, monthly)

        Returns:
            HTMLコンテンツまたはNone
        """
        params = {
            'market': market,
            'term': term,
            'page': page
        }

        try:
            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()
            print(f"レスポンスステータス: {response.status_code}")
            print(f"レスポンス長: {len(response.text)} 文字")
            return response.text
        except requests.RequestException as e:
            print(f"エラー: ページ {page} の取得に失敗しました - {e}")
            return None

    def parse_stock_data(self, html_content: str) -> List[Dict]:
        """
        HTMLから株式データを抽出

        Args:
            html_content: HTMLコンテンツ

        Returns:
            株式データのリスト
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        stocks = []

        # ランキングテーブルを検索
        ranking_table = soup.find('table', class_='rankingTable')
        if not ranking_table:
            # 別のクラス名やセレクタを試す
            ranking_table = soup.find('table')
            if not ranking_table:
                print("ランキングテーブルが見つかりません")
                # デバッグ用: 全てのテーブル要素を確認
                all_tables = soup.find_all('table')
                print(f"見つかったテーブル数: {len(all_tables)}")
                for i, table in enumerate(all_tables[:3]):  # 最初の3つのテーブルだけ確認
                    print(f"テーブル{i+1}: {table.get('class', 'クラスなし')}")
                return stocks

        # テーブル行を取得
        rows = ranking_table.find('tbody').find_all('tr') if ranking_table.find('tbody') else ranking_table.find_all('tr')

        for i, row in enumerate(rows):
            try:
                cells = row.find_all('td')
                if len(cells) < 3:  # 最低限のセル数チェック
                    continue

                # 順位を取得
                rank_text = cells[0].get_text(strip=True)
                if not rank_text.isdigit():
                    continue

                rank = int(rank_text)

                # 銘柄情報を取得
                stock_info_cell = cells[1]

                # 銘柄リンクを探す
                stock_link = stock_info_cell.find('a')
                if not stock_link:
                    continue

                stock_name = stock_link.get_text(strip=True)
                href = stock_link.get('href', '')

                # 株式コードを抽出
                code_match = re.search(r'code=([^&]+)', href) or re.search(r'/detail/([^/?]+)', href)
                stock_code = code_match.group(1) if code_match else ''

                # 市場情報を取得
                market_span = stock_info_cell.find('span')
                market = market_span.get_text(strip=True) if market_span else ''

                # その他のデータ (価格情報など) を取得
                additional_data = {}
                for j, cell in enumerate(cells[2:], 2):
                    cell_text = cell.get_text(strip=True)
                    if j == 2:
                        additional_data['value'] = cell_text
                    elif j == 3:
                        additional_data['price'] = cell_text
                    elif j == 4:
                        additional_data['change'] = cell_text

                stock_data = {
                    'rank': rank,
                    'stock_code': stock_code,
                    'stock_name': stock_name,
                    'market': market,
                    'url': f"https://finance.yahoo.co.jp{href}" if href.startswith('/') else href,
                    **additional_data
                }

                stocks.append(stock_data)

                if i < 5:  # 最初の5つの結果をデバッグ出力
                    print(f"株式データ {i+1}: {stock_data}")

            except Exception as e:
                print(f"行 {i+1} の解析中にエラー: {e}")
                continue

        return stocks

    def get_all_stocks(self, max_pages: int = 10, market: str = "all", term: str = "daily") -> List[Dict]:
        """
        全ページから株式データを取得

        Args:
            max_pages: 取得する最大ページ数
            market: 市場
            term: 期間

        Returns:
            全株式データのリスト
        """
        all_stocks = []

        for page in range(1, max_pages + 1):
            print(f"ページ {page} を取得中...")

            html_content = self.get_page_data(page, market, term)
            if not html_content:
                print(f"ページ {page} の取得に失敗しました")
                break

            page_stocks = self.parse_stock_data(html_content)
            if not page_stocks:
                print(f"ページ {page} にデータがありません。取得を終了します。")
                break

            all_stocks.extend(page_stocks)
            print(f"ページ {page}: {len(page_stocks)} 銘柄を取得")

            # レート制限のため少し待機
            time.sleep(1)

        return all_stocks

    def save_to_csv(self, stocks: List[Dict], filename: str = "yahoo_finance_ytd_highs.csv") -> None:
        """
        株式データをCSVファイルに保存

        Args:
            stocks: 株式データのリスト
            filename: 保存ファイル名
        """
        if not stocks:
            print("保存するデータがありません")
            return

        import os
        # workディレクトリが存在しない場合は作成
        os.makedirs("work", exist_ok=True)

        # workディレクトリ内にファイルを保存
        filepath = os.path.join("work", filename)

        df = pd.DataFrame(stocks)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"データを {filepath} に保存しました ({len(stocks)} 銘柄)")

    def print_summary(self, stocks: List[Dict]) -> None:
        """
        取得した株式データの要約を表示

        Args:
            stocks: 株式データのリスト
        """
        if not stocks:
            print("データがありません")
            return

        print(f"\n=== 年初来高値更新銘柄 取得結果 ===")
        print(f"総銘柄数: {len(stocks)}")

        # 市場別集計
        markets = {}
        for stock in stocks:
            market = stock.get('market', '不明')
            markets[market] = markets.get(market, 0) + 1

        print(f"\n市場別内訳:")
        for market, count in sorted(markets.items(), key=lambda x: x[1], reverse=True):
            print(f"  {market}: {count} 銘柄")

        print(f"\n上位10銘柄:")
        for i, stock in enumerate(stocks[:10], 1):
            print(f"  {i:2d}. {stock['stock_code']} {stock['stock_name']} ({stock['market']})")


def main():
    """
    メイン実行関数
    """
    scraper = YahooFinanceJapanScraper()

    print("Yahoo Finance Japan 年初来高値更新銘柄を取得中...")

    # APIでデータ取得を試行
    print("APIエンドポイントを試行中...")
    api_data = scraper.get_api_data(1, "all", "daily")

    if api_data:
        print("APIからデータを取得しました")
        print(json.dumps(api_data, indent=2, ensure_ascii=False)[:1000])
        return

    # HTMLスクレイピングを試行
    print("HTMLスクレイピングを試行中...")
    stocks = scraper.get_all_stocks(max_pages=5, market="all", term="daily")

    if stocks:
        # 結果表示
        scraper.print_summary(stocks)

        # CSVファイルに保存
        scraper.save_to_csv(stocks)

        print(f"\n取得完了: {len(stocks)} 銘柄")
    else:
        print("データの取得に失敗しました")


if __name__ == "__main__":
    main()