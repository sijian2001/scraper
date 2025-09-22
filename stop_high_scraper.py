#!/usr/bin/env python3
"""
Yahoo Finance Japan ストップ高銘柄取得スクリプト
Yahoo Finance Japan のストップ高ランキングページからデータを取得する
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
import re
from typing import List, Dict, Optional


class StopHighScraper:
    def __init__(self):
        self.base_url = "https://finance.yahoo.co.jp/stocks/ranking/stopHigh"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_stop_high_stocks(
        self, market: str = "all", term: str = "daily", page: int = 1
    ) -> List[Dict]:
        """
        ストップ高銘柄を取得

        Args:
            market: 市場指定 ("all", "tokyo", "osaka", etc.)
            term: 期間指定 ("daily", "weekly", "monthly")
            page: ページ番号
        """
        params = {"market": market, "term": term, "page": page}

        try:
            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()

            # JSON データの抽出を試みる
            stocks_from_json = self._extract_from_json(response.text)
            if stocks_from_json:
                return stocks_from_json

            # HTML パースの代替手段
            return self._extract_from_html(response.text)

        except Exception as e:
            print(f"ページ取得エラー: {e}")
            return []

    def _extract_from_json(self, html_content: str) -> List[Dict]:
        """
        HTML内のJSONデータからストップ高銘柄を抽出
        """
        try:
            # mainRankingList を含むJSONデータを検索
            json_pattern = r"window\.mainRankingList\s*=\s*({.*?});"
            json_match = re.search(json_pattern, html_content, re.DOTALL)

            if not json_match:
                # 他のパターンを試す
                json_pattern = r'"mainRankingList"\s*:\s*({.*?})'
                json_match = re.search(json_pattern, html_content, re.DOTALL)

            if json_match:
                json_data = json.loads(json_match.group(1))
                return self._parse_ranking_data(json_data)

        except Exception as e:
            print(f"JSON抽出エラー: {e}")

        return []

    def _parse_ranking_data(self, json_data: Dict) -> List[Dict]:
        """
        JSONランキングデータからストップ高銘柄リストを生成
        """
        stocks = []

        try:
            results = json_data.get("results", [])

            for i, result in enumerate(results, 1):
                try:
                    stock_data = {
                        "rank": i,
                        "stock_code": result.get("stockCode", ""),
                        "stock_name": result.get("stockName", ""),
                        "market": result.get("marketName", ""),
                        "current_price": result.get("savePrice", ""),
                        "yahoo_url": f"https://finance.yahoo.co.jp/quote/{result.get('stockCode', '')}",
                    }

                    # 価格変動情報
                    ranking_result = result.get("rankingResult", {})
                    stop_price = ranking_result.get("stopPrice", {})

                    if stop_price:
                        stock_data.update(
                            {
                                "price_change": stop_price.get("changePrice", ""),
                                "price_change_rate": stop_price.get(
                                    "changePriceRate", ""
                                ),
                                "previous_close": stop_price.get("previousClose", ""),
                            }
                        )

                    stocks.append(stock_data)

                except Exception as e:
                    print(f"株式データ {i} の処理中にエラー: {e}")
                    continue

        except Exception as e:
            print(f"ランキングデータの解析エラー: {e}")

        return stocks

    def _extract_from_html(self, html_content: str) -> List[Dict]:
        """
        HTMLテーブルからストップ高銘柄を抽出
        """
        soup = BeautifulSoup(html_content, "html.parser")
        stocks = []

        # 複数のセレクタパターンを試す
        selectors = [
            'div[data-module="RankingResult"] table tr',
            "table.rankingTable tr",
            "table tr",
            "div.RankingResult table tr",
            "[data-ranking] tr",
            ".rankingTable tr",
        ]

        rows = []
        for selector in selectors:
            rows = soup.select(selector)
            if rows and len(rows) > 1:
                print(f"使用したHTMLセレクタ: {selector}")
                break

        if not rows:
            print("HTMLテーブルからデータ行が見つかりません")
            return stocks

        for i, row in enumerate(rows[1:], 1):  # ヘッダー行をスキップ
            try:
                cells = row.find_all(["td", "th"])
                if len(cells) < 3:
                    continue

                # 順位
                rank_text = cells[0].get_text(strip=True)
                if not rank_text.replace(".", "").isdigit():
                    continue

                rank = int(rank_text.replace(".", ""))

                # 銘柄情報セル
                stock_cell = cells[1]
                link = stock_cell.find("a")
                if not link:
                    continue

                stock_name = link.get_text(strip=True)
                href = link.get("href", "")

                # 株式コードを抽出
                code_match = re.search(r"code=([^&]+)", href)
                if not code_match:
                    code_match = re.search(r"/quote/([^/?]+)", href)

                if code_match:
                    stock_code = code_match.group(1)
                else:
                    code_text = stock_cell.get_text()
                    code_match = re.search(r"(\d{4})", code_text)
                    stock_code = code_match.group(1) if code_match else f"UNK{i}"

                # 市場情報
                market_elem = stock_cell.find("span")
                market = market_elem.get_text(strip=True) if market_elem else "不明"

                # 価格情報
                price_info = {}
                for j, cell in enumerate(cells[2:], 2):
                    cell_text = cell.get_text(strip=True)
                    if j == 2:
                        price_info["current_price"] = cell_text
                    elif j == 3:
                        price_info["price_change"] = cell_text
                    elif j == 4:
                        price_info["price_change_rate"] = cell_text

                stock_data = {
                    "rank": rank,
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "market": market,
                    "yahoo_url": (
                        f"https://finance.yahoo.co.jp{href}"
                        if href.startswith("/")
                        else href
                    ),
                    **price_info,
                }

                stocks.append(stock_data)

                if i <= 5:  # 最初の5つをデバッグ出力
                    print(f"取得したストップ高株式 {i}: {stock_data}")

            except Exception as e:
                print(f"行 {i} の処理中にエラー: {e}")
                continue

        return stocks

    def get_multiple_pages(
        self, market: str = "all", term: str = "daily", max_pages: int = 3
    ) -> List[Dict]:
        """
        複数ページからストップ高銘柄を取得
        """
        all_stocks = []

        for page in range(1, max_pages + 1):
            print(f"ページ {page} を取得中...")

            stocks = self.get_stop_high_stocks(market=market, term=term, page=page)

            if not stocks:
                print(f"ページ {page} でデータが見つかりませんでした")
                break

            all_stocks.extend(stocks)
            print(f"ページ {page}: {len(stocks)} 銘柄を取得")

            # リクエスト間隔を空ける
            if page < max_pages:
                time.sleep(1)

        return all_stocks

    def save_to_csv(
        self, stocks: List[Dict], filename: str = "stop_high_stocks.csv"
    ) -> None:
        """
        ストップ高銘柄データをCSVファイルに保存
        """
        if not stocks:
            print("保存するデータがありません")
            return

        import os

        os.makedirs("work", exist_ok=True)
        filepath = os.path.join("work", filename)

        df = pd.DataFrame(stocks)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        print(f"データを {filepath} に保存しました ({len(stocks)} 銘柄)")

    def print_summary(self, stocks: List[Dict]) -> None:
        """
        取得したストップ高銘柄データの要約を表示
        """
        if not stocks:
            print("データがありません")
            return

        print(f"\n=== ストップ高銘柄 取得結果 ===")
        print(f"総銘柄数: {len(stocks)}")

        # 市場別集計
        market_counts = {}
        for stock in stocks:
            market = stock.get("market", "不明")
            market_counts[market] = market_counts.get(market, 0) + 1

        print(f"\n市場別内訳:")
        for market, count in sorted(market_counts.items()):
            print(f"  {market}: {count} 銘柄")

        print(f"\n取得した銘柄:")
        for i, stock in enumerate(stocks[:20], 1):  # 上位20銘柄を表示
            price_change = stock.get("price_change", "N/A")
            price_change_rate = stock.get("price_change_rate", "N/A")
            price_info = (
                f"({price_change} {price_change_rate})" if price_change != "N/A" else ""
            )

            print(
                f"  {i:2d}. [{stock.get('stock_code', 'N/A')}] {stock.get('stock_name', 'N/A')} ({stock.get('market', 'N/A')}) {price_info}"
            )

        if len(stocks) > 20:
            print(f"  ... 他 {len(stocks) - 20} 銘柄")


def main():
    """
    メイン実行関数
    """
    scraper = StopHighScraper()

    print("Yahoo Finance Japan ストップ高銘柄を取得中...")

    # ストップ高銘柄を取得
    stocks = scraper.get_stop_high_stocks(market="all", term="daily", page=1)

    if stocks:
        # 結果表示
        scraper.print_summary(stocks)

        # CSVファイルに保存
        scraper.save_to_csv(stocks)

        print(f"\n取得完了: {len(stocks)} 銘柄")
    else:
        print("ストップ高銘柄の取得に失敗しました")
        print("以下の要因が考えられます:")
        print("- Yahoo Finance Japan のHTML構造が変更された")
        print("- ネットワークエラー")
        print("- アクセス制限")

    # 複数ページの取得例（オプション）
    if stocks:
        print("\n=== 複数ページ取得の例 ===")
        choice = input("複数ページからデータを取得しますか？ (y/N): ").lower()
        if choice == "y":
            all_stocks = scraper.get_multiple_pages(max_pages=3)
            if all_stocks:
                scraper.print_summary(all_stocks)
                scraper.save_to_csv(all_stocks, "stop_high_stocks_all_pages.csv")


if __name__ == "__main__":
    main()
