import pytest
import pandas as pd
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from yahoo_finance_scraper import YahooFinanceScraper


class TestYahooFinanceScraper:
    """Yahoo Finance Scraperのテストクラス"""

    @pytest.fixture
    def scraper(self):
        """スクレーパーのインスタンスを作成"""
        return YahooFinanceScraper()

    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_stock_data(self):
        """サンプル株式データ"""
        return [
            {
                "code": "7203",
                "name": "トヨタ自動車",
                "price": 2500.0,
                "change": "+50",
                "change_percent": "+2.04%",
                "ytd_high": 2600.0,
                "ytd_low": 2000.0,
                "volume": 1000000,
            },
            {
                "code": "6758",
                "name": "ソニーグループ",
                "price": 12000.0,
                "change": "-100",
                "change_percent": "-0.82%",
                "ytd_high": 13000.0,
                "ytd_low": 10000.0,
                "volume": 500000,
            },
        ]

    def test_init(self, scraper):
        """初期化のテスト"""
        assert scraper.session is not None
        assert scraper.session.headers["User-Agent"] is not None

    @patch("yahoo_finance_scraper.requests.Session.get")
    def test_get_stock_info_success(self, mock_get, scraper):
        """株式情報取得の成功テスト"""
        # モックレスポンスの設定
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <div class="price" data-symbol="7203" data-field="regularMarketPrice" data-trend="none" data-pricehint="2">2,500</div>
        <div class="change positive">+50.00 (+2.04%)</div>
        <td>年初来高値</td><td>2,600</td>
        <td>年初来安値</td><td>2,000</td>
        <span>出来高</span><span>1,000,000</span>
        """
        mock_get.return_value = mock_response

        result = scraper.get_stock_info("7203")

        assert result is not None
        assert result["code"] == "7203"
        assert result["price"] == 2500.0

    @patch("yahoo_finance_scraper.requests.Session.get")
    def test_get_stock_info_failure(self, mock_get, scraper):
        """株式情報取得の失敗テスト"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = scraper.get_stock_info("INVALID")
        assert result is None

    def test_save_to_csv(self, scraper, sample_stock_data, temp_dir):
        """CSV保存のテスト"""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            scraper.save_to_csv(sample_stock_data, "test_output.csv")

            # ファイルが作成されたことを確認
            assert os.path.exists("work/test_output.csv")

            # ファイル内容を確認
            df = pd.read_csv("work/test_output.csv")
            assert len(df) == 2
            assert "7203" in df["code"].values
            assert "6758" in df["code"].values

        finally:
            os.chdir(original_cwd)

    def test_save_to_csv_empty_data(self, scraper, temp_dir, capsys):
        """空データのCSV保存テスト"""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            scraper.save_to_csv([], "empty_test.csv")

            # エラーメッセージが出力されることを確認
            captured = capsys.readouterr()
            assert "保存するデータがありません" in captured.out

        finally:
            os.chdir(original_cwd)

    def test_print_summary(self, scraper, sample_stock_data, capsys):
        """サマリー表示のテスト"""
        scraper.print_summary(sample_stock_data)

        captured = capsys.readouterr()
        assert "取得結果サマリー" in captured.out
        assert "2 銘柄" in captured.out

    def test_parse_price(self, scraper):
        """価格パースのテスト"""
        # テスト用のメソッドを追加する場合
        pass

    @patch("yahoo_finance_scraper.time.sleep")
    @patch("yahoo_finance_scraper.YahooFinanceScraper.get_stock_info")
    def test_get_multiple_stocks(self, mock_get_stock_info, mock_sleep, scraper):
        """複数株式取得のテスト"""
        # モックの設定
        mock_get_stock_info.side_effect = [
            {"code": "7203", "name": "トヨタ自動車", "price": 2500.0},
            {"code": "6758", "name": "ソニーグループ", "price": 12000.0},
        ]

        stock_codes = ["7203", "6758"]
        results = scraper.get_multiple_stocks(stock_codes)

        assert len(results) == 2
        assert results[0]["code"] == "7203"
        assert results[1]["code"] == "6758"

        # sleep が呼ばれたことを確認
        assert mock_sleep.call_count == 2

    def test_get_popular_japanese_stocks(self, scraper):
        """人気日本株取得のテスト"""
        with patch.object(scraper, "get_multiple_stocks") as mock_get_multiple:
            mock_get_multiple.return_value = [
                {"code": "7203", "name": "トヨタ自動車"},
                {"code": "6758", "name": "ソニーグループ"},
            ]

            results = scraper.get_popular_japanese_stocks()

            assert len(results) == 2
            mock_get_multiple.assert_called_once()
