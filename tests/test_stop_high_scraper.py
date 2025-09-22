#!/usr/bin/env python3
"""
ストップ高スクレイパーのテスト
"""

import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from stop_high_scraper import StopHighScraper


class TestStopHighScraper:
    """StopHighScraperクラスのテスト"""

    def setup_method(self):
        """各テストメソッドの前に実行される"""
        self.scraper = StopHighScraper()

    def test_init(self):
        """初期化のテスト"""
        assert (
            self.scraper.base_url
            == "https://finance.yahoo.co.jp/stocks/ranking/stopHigh"
        )
        assert "User-Agent" in self.scraper.headers
        assert self.scraper.session is not None

    def test_parse_ranking_data_valid_json(self):
        """有効なJSONデータのパーステスト"""
        sample_json = {
            "results": [
                {
                    "stockCode": "1234",
                    "stockName": "テスト株式",
                    "marketName": "東証",
                    "savePrice": "1000",
                    "rankingResult": {
                        "stopPrice": {
                            "changePrice": "+100",
                            "changePriceRate": "+11.11%",
                            "previousClose": "900",
                        }
                    },
                },
                {
                    "stockCode": "5678",
                    "stockName": "サンプル株式",
                    "marketName": "札幌",
                    "savePrice": "500",
                    "rankingResult": {
                        "stopPrice": {
                            "changePrice": "+50",
                            "changePriceRate": "+11.11%",
                            "previousClose": "450",
                        }
                    },
                },
            ]
        }

        result = self.scraper._parse_ranking_data(sample_json)

        assert len(result) == 2
        assert result[0]["stock_code"] == "1234"
        assert result[0]["stock_name"] == "テスト株式"
        assert result[0]["market"] == "東証"
        assert result[0]["current_price"] == "1000"
        assert result[0]["price_change"] == "+100"
        assert result[0]["price_change_rate"] == "+11.11%"
        assert result[1]["stock_code"] == "5678"

    def test_parse_ranking_data_empty_results(self):
        """空のresultsのテスト"""
        empty_json = {"results": []}
        result = self.scraper._parse_ranking_data(empty_json)
        assert result == []

    def test_parse_ranking_data_missing_fields(self):
        """必須フィールドが欠けている場合のテスト"""
        incomplete_json = {
            "results": [
                {
                    "stockCode": "1234",
                    # stockNameが欠けている
                    "marketName": "東証",
                }
            ]
        }

        result = self.scraper._parse_ranking_data(incomplete_json)
        assert len(result) == 1
        assert result[0]["stock_code"] == "1234"
        assert result[0]["stock_name"] == ""  # デフォルト値

    def test_extract_from_json_with_valid_pattern(self):
        """有効なJSONパターンでの抽出テスト"""
        html_content = """
        <html>
        <script>
        window.mainRankingList = {
            "results": [
                {
                    "stockCode": "1234",
                    "stockName": "テスト株式",
                    "marketName": "東証",
                    "savePrice": "1000"
                }
            ]
        };
        </script>
        </html>
        """

        result = self.scraper._extract_from_json(html_content)
        assert len(result) == 1
        assert result[0]["stock_code"] == "1234"

    def test_extract_from_json_no_pattern(self):
        """JSONパターンが見つからない場合のテスト"""
        html_content = "<html><body>No JSON data here</body></html>"
        result = self.scraper._extract_from_json(html_content)
        assert result == []

    @patch("stop_high_scraper.BeautifulSoup")
    def test_extract_from_html(self, mock_bs):
        """HTML抽出のテスト"""
        # モックのHTMLテーブルを設定
        mock_soup = Mock()
        mock_bs.return_value = mock_soup

        # テーブル行のモック
        mock_header_row = Mock()
        mock_data_row = Mock()

        # セルのモック
        mock_rank_cell = Mock()
        mock_rank_cell.get_text.return_value = "1"

        mock_stock_cell = Mock()
        mock_link = Mock()
        mock_link.get_text.return_value = "テスト株式"
        mock_link.get.return_value = "/quote/1234"
        mock_stock_cell.find.return_value = mock_link

        mock_span = Mock()
        mock_span.get_text.return_value = "東証"
        mock_stock_cell.find.side_effect = [mock_link, mock_span]

        mock_price_cell = Mock()
        mock_price_cell.get_text.return_value = "1000"

        mock_data_row.find_all.return_value = [
            mock_rank_cell,
            mock_stock_cell,
            mock_price_cell,
        ]

        mock_soup.select.return_value = [mock_header_row, mock_data_row]

        result = self.scraper._extract_from_html("<html></html>")

        assert len(result) == 1
        assert result[0]["rank"] == 1
        assert result[0]["stock_name"] == "テスト株式"

    @patch("requests.Session.get")
    def test_get_stop_high_stocks_success(self, mock_get):
        """ストップ高銘柄取得成功のテスト"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = """
        <script>
        window.mainRankingList = {
            "results": [
                {
                    "stockCode": "1234",
                    "stockName": "テスト株式",
                    "marketName": "東証",
                    "savePrice": "1000"
                }
            ]
        };
        </script>
        """
        mock_get.return_value = mock_response

        result = self.scraper.get_stop_high_stocks()

        assert len(result) == 1
        assert result[0]["stock_code"] == "1234"
        mock_get.assert_called_once()

    @patch("requests.Session.get")
    def test_get_stop_high_stocks_http_error(self, mock_get):
        """HTTP エラーのテスト"""
        mock_get.side_effect = Exception("Network error")

        result = self.scraper.get_stop_high_stocks()

        assert result == []

    @patch("time.sleep")
    @patch.object(StopHighScraper, "get_stop_high_stocks")
    def test_get_multiple_pages(self, mock_get_stocks, mock_sleep):
        """複数ページ取得のテスト"""
        # 1ページ目: 2つの銘柄
        # 2ページ目: 1つの銘柄
        # 3ページ目: 空のリスト（終了）
        mock_get_stocks.side_effect = [
            [
                {"stock_code": "1234", "stock_name": "株式1"},
                {"stock_code": "5678", "stock_name": "株式2"},
            ],
            [{"stock_code": "9012", "stock_name": "株式3"}],
            [],
        ]

        result = self.scraper.get_multiple_pages(max_pages=5)

        assert len(result) == 3
        assert result[0]["stock_code"] == "1234"
        assert result[1]["stock_code"] == "5678"
        assert result[2]["stock_code"] == "9012"

        # get_stop_high_stocksが3回呼ばれる（3ページ目で空リストが返されて終了）
        assert mock_get_stocks.call_count == 3

        # sleepが2回呼ばれる（ページ間の待機）
        assert mock_sleep.call_count == 2

    @patch("os.makedirs")
    @patch("pandas.DataFrame.to_csv")
    def test_save_to_csv(self, mock_to_csv, mock_makedirs):
        """CSV保存のテスト"""
        stocks_data = [
            {"stock_code": "1234", "stock_name": "テスト株式", "market": "東証"},
            {"stock_code": "5678", "stock_name": "サンプル株式", "market": "札幌"},
        ]

        self.scraper.save_to_csv(stocks_data, "test_output.csv")

        mock_makedirs.assert_called_once_with("work", exist_ok=True)
        mock_to_csv.assert_called_once_with(
            os.path.join("work", "test_output.csv"), index=False, encoding="utf-8-sig"
        )

    def test_save_to_csv_empty_data(self, capsys):
        """空データでのCSV保存テスト"""
        self.scraper.save_to_csv([])

        captured = capsys.readouterr()
        assert "保存するデータがありません" in captured.out

    def test_print_summary_with_data(self, capsys):
        """データありの要約表示テスト"""
        stocks_data = [
            {
                "stock_code": "1234",
                "stock_name": "テスト株式",
                "market": "東証",
                "price_change": "+100",
                "price_change_rate": "+10%",
            },
            {
                "stock_code": "5678",
                "stock_name": "サンプル株式",
                "market": "札幌",
                "price_change": "+50",
                "price_change_rate": "+5%",
            },
            {
                "stock_code": "9012",
                "stock_name": "例示株式",
                "market": "東証",
                "price_change": "+75",
                "price_change_rate": "+7.5%",
            },
        ]

        self.scraper.print_summary(stocks_data)

        captured = capsys.readouterr()
        assert "ストップ高銘柄 取得結果" in captured.out
        assert "総銘柄数: 3" in captured.out
        assert "東証: 2 銘柄" in captured.out
        assert "札幌: 1 銘柄" in captured.out
        assert "テスト株式" in captured.out

    def test_print_summary_empty_data(self, capsys):
        """空データの要約表示テスト"""
        self.scraper.print_summary([])

        captured = capsys.readouterr()
        assert "データがありません" in captured.out

    def test_print_summary_many_stocks(self, capsys):
        """多数の銘柄データの要約表示テスト（上位20件のみ表示）"""
        stocks_data = []
        for i in range(25):
            stocks_data.append(
                {
                    "stock_code": f"{1000 + i}",
                    "stock_name": f"株式{i+1}",
                    "market": "東証",
                    "price_change": f"+{10 + i}",
                    "price_change_rate": f"+{5 + i}%",
                }
            )

        self.scraper.print_summary(stocks_data)

        captured = capsys.readouterr()
        assert "総銘柄数: 25" in captured.out
        assert "他 5 銘柄" in captured.out
        assert "株式20" in captured.out  # 20番目まで表示
        assert "株式25" not in captured.out  # 25番目は表示されない


@pytest.fixture
def sample_stocks_data():
    """テスト用のサンプル株式データ"""
    return [
        {
            "rank": 1,
            "stock_code": "1234",
            "stock_name": "テスト株式",
            "market": "東証",
            "current_price": "1000",
            "price_change": "+100",
            "price_change_rate": "+11.11%",
            "yahoo_url": "https://finance.yahoo.co.jp/quote/1234",
        },
        {
            "rank": 2,
            "stock_code": "5678",
            "stock_name": "サンプル株式",
            "market": "札幌",
            "current_price": "500",
            "price_change": "+50",
            "price_change_rate": "+11.11%",
            "yahoo_url": "https://finance.yahoo.co.jp/quote/5678",
        },
    ]


def test_integration_with_sample_data(sample_stocks_data):
    """サンプルデータを使った統合テスト"""
    scraper = StopHighScraper()

    # データ形式の確認
    for stock in sample_stocks_data:
        assert "stock_code" in stock
        assert "stock_name" in stock
        assert "market" in stock
        assert "yahoo_url" in stock

    # URL形式の確認
    for stock in sample_stocks_data:
        assert stock["yahoo_url"].startswith("https://finance.yahoo.co.jp/quote/")
        assert stock["stock_code"] in stock["yahoo_url"]
