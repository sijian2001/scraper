#!/usr/bin/env python3
"""
Yahoo Finance Japan 年初来高値更新銘柄取得スクリプト (簡易版)
yfinanceライブラリとWebスクレイピングを組み合わせた実装
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
import re
from typing import List, Dict, Optional


class SimpleYahooFinanceJapanScraper:
    def __init__(self):
        self.base_url = "https://finance.yahoo.co.jp/stocks/ranking/yearToDateHigh"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_stocks_from_html(self, page: int = 1) -> List[Dict]:
        """
        HTMLから年初来高値更新銘柄を抽出
        """
        params = {'market': 'all', 'term': 'daily', 'page': page}

        try:
            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            stocks = []

            # 異なるセレクタパターンを試す
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
                return stocks

            for i, row in enumerate(rows[1:], 1):  # ヘッダー行をスキップ
                try:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) < 3:
                        continue

                    # 順位
                    rank_text = cells[0].get_text(strip=True)
                    if not rank_text.replace('.', '').isdigit():
                        continue

                    rank = int(rank_text.replace('.', ''))

                    # 銘柄情報セル
                    stock_cell = cells[1]

                    # リンクを探す
                    link = stock_cell.find('a')
                    if not link:
                        continue

                    stock_name = link.get_text(strip=True)
                    href = link.get('href', '')

                    # 株式コードを抽出
                    code_match = re.search(r'code=([^&]+)', href)
                    if not code_match:
                        code_match = re.search(r'/detail/([^/?]+)', href)

                    if code_match:
                        stock_code = code_match.group(1)
                    else:
                        # セル内でコードを直接探す
                        code_text = stock_cell.get_text()
                        code_match = re.search(r'(\d{4})', code_text)
                        stock_code = code_match.group(1) if code_match else f"UNK{i}"

                    # 市場情報
                    market_elem = stock_cell.find('span')
                    market = market_elem.get_text(strip=True) if market_elem else "不明"

                    # 価格情報 (利用可能な場合)
                    price_info = {}
                    for j, cell in enumerate(cells[2:], 2):
                        cell_text = cell.get_text(strip=True)
                        if j == 2:
                            price_info['value1'] = cell_text
                        elif j == 3:
                            price_info['value2'] = cell_text
                        elif j == 4:
                            price_info['value3'] = cell_text

                    stock_data = {
                        'rank': rank,
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'market': market,
                        'url': f"https://finance.yahoo.co.jp{href}" if href.startswith('/') else href,
                        **price_info
                    }

                    stocks.append(stock_data)

                    if i <= 5:  # 最初の5つをデバッグ出力
                        print(f"取得した株式 {i}: {stock_data}")

                except Exception as e:
                    print(f"行 {i} の処理中にエラー: {e}")
                    continue

            return stocks

        except Exception as e:
            print(f"ページ取得エラー: {e}")
            return []

    def get_popular_japanese_stocks(self) -> List[Dict]:
        """
        人気の日本株リストを取得 (代替手段)
        """
        popular_stocks = [
            {'code': '7203', 'name': 'トヨタ自動車'},
            {'code': '9984', 'name': 'ソフトバンクグループ'},
            {'code': '6758', 'name': 'ソニーグループ'},
            {'code': '8306', 'name': '三菱UFJフィナンシャル・グループ'},
            {'code': '6861', 'name': 'キーエンス'},
            {'code': '7974', 'name': '任天堂'},
            {'code': '4063', 'name': '信越化学工業'},
            {'code': '8035', 'name': '東京エレクトロン'},
            {'code': '6954', 'name': 'ファナック'},
            {'code': '4502', 'name': '武田薬品工業'},
        ]

        return popular_stocks

    def save_to_csv(self, stocks: List[Dict], filename: str = "yahoo_finance_ytd_highs.csv") -> None:
        """
        株式データをCSVファイルに保存
        """
        if not stocks:
            print("保存するデータがありません")
            return

        df = pd.DataFrame(stocks)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"データを {filename} に保存しました ({len(stocks)} 銘柄)")

    def print_summary(self, stocks: List[Dict]) -> None:
        """
        取得した株式データの要約を表示
        """
        if not stocks:
            print("データがありません")
            return

        print(f"\n=== 年初来高値更新銘柄 取得結果 ===")
        print(f"総銘柄数: {len(stocks)}")

        print(f"\n取得した銘柄:")
        for i, stock in enumerate(stocks, 1):
            print(f"  {i:2d}. [{stock.get('stock_code', 'N/A')}] {stock.get('stock_name', 'N/A')} ({stock.get('market', 'N/A')})")


def main():
    """
    メイン実行関数
    """
    scraper = SimpleYahooFinanceJapanScraper()

    print("Yahoo Finance Japan 年初来高値更新銘柄を取得中...")

    # 年初来高値更新銘柄を取得
    stocks = scraper.get_stocks_from_html(page=1)

    if stocks:
        # 結果表示
        scraper.print_summary(stocks)

        # CSVファイルに保存
        scraper.save_to_csv(stocks)

        print(f"\n取得完了: {len(stocks)} 銘柄")
    else:
        print("直接スクレイピングに失敗しました。代替データを使用します。")

        # 代替データを使用
        popular_stocks = scraper.get_popular_japanese_stocks()
        print(f"\n人気の日本株リスト ({len(popular_stocks)} 銘柄):")
        for i, stock in enumerate(popular_stocks, 1):
            print(f"  {i:2d}. [{stock['code']}] {stock['name']}")

        scraper.save_to_csv(popular_stocks, "popular_japanese_stocks.csv")

        print("\n注意: Yahoo Financeの実際のランキングデータの取得には、")
        print("より高度なスクレイピング手法（Selenium等）が必要な場合があります。")


if __name__ == "__main__":
    main()