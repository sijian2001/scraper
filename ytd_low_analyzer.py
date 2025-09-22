#!/usr/bin/env python3
"""
年初来安値取得・分析プログラム
Yahoo Finance Japan から年初来安値データを取得し、詳細分析を行う
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
import numpy as np


class YearToDateLowAnalyzer:
    def __init__(self):
        self.base_url = "https://finance.yahoo.co.jp/stocks/ranking/yearToDateLow"
        self.quote_base = "https://finance.yahoo.co.jp/quote"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.5',
            'Connection': 'keep-alive',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_ytd_low_stocks(self, pages: int = 3) -> List[Dict]:
        """
        年初来安値更新銘柄を取得

        Args:
            pages: 取得するページ数

        Returns:
            銘柄データのリスト
        """
        all_stocks = []

        for page in range(1, pages + 1):
            print(f"ページ {page}/{pages} を処理中...")

            params = {'market': 'all', 'term': 'daily', 'page': page}

            try:
                response = self.session.get(self.base_url, params=params)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')

                # テーブル行を検索
                rows = soup.select('table tr')

                if not rows or len(rows) <= 1:
                    print(f"ページ {page} にデータが見つかりません")
                    continue

                page_stocks = []
                for i, row in enumerate(rows[1:], 1):  # ヘッダー行をスキップ
                    try:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) < 3:
                            continue

                        # 順位
                        rank_text = cells[0].get_text(strip=True).replace('.', '')
                        if not rank_text.isdigit():
                            continue

                        rank = int(rank_text)

                        # 銘柄情報
                        stock_cell = cells[1]
                        link = stock_cell.find('a')

                        if not link:
                            continue

                        stock_name = link.get_text(strip=True)
                        href = link.get('href', '')

                        # 銘柄コード抽出
                        code_match = re.search(r'code=([^&]+)', href) or re.search(r'/quote/([^/?]+)', href)
                        if code_match:
                            stock_code = code_match.group(1).replace('.T', '')
                        else:
                            # セル内からコードを探す
                            code_match = re.search(r'(\d{4})', stock_cell.get_text())
                            stock_code = code_match.group(1) if code_match else f"UNKNOWN_{rank}"

                        # 市場情報
                        market_span = stock_cell.find('span')
                        market = market_span.get_text(strip=True) if market_span else "不明"

                        # 価格データ
                        price_data = {}
                        for j, cell in enumerate(cells[2:], 2):
                            cell_text = cell.get_text(strip=True)
                            if j == 2:
                                price_data['current_info'] = cell_text
                            elif j == 3:
                                price_data['ytd_low_info'] = cell_text
                            elif j == 4:
                                price_data['additional_info'] = cell_text

                        stock_info = {
                            'rank': rank,
                            'stock_code': stock_code,
                            'stock_name': stock_name,
                            'market': market,
                            'yahoo_url': f"https://finance.yahoo.co.jp{href}" if href.startswith('/') else href,
                            **price_data
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
        個別銘柄の詳細情報を取得（年初来安値に特化）

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

            # 年初来安値を計算
            ytd_low = hist['Low'].min()
            ytd_low_date = hist['Low'].idxmin().strftime('%Y-%m-%d')

            # 現在価格
            current_price = hist['Close'].iloc[-1]

            # 年初来高値
            ytd_high = hist['High'].max()
            ytd_high_date = hist['High'].idxmax().strftime('%Y-%m-%d')

            # 年初価格
            year_start_price = hist['Close'].iloc[0]

            # パフォーマンス計算
            ytd_return = ((current_price - year_start_price) / year_start_price) * 100
            low_decline = ((ytd_low - year_start_price) / year_start_price) * 100
            recovery_from_low = ((current_price - ytd_low) / ytd_low) * 100

            # 安値からの回復率
            max_drawdown = ((ytd_low - ytd_high) / ytd_high) * 100 if ytd_high > 0 else 0

            # 技術指標の計算
            sma_20 = hist['Close'].rolling(window=20).mean().iloc[-1] if len(hist) >= 20 else current_price
            sma_50 = hist['Close'].rolling(window=50).mean().iloc[-1] if len(hist) >= 50 else current_price

            # ボラティリティ計算
            returns = hist['Close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252) * 100  # 年率ボラティリティ

            # 基本情報を取得
            info = stock.info

            return {
                'stock_code': stock_code,
                'company_name': info.get('longName', 'N/A'),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'current_price': round(current_price, 2),
                'ytd_low': round(ytd_low, 2),
                'ytd_low_date': ytd_low_date,
                'ytd_high': round(ytd_high, 2),
                'ytd_high_date': ytd_high_date,
                'year_start_price': round(year_start_price, 2),
                'ytd_return_pct': round(ytd_return, 2),
                'low_decline_pct': round(low_decline, 2),
                'recovery_from_low_pct': round(recovery_from_low, 2),
                'max_drawdown_pct': round(max_drawdown, 2),
                'sma_20': round(sma_20, 2),
                'sma_50': round(sma_50, 2),
                'volatility_pct': round(volatility, 2),
                'market_cap': info.get('marketCap', 'N/A'),
                'pe_ratio': info.get('trailingPE', 'N/A'),
                'pb_ratio': info.get('priceToBook', 'N/A'),
                'volume': info.get('volume', 'N/A'),
                'avg_volume': info.get('averageVolume', 'N/A'),
                'dividend_yield': info.get('dividendYield', 'N/A')
            }

        except Exception as e:
            print(f"銘柄 {stock_code} の詳細取得でエラー: {e}")
            return None

    def analyze_recovery_potential(self, stocks: List[Dict]) -> pd.DataFrame:
        """
        回復ポテンシャルを分析

        Args:
            stocks: 銘柄データリスト

        Returns:
            分析結果のDataFrame
        """
        detailed_data = []

        print(f"\n回復ポテンシャル分析を開始... ({len(stocks)} 銘柄)")

        for i, stock in enumerate(stocks[:25], 1):  # 最初の25銘柄を詳細分析
            print(f"分析中 ({i}/25): {stock['stock_code']} - {stock['stock_name']}")

            detailed_info = self.get_detailed_stock_info(stock['stock_code'])

            if detailed_info:
                # 回復ポテンシャル スコアを計算
                recovery_score = self.calculate_recovery_score(detailed_info)
                detailed_info['recovery_score'] = recovery_score

                # 元のデータと詳細データを結合
                combined_data = {**stock, **detailed_info}
                detailed_data.append(combined_data)
            else:
                # 詳細取得に失敗した場合は元のデータのみ
                detailed_data.append(stock)

            # レート制限
            time.sleep(0.5)

        return pd.DataFrame(detailed_data)

    def calculate_recovery_score(self, stock_info: Dict) -> float:
        """
        回復ポテンシャル スコアを計算

        Args:
            stock_info: 銘柄の詳細情報

        Returns:
            回復スコア (0-100)
        """
        score = 50  # ベーススコア

        try:
            # 安値からの回復率（正の要因）
            if stock_info.get('recovery_from_low_pct', 0) > 20:
                score += 15
            elif stock_info.get('recovery_from_low_pct', 0) > 10:
                score += 10
            elif stock_info.get('recovery_from_low_pct', 0) > 5:
                score += 5

            # PBR（株価純資産倍率）
            pb_ratio = stock_info.get('pb_ratio', 'N/A')
            if pb_ratio != 'N/A' and pb_ratio < 1.0:
                score += 15  # 資産価値より安い
            elif pb_ratio != 'N/A' and pb_ratio < 1.5:
                score += 10

            # PER（株価収益率）
            pe_ratio = stock_info.get('pe_ratio', 'N/A')
            if pe_ratio != 'N/A' and 5 < pe_ratio < 15:
                score += 10  # 適正範囲

            # 配当利回り
            dividend_yield = stock_info.get('dividend_yield', 'N/A')
            if dividend_yield != 'N/A' and dividend_yield > 0.03:  # 3%以上
                score += 10

            # 移動平均との関係
            current_price = stock_info.get('current_price', 0)
            sma_20 = stock_info.get('sma_20', 0)
            sma_50 = stock_info.get('sma_50', 0)

            if current_price > sma_20 > sma_50:
                score += 15  # 上昇トレンド
            elif current_price > sma_20:
                score += 5

            # ボラティリティ（安定性）
            volatility = stock_info.get('volatility_pct', 100)
            if volatility < 30:
                score += 5  # 低ボラティリティは安定性を示す

            # 年初来の下落率（深い下落ほど反発の可能性）
            low_decline = abs(stock_info.get('low_decline_pct', 0))
            if low_decline > 50:
                score += 10
            elif low_decline > 30:
                score += 5

        except Exception:
            pass

        return min(max(score, 0), 100)  # 0-100の範囲に制限

    def filter_recovery_candidates(self, df: pd.DataFrame, criteria: Dict) -> pd.DataFrame:
        """
        回復候補銘柄をフィルタリング

        Args:
            df: 銘柄データのDataFrame
            criteria: フィルタリング条件

        Returns:
            フィルタリング後のDataFrame
        """
        filtered_df = df.copy()

        # 回復スコアによるフィルタ
        if 'min_recovery_score' in criteria:
            filtered_df = filtered_df[filtered_df['recovery_score'] >= criteria['min_recovery_score']]

        # 安値からの回復率によるフィルタ
        if 'min_recovery_from_low' in criteria:
            filtered_df = filtered_df[filtered_df['recovery_from_low_pct'] >= criteria['min_recovery_from_low']]

        # PBR によるフィルタ
        if 'max_pb_ratio' in criteria:
            pb_mask = (filtered_df['pb_ratio'] != 'N/A') & (pd.to_numeric(filtered_df['pb_ratio'], errors='coerce') <= criteria['max_pb_ratio'])
            filtered_df = filtered_df[pb_mask]

        # 配当利回りによるフィルタ
        if 'min_dividend_yield' in criteria:
            div_mask = (filtered_df['dividend_yield'] != 'N/A') & (pd.to_numeric(filtered_df['dividend_yield'], errors='coerce') >= criteria['min_dividend_yield'])
            filtered_df = filtered_df[div_mask]

        # セクターによるフィルタ
        if 'sectors' in criteria:
            filtered_df = filtered_df[filtered_df['sector'].isin(criteria['sectors'])]

        return filtered_df

    def save_analysis_results(self, df: pd.DataFrame, filename: str = "ytd_low_analysis.csv") -> None:
        """
        分析結果をCSVファイルに保存

        Args:
            df: 保存するDataFrame
            filename: ファイル名
        """
        if df.empty:
            print("保存するデータがありません")
            return

        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"分析結果を {filename} に保存しました ({len(df)} 銘柄)")

    def print_recovery_candidates(self, df: pd.DataFrame, top_n: int = 10) -> None:
        """
        回復候補銘柄を表示

        Args:
            df: 銘柄データのDataFrame
            top_n: 表示する銘柄数
        """
        if df.empty:
            print("表示するデータがありません")
            return

        print(f"\n=== 回復ポテンシャル銘柄 トップ{top_n} ===")

        # 回復スコアでソート
        if 'recovery_score' in df.columns:
            top_stocks = df.nlargest(top_n, 'recovery_score')

            for i, row in top_stocks.iterrows():
                print(f"{row.get('rank', 'N/A'):2}. [{row.get('stock_code', 'N/A')}] {row.get('stock_name', 'N/A')}")
                if 'recovery_score' in row:
                    print(f"    回復スコア: {row['recovery_score']:.1f}/100")
                if 'ytd_low' in row:
                    print(f"    年初来安値: {row['ytd_low']:,.0f}円 ({row.get('ytd_low_date', 'N/A')})")
                if 'recovery_from_low_pct' in row:
                    print(f"    安値からの回復: {row['recovery_from_low_pct']:.2f}%")
                if 'pb_ratio' in row and row['pb_ratio'] != 'N/A':
                    print(f"    PBR: {row['pb_ratio']:.2f}")
                if 'sector' in row and row['sector'] != 'N/A':
                    print(f"    セクター: {row['sector']}")
                print()
        else:
            # 詳細データがない場合は基本情報のみ表示
            for i, row in df.head(top_n).iterrows():
                print(f"{row.get('rank', 'N/A'):2}. [{row.get('stock_code', 'N/A')}] {row.get('stock_name', 'N/A')} ({row.get('market', 'N/A')})")

    def print_worst_performers(self, df: pd.DataFrame, top_n: int = 10) -> None:
        """
        年初来で最も下落した銘柄を表示

        Args:
            df: 銘柄データのDataFrame
            top_n: 表示する銘柄数
        """
        if df.empty or 'low_decline_pct' not in df.columns:
            print("下落データがありません")
            return

        print(f"\n=== 年初来安値更新 最大下落銘柄 トップ{top_n} ===")

        # 下落率でソート（最も下落した銘柄）
        worst_stocks = df.nsmallest(top_n, 'low_decline_pct')

        for i, row in worst_stocks.iterrows():
            print(f"{row.get('rank', 'N/A'):2}. [{row.get('stock_code', 'N/A')}] {row.get('stock_name', 'N/A')}")
            if 'low_decline_pct' in row:
                print(f"    最大下落率: {row['low_decline_pct']:.2f}%")
            if 'ytd_low' in row:
                print(f"    年初来安値: {row['ytd_low']:,.0f}円")
            if 'current_price' in row:
                print(f"    現在価格: {row['current_price']:,.0f}円")
            if 'sector' in row and row['sector'] != 'N/A':
                print(f"    セクター: {row['sector']}")
            print()

    def generate_summary_report(self, df: pd.DataFrame) -> None:
        """
        サマリーレポートを生成

        Args:
            df: 銘柄データのDataFrame
        """
        print("\n" + "="*60)
        print("年初来安値更新銘柄 分析レポート")
        print("="*60)

        print(f"総銘柄数: {len(df)}")

        if 'low_decline_pct' in df.columns:
            declines = df['low_decline_pct'].dropna()
            if not declines.empty:
                print(f"平均下落率: {declines.mean():.2f}%")
                print(f"最大下落率: {declines.min():.2f}%")
                print(f"最小下落率: {declines.max():.2f}%")

        if 'recovery_from_low_pct' in df.columns:
            recoveries = df['recovery_from_low_pct'].dropna()
            if not recoveries.empty:
                print(f"平均安値からの回復率: {recoveries.mean():.2f}%")

        if 'recovery_score' in df.columns:
            scores = df['recovery_score'].dropna()
            if not scores.empty:
                print(f"平均回復スコア: {scores.mean():.1f}/100")

        if 'sector' in df.columns:
            sectors = df['sector'].value_counts()
            print(f"\nセクター別分布:")
            for sector, count in sectors.head(5).items():
                if sector != 'N/A':
                    print(f"  {sector}: {count} 銘柄")

        if 'market' in df.columns:
            markets = df['market'].value_counts()
            print(f"\n市場別分布:")
            for market, count in markets.head(5).items():
                if market != '不明':
                    print(f"  {market}: {count} 銘柄")


def main():
    """
    メイン実行関数
    """
    analyzer = YearToDateLowAnalyzer()

    print("年初来安値更新銘柄の取得と分析を開始...")

    # 年初来安値更新銘柄を取得
    stocks = analyzer.get_ytd_low_stocks(pages=2)

    if not stocks:
        print("データの取得に失敗しました")
        return

    print(f"\n{len(stocks)} 銘柄を取得しました")

    # 回復ポテンシャル分析を実行
    detailed_df = analyzer.analyze_recovery_potential(stocks)

    # 基本的な分析結果を保存
    basic_df = pd.DataFrame(stocks)
    analyzer.save_analysis_results(basic_df, "ytd_low_basic.csv")

    # 詳細分析結果を保存（詳細データがある場合）
    if not detailed_df.empty:
        analyzer.save_analysis_results(detailed_df, "ytd_low_detailed.csv")

    # 結果表示
    analyzer.print_recovery_candidates(detailed_df if not detailed_df.empty else basic_df)

    if not detailed_df.empty and 'low_decline_pct' in detailed_df.columns:
        analyzer.print_worst_performers(detailed_df)

    analyzer.generate_summary_report(detailed_df if not detailed_df.empty else basic_df)

    # 回復候補フィルタリング例
    if not detailed_df.empty and 'recovery_score' in detailed_df.columns:
        print("\n高回復ポテンシャル銘柄（回復スコア70以上）:")
        high_potential = analyzer.filter_recovery_candidates(
            detailed_df,
            {'min_recovery_score': 70}
        )
        analyzer.print_recovery_candidates(high_potential, 5)

        print("\nバリュー投資候補（PBR 1.5以下）:")
        value_candidates = analyzer.filter_recovery_candidates(
            detailed_df,
            {'max_pb_ratio': 1.5, 'min_recovery_score': 60}
        )
        analyzer.print_recovery_candidates(value_candidates, 5)


if __name__ == "__main__":
    main()