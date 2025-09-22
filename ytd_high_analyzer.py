#!/usr/bin/env python3
"""
年初来高値取得・分析プログラム
Yahoo Finance Japan から年初来高値データを取得し、詳細分析を行う
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import yfinance as yf


class YearToDateHighAnalyzer:
    def __init__(self):
        self.base_url = "https://finance.yahoo.co.jp/stocks/ranking/yearToDateHigh"
        self.quote_base = "https://finance.yahoo.co.jp/quote"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.5",
            "Connection": "keep-alive",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_ytd_high_stocks(self, pages: int = 3) -> List[Dict]:
        """
        年初来高値更新銘柄を取得

        Args:
            pages: 取得するページ数

        Returns:
            銘柄データのリスト
        """
        all_stocks = []

        for page in range(1, pages + 1):
            print(f"ページ {page}/{pages} を処理中...")

            params = {"market": "all", "term": "daily", "page": page}

            try:
                response = self.session.get(self.base_url, params=params)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                # テーブル行を検索
                rows = soup.select("table tr")

                if not rows or len(rows) <= 1:
                    print(f"ページ {page} にデータが見つかりません")
                    continue

                page_stocks = []
                for i, row in enumerate(rows[1:], 1):  # ヘッダー行をスキップ
                    try:
                        cells = row.find_all(["td", "th"])
                        if len(cells) < 3:
                            continue

                        # 順位
                        rank_text = cells[0].get_text(strip=True).replace(".", "")
                        if not rank_text.isdigit():
                            continue

                        rank = int(rank_text)

                        # 銘柄情報
                        stock_cell = cells[1]
                        link = stock_cell.find("a")

                        if not link:
                            continue

                        stock_name = link.get_text(strip=True)
                        href = link.get("href", "")

                        # 銘柄コード抽出
                        code_match = re.search(r"code=([^&]+)", href) or re.search(
                            r"/quote/([^/?]+)", href
                        )
                        if code_match:
                            stock_code = code_match.group(1).replace(".T", "")
                        else:
                            # セル内からコードを探す
                            code_match = re.search(r"(\d{4})", stock_cell.get_text())
                            stock_code = (
                                code_match.group(1) if code_match else f"UNKNOWN_{rank}"
                            )

                        # 市場情報
                        market_span = stock_cell.find("span")
                        market = (
                            market_span.get_text(strip=True) if market_span else "不明"
                        )

                        # 価格データ
                        price_data = {}
                        for j, cell in enumerate(cells[2:], 2):
                            cell_text = cell.get_text(strip=True)
                            if j == 2:
                                price_data["current_info"] = cell_text
                            elif j == 3:
                                price_data["ytd_high_info"] = cell_text
                            elif j == 4:
                                price_data["additional_info"] = cell_text

                        stock_info = {
                            "rank": rank,
                            "stock_code": stock_code,
                            "stock_name": stock_name,
                            "market": market,
                            "yahoo_url": (
                                f"https://finance.yahoo.co.jp{href}"
                                if href.startswith("/")
                                else href
                            ),
                            **price_data,
                        }

                        page_stocks.append(stock_info)

                    except Exception as e:
                        print(f"行 {i} の処理でエラー: {e}")
                        continue

                all_stocks.extend(page_stocks)
                print(f"ページ {page}: {len(page_stocks)} 銘柄を取得")

                # レート制限
                time.sleep(1)

            except Exception as e:
                print(f"ページ {page} の取得でエラー: {e}")
                continue

        return all_stocks

    def get_detailed_stock_info(self, stock_code: str) -> Optional[Dict]:
        """
        個別銘柄の詳細情報を取得

        Args:
            stock_code: 銘柄コード

        Returns:
            詳細情報辞書
        """
        try:
            # yfinanceで取得を試行（日本株は .T を付加）
            ticker_symbol = f"{stock_code}.T"
            stock = yf.Ticker(ticker_symbol)

            # 過去1年のデータを取得
            hist = stock.history(period="1y")

            if hist.empty:
                return None

            # 年初来高値を計算
            ytd_high = hist["High"].max()
            ytd_high_date = hist["High"].idxmax().strftime("%Y-%m-%d")

            # 現在価格
            current_price = hist["Close"].iloc[-1]

            # 年初来安値
            ytd_low = hist["Low"].min()
            ytd_low_date = hist["Low"].idxmin().strftime("%Y-%m-%d")

            # 年初価格
            year_start_price = hist["Close"].iloc[0]

            # パフォーマンス計算
            ytd_return = ((current_price - year_start_price) / year_start_price) * 100
            high_return = ((ytd_high - year_start_price) / year_start_price) * 100

            # 基本情報を取得
            info = stock.info

            return {
                "stock_code": stock_code,
                "company_name": info.get("longName", "N/A"),
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "current_price": round(current_price, 2),
                "ytd_high": round(ytd_high, 2),
                "ytd_high_date": ytd_high_date,
                "ytd_low": round(ytd_low, 2),
                "ytd_low_date": ytd_low_date,
                "year_start_price": round(year_start_price, 2),
                "ytd_return_pct": round(ytd_return, 2),
                "high_return_pct": round(high_return, 2),
                "market_cap": info.get("marketCap", "N/A"),
                "pe_ratio": info.get("trailingPE", "N/A"),
                "volume": info.get("volume", "N/A"),
                "avg_volume": info.get("averageVolume", "N/A"),
            }

        except Exception as e:
            print(f"銘柄 {stock_code} の詳細取得でエラー: {e}")
            return None

    def analyze_ytd_performance(self, stocks: List[Dict]) -> pd.DataFrame:
        """
        年初来パフォーマンスを分析

        Args:
            stocks: 銘柄データリスト

        Returns:
            分析結果のDataFrame
        """
        detailed_data = []

        print(f"\n詳細分析を開始... ({len(stocks)} 銘柄)")

        for i, stock in enumerate(stocks[:20], 1):  # 最初の20銘柄を詳細分析
            print(f"分析中 ({i}/20): {stock['stock_code']} - {stock['stock_name']}")

            detailed_info = self.get_detailed_stock_info(stock["stock_code"])

            if detailed_info:
                # 元のデータと詳細データを結合
                combined_data = {**stock, **detailed_info}
                detailed_data.append(combined_data)
            else:
                # 詳細取得に失敗した場合は元のデータのみ
                detailed_data.append(stock)

            # レート制限
            time.sleep(0.5)

        return pd.DataFrame(detailed_data)

    def filter_stocks(self, df: pd.DataFrame, criteria: Dict) -> pd.DataFrame:
        """
        銘柄をフィルタリング

        Args:
            df: 銘柄データのDataFrame
            criteria: フィルタリング条件

        Returns:
            フィルタリング後のDataFrame
        """
        filtered_df = df.copy()

        # 年初来リターンによるフィルタ
        if "min_ytd_return" in criteria:
            filtered_df = filtered_df[
                filtered_df["ytd_return_pct"] >= criteria["min_ytd_return"]
            ]

        # 最大年初来リターンによるフィルタ
        if "min_high_return" in criteria:
            filtered_df = filtered_df[
                filtered_df["high_return_pct"] >= criteria["min_high_return"]
            ]

        # セクターによるフィルタ
        if "sectors" in criteria:
            filtered_df = filtered_df[filtered_df["sector"].isin(criteria["sectors"])]

        # 時価総額によるフィルタ
        if "min_market_cap" in criteria:
            filtered_df = filtered_df[
                (filtered_df["market_cap"] != "N/A")
                & (filtered_df["market_cap"] >= criteria["min_market_cap"])
            ]

        return filtered_df

    def save_analysis_results(
        self, df: pd.DataFrame, filename: str = "ytd_high_analysis.csv"
    ) -> None:
        """
        分析結果をCSVファイルに保存

        Args:
            df: 保存するDataFrame
            filename: ファイル名
        """
        if df.empty:
            print("保存するデータがありません")
            return

        import os

        # workディレクトリが存在しない場合は作成
        os.makedirs("work", exist_ok=True)

        # workディレクトリ内にファイルを保存
        filepath = os.path.join("work", filename)

        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        print(f"分析結果を {filepath} に保存しました ({len(df)} 銘柄)")

    def print_top_performers(self, df: pd.DataFrame, top_n: int = 10) -> None:
        """
        トップパフォーマーを表示

        Args:
            df: 銘柄データのDataFrame
            top_n: 表示する銘柄数
        """
        if df.empty:
            print("表示するデータがありません")
            return

        print(f"\n=== 年初来高値更新銘柄 トップ{top_n} ===")

        # 年初来リターンでソート
        if "ytd_return_pct" in df.columns:
            top_stocks = df.nlargest(top_n, "ytd_return_pct")

            for i, row in top_stocks.iterrows():
                print(
                    f"{row.get('rank', 'N/A'):2}. [{row.get('stock_code', 'N/A')}] {row.get('stock_name', 'N/A')}"
                )
                if "ytd_return_pct" in row:
                    print(f"    年初来リターン: {row['ytd_return_pct']:.2f}%")
                if "ytd_high" in row:
                    print(f"    年初来高値: {row['ytd_high']:,.0f}円")
                if "sector" in row and row["sector"] != "N/A":
                    print(f"    セクター: {row['sector']}")
                print()
        else:
            # 詳細データがない場合は基本情報のみ表示
            for i, row in df.head(top_n).iterrows():
                print(
                    f"{row.get('rank', 'N/A'):2}. [{row.get('stock_code', 'N/A')}] {row.get('stock_name', 'N/A')} ({row.get('market', 'N/A')})"
                )

    def generate_summary_report(self, df: pd.DataFrame) -> None:
        """
        サマリーレポートを生成

        Args:
            df: 銘柄データのDataFrame
        """
        print("\n" + "=" * 60)
        print("年初来高値更新銘柄 分析レポート")
        print("=" * 60)

        print(f"総銘柄数: {len(df)}")

        if "ytd_return_pct" in df.columns:
            ytd_returns = df["ytd_return_pct"].dropna()
            if not ytd_returns.empty:
                print(f"平均年初来リターン: {ytd_returns.mean():.2f}%")
                print(f"最大年初来リターン: {ytd_returns.max():.2f}%")
                print(f"最小年初来リターン: {ytd_returns.min():.2f}%")

        if "sector" in df.columns:
            sectors = df["sector"].value_counts()
            print(f"\nセクター別分布:")
            for sector, count in sectors.head(5).items():
                if sector != "N/A":
                    print(f"  {sector}: {count} 銘柄")

        if "market" in df.columns:
            markets = df["market"].value_counts()
            print(f"\n市場別分布:")
            for market, count in markets.head(5).items():
                if market != "不明":
                    print(f"  {market}: {count} 銘柄")


def main():
    """
    メイン実行関数
    """
    analyzer = YearToDateHighAnalyzer()

    print("年初来高値更新銘柄の取得と分析を開始...")

    # 年初来高値更新銘柄を取得
    stocks = analyzer.get_ytd_high_stocks(pages=2)

    if not stocks:
        print("データの取得に失敗しました")
        return

    print(f"\n{len(stocks)} 銘柄を取得しました")

    # 詳細分析を実行
    detailed_df = analyzer.analyze_ytd_performance(stocks)

    # 基本的な分析結果を保存
    basic_df = pd.DataFrame(stocks)
    analyzer.save_analysis_results(basic_df, "ytd_high_basic.csv")

    # 詳細分析結果を保存（詳細データがある場合）
    if not detailed_df.empty:
        analyzer.save_analysis_results(detailed_df, "ytd_high_detailed.csv")

    # 結果表示
    analyzer.print_top_performers(detailed_df if not detailed_df.empty else basic_df)
    analyzer.generate_summary_report(detailed_df if not detailed_df.empty else basic_df)

    # フィルタリング例
    if not detailed_df.empty and "ytd_return_pct" in detailed_df.columns:
        print("\n高パフォーマンス銘柄（年初来リターン10%以上）:")
        high_performers = analyzer.filter_stocks(detailed_df, {"min_ytd_return": 10.0})
        analyzer.print_top_performers(high_performers, 5)


if __name__ == "__main__":
    main()
