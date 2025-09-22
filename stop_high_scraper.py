#!/usr/bin/env python3
"""
Yahoo Finance Japan ストップ高銘柄取得スクリプト
Yahoo Finance Japan のストップ高ランキングページからデータを取得する
"""

import logging
import os
import time
import json
import re
from typing import List, Dict, Optional
from datetime import datetime

import requests
from bs4 import BeautifulSoup
import pandas as pd


class StopHighScraperError(Exception):
    """ストップ高スクレイパーのベース例外クラス"""

    pass


class ValidationError(StopHighScraperError):
    """入力バリデーションエラー"""

    pass


class NetworkError(StopHighScraperError):
    """ネットワークエラー"""

    pass


class DataParsingError(StopHighScraperError):
    """データ解析エラー"""

    pass


class StopHighScraper:
    # 定数定義
    DEBUG_OUTPUT_LIMIT = 5
    DISPLAY_LIMIT = 20
    DEFAULT_MAX_PAGES = 3

    VALID_MARKETS = ["all", "tokyo", "osaka", "nagoya", "sapporo", "fukuoka"]
    VALID_TERMS = ["daily", "weekly", "monthly"]

    def __init__(
        self,
        request_delay: float = 1.0,
        timeout: int = 30,
        logger: Optional[logging.Logger] = None,
    ):
        """
        StopHighScraperの初期化

        Args:
            request_delay: リクエスト間の待機時間（秒）
            timeout: HTTPリクエストのタイムアウト（秒）
            logger: ロガーインスタンス（None の場合は新規作成）
        """
        self.base_url = "https://finance.yahoo.co.jp/stocks/ranking/stopHigh"
        self.request_delay = request_delay
        self.timeout = timeout

        # ロガーの設定
        self.logger = logger or self._setup_logger()

        # パフォーマンス監視用
        self.performance_stats = {
            "requests_made": 0,
            "total_request_time": 0.0,
            "successful_requests": 0,
            "failed_requests": 0,
            "last_request_time": None,
        }

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        self.logger.info("StopHighScraper initialized successfully")

    def _setup_logger(self) -> logging.Logger:
        """ロガーのセットアップ"""
        logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

        return logger

    def _validate_inputs(self, market: str, term: str, page: int) -> None:
        """入力パラメータのバリデーション"""
        if not isinstance(market, str) or market not in self.VALID_MARKETS:
            raise ValidationError(
                f"無効な市場指定: {market}. 有効な値: {self.VALID_MARKETS}"
            )

        if not isinstance(term, str) or term not in self.VALID_TERMS:
            raise ValidationError(
                f"無効な期間指定: {term}. 有効な値: {self.VALID_TERMS}"
            )

        if not isinstance(page, int) or page < 1:
            raise ValidationError(
                f"ページ番号は1以上の整数である必要があります。指定値: {page}"
            )

    def _record_request_performance(self, start_time: float, success: bool) -> None:
        """リクエストのパフォーマンスを記録"""
        request_duration = time.time() - start_time
        self.performance_stats["requests_made"] += 1
        self.performance_stats["total_request_time"] += request_duration
        self.performance_stats["last_request_time"] = datetime.now()

        if success:
            self.performance_stats["successful_requests"] += 1
        else:
            self.performance_stats["failed_requests"] += 1

        self.logger.debug(
            f"Request completed in {request_duration:.2f}s, success: {success}"
        )

    def get_performance_stats(self) -> Dict:
        """パフォーマンス統計を取得"""
        stats = self.performance_stats.copy()
        if stats["requests_made"] > 0:
            stats["average_request_time"] = (
                stats["total_request_time"] / stats["requests_made"]
            )
            stats["success_rate"] = (
                stats["successful_requests"] / stats["requests_made"]
            )
        else:
            stats["average_request_time"] = 0.0
            stats["success_rate"] = 0.0

        return stats

    def get_stop_high_stocks(
        self, market: str = "all", term: str = "daily", page: int = 1
    ) -> List[Dict]:
        """
        ストップ高銘柄を取得

        Args:
            market: 市場指定 ("all", "tokyo", "osaka", etc.)
            term: 期間指定 ("daily", "weekly", "monthly")
            page: ページ番号

        Returns:
            取得した株式データのリスト

        Raises:
            ValidationError: 入力パラメータが無効な場合
            NetworkError: ネットワークエラーが発生した場合
        """
        # 入力バリデーション
        self._validate_inputs(market, term, page)

        params = {"market": market, "term": term, "page": page}
        start_time = time.time()

        try:
            self.logger.info(
                f"Requesting data: market={market}, term={term}, page={page}"
            )

            response = self.session.get(
                self.base_url, params=params, timeout=self.timeout
            )
            response.raise_for_status()

            self._record_request_performance(start_time, True)

            # JSON データの抽出を試みる
            stocks_from_json = self._extract_from_json(response.text)
            if stocks_from_json:
                self.logger.info(
                    f"Successfully extracted {len(stocks_from_json)} stocks from JSON"
                )
                return stocks_from_json

            # HTML パースの代替手段
            stocks_from_html = self._extract_from_html(response.text)
            self.logger.info(
                f"Successfully extracted {len(stocks_from_html)} stocks from HTML"
            )
            return stocks_from_html

        except requests.exceptions.RequestException as e:
            self._record_request_performance(start_time, False)
            self.logger.error(f"Network error: {e}")
            raise NetworkError(f"ネットワークエラーが発生しました: {e}")
        except Exception as e:
            self._record_request_performance(start_time, False)
            self.logger.error(f"Unexpected error: {e}")
            raise StopHighScraperError(f"予期しないエラーが発生しました: {e}")

    def _extract_from_json(self, html_content: str) -> List[Dict]:
        """
        HTML内のJSONデータからストップ高銘柄を抽出

        Args:
            html_content: HTML コンテンツ

        Returns:
            抽出された株式データのリスト

        Raises:
            DataParsingError: JSON データの解析に失敗した場合
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
                self.logger.debug("Found JSON pattern in HTML")
                json_data = json.loads(json_match.group(1))
                return self._parse_ranking_data(json_data)
            else:
                self.logger.warning("No JSON pattern found in HTML content")

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            raise DataParsingError(f"JSON解析エラー: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error in JSON extraction: {e}")
            raise DataParsingError(f"JSON抽出中の予期しないエラー: {e}")

        return []

    def _parse_ranking_data(self, json_data: Dict) -> List[Dict]:
        """
        JSONランキングデータからストップ高銘柄リストを生成

        Args:
            json_data: 解析対象のJSONデータ

        Returns:
            パースされた株式データのリスト
        """
        stocks = []

        try:
            results = json_data.get("results", [])
            self.logger.debug(f"Parsing {len(results)} results from JSON data")

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
                    self.logger.warning(f"株式データ {i} の処理中にエラー: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"ランキングデータの解析エラー: {e}")
            raise DataParsingError(f"ランキングデータの解析に失敗しました: {e}")

        return stocks

    def _find_table_rows(self, soup: BeautifulSoup) -> List:
        """HTMLからテーブル行を見つける"""
        selectors = [
            'div[data-module="RankingResult"] table tr',
            "table.rankingTable tr",
            "table tr",
            "div.RankingResult table tr",
            "[data-ranking] tr",
            ".rankingTable tr",
        ]

        for selector in selectors:
            rows = soup.select(selector)
            if rows and len(rows) > 1:
                self.logger.debug(f"使用したHTMLセレクタ: {selector}")
                return rows

        self.logger.warning("HTMLテーブルからデータ行が見つかりません")
        return []

    def _extract_stock_code(self, stock_cell, href: str, row_index: int) -> str:
        """株式コードを抽出"""
        code_match = re.search(r"code=([^&]+)", href)
        if not code_match:
            code_match = re.search(r"/quote/([^/?]+)", href)

        if code_match:
            return code_match.group(1)

        # セル内のテキストから4桁数字を探す
        code_text = stock_cell.get_text()
        code_match = re.search(r"(\d{4})", code_text)
        return code_match.group(1) if code_match else f"UNK{row_index}"

    def _extract_price_info(self, cells: List) -> Dict[str, str]:
        """価格情報を抽出"""
        price_info = {}
        for j, cell in enumerate(cells[2:], 2):
            cell_text = cell.get_text(strip=True)
            if j == 2:
                price_info["current_price"] = cell_text
            elif j == 3:
                price_info["price_change"] = cell_text
            elif j == 4:
                price_info["price_change_rate"] = cell_text
        return price_info

    def _parse_table_row(self, row, row_index: int) -> Optional[Dict]:
        """テーブル行から株式データを解析"""
        try:
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                return None

            # 順位
            rank_text = cells[0].get_text(strip=True)
            if not rank_text.replace(".", "").isdigit():
                return None

            rank = int(rank_text.replace(".", ""))

            # 銘柄情報セル
            stock_cell = cells[1]
            link = stock_cell.find("a")
            if not link:
                return None

            stock_name = link.get_text(strip=True)
            href = link.get("href", "")

            # 株式コードを抽出
            stock_code = self._extract_stock_code(stock_cell, href, row_index)

            # 市場情報
            market_elem = stock_cell.find("span")
            market = market_elem.get_text(strip=True) if market_elem else "不明"

            # 価格情報
            price_info = self._extract_price_info(cells)

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

            return stock_data

        except Exception as e:
            self.logger.warning(f"行 {row_index} の処理中にエラー: {e}")
            return None

    def _extract_from_html(self, html_content: str) -> List[Dict]:
        """
        HTMLテーブルからストップ高銘柄を抽出

        Args:
            html_content: HTML コンテンツ

        Returns:
            抽出された株式データのリスト
        """
        soup = BeautifulSoup(html_content, "html.parser")
        stocks = []

        rows = self._find_table_rows(soup)
        if not rows:
            return stocks

        self.logger.debug(f"Found {len(rows)} table rows")

        for i, row in enumerate(rows[1:], 1):  # ヘッダー行をスキップ
            stock_data = self._parse_table_row(row, i)
            if stock_data:
                stocks.append(stock_data)

                if i <= self.DEBUG_OUTPUT_LIMIT:
                    self.logger.debug(f"取得したストップ高株式 {i}: {stock_data}")

        self.logger.info(f"Successfully extracted {len(stocks)} stocks from HTML")
        return stocks

    def get_multiple_pages(
        self, market: str = "all", term: str = "daily", max_pages: Optional[int] = None
    ) -> List[Dict]:
        """
        複数ページからストップ高銘柄を取得

        Args:
            market: 市場指定
            term: 期間指定
            max_pages: 最大ページ数（Noneの場合はデフォルト値を使用）

        Returns:
            取得した全株式データのリスト

        Raises:
            ValidationError: 入力パラメータが無効な場合
        """
        if max_pages is None:
            max_pages = self.DEFAULT_MAX_PAGES

        if not isinstance(max_pages, int) or max_pages < 1:
            raise ValidationError(
                f"max_pages は1以上の整数である必要があります。指定値: {max_pages}"
            )

        all_stocks = []
        self.logger.info(f"Starting multi-page extraction: {max_pages} pages")

        for page in range(1, max_pages + 1):
            self.logger.info(f"ページ {page} を取得中...")

            try:
                stocks = self.get_stop_high_stocks(market=market, term=term, page=page)

                if not stocks:
                    self.logger.warning(f"ページ {page} でデータが見つかりませんでした")
                    break

                all_stocks.extend(stocks)
                self.logger.info(f"ページ {page}: {len(stocks)} 銘柄を取得")

                # リクエスト間隔を空ける
                if page < max_pages:
                    self.logger.debug(
                        f"Waiting {self.request_delay}s before next request"
                    )
                    time.sleep(self.request_delay)

            except (ValidationError, NetworkError, DataParsingError) as e:
                self.logger.error(f"ページ {page} の取得中にエラーが発生: {e}")
                break

        self.logger.info(
            f"Multi-page extraction completed: {len(all_stocks)} total stocks"
        )
        return all_stocks

    def save_to_csv(
        self, stocks: List[Dict], filename: str = "stop_high_stocks.csv"
    ) -> None:
        """
        ストップ高銘柄データをCSVファイルに保存

        Args:
            stocks: 保存する株式データのリスト
            filename: 保存ファイル名

        Raises:
            IOError: ファイル保存に失敗した場合
        """
        if not stocks:
            self.logger.warning("保存するデータがありません")
            return

        try:
            os.makedirs("work", exist_ok=True)
            filepath = os.path.join("work", filename)

            df = pd.DataFrame(stocks)
            df.to_csv(filepath, index=False, encoding="utf-8-sig")

            self.logger.info(f"データを {filepath} に保存しました ({len(stocks)} 銘柄)")

        except Exception as e:
            self.logger.error(f"CSV保存エラー: {e}")
            raise IOError(f"CSVファイルの保存に失敗しました: {e}")

    def print_summary(self, stocks: List[Dict]) -> None:
        """
        取得したストップ高銘柄データの要約を表示

        Args:
            stocks: 表示する株式データのリスト
        """
        if not stocks:
            print("データがありません")
            self.logger.info("No data to display in summary")
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
        display_limit = min(len(stocks), self.DISPLAY_LIMIT)

        for i, stock in enumerate(stocks[:display_limit], 1):
            price_change = stock.get("price_change", "N/A")
            price_change_rate = stock.get("price_change_rate", "N/A")
            price_info = (
                f"({price_change} {price_change_rate})" if price_change != "N/A" else ""
            )

            print(
                f"  {i:2d}. [{stock.get('stock_code', 'N/A')}] {stock.get('stock_name', 'N/A')} ({stock.get('market', 'N/A')}) {price_info}"
            )

        if len(stocks) > self.DISPLAY_LIMIT:
            print(f"  ... 他 {len(stocks) - self.DISPLAY_LIMIT} 銘柄")

        self.logger.info(f"Summary displayed for {len(stocks)} stocks")


def main():
    """
    メイン実行関数
    """
    # ロガーのセットアップ
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
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

            # パフォーマンス統計を表示
            stats = scraper.get_performance_stats()
            print(f"\n=== パフォーマンス統計 ===")
            print(f"総リクエスト数: {stats['requests_made']}")
            print(f"成功率: {stats['success_rate']:.1%}")
            print(f"平均レスポンス時間: {stats['average_request_time']:.2f}秒")

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

                    # 最終的なパフォーマンス統計
                    final_stats = scraper.get_performance_stats()
                    print(f"\n=== 最終パフォーマンス統計 ===")
                    print(f"総リクエスト数: {final_stats['requests_made']}")
                    print(f"成功率: {final_stats['success_rate']:.1%}")
                    print(
                        f"平均レスポンス時間: {final_stats['average_request_time']:.2f}秒"
                    )

    except ValidationError as e:
        print(f"入力エラー: {e}")
    except NetworkError as e:
        print(f"ネットワークエラー: {e}")
    except DataParsingError as e:
        print(f"データ解析エラー: {e}")
    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}")
        logging.exception("Unexpected error in main function")


if __name__ == "__main__":
    main()
