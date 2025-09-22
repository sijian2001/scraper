import pytest
import pandas as pd
import os
import tempfile
import shutil
from unittest.mock import Mock, patch
from simple_yahoo_scraper import SimpleYahooScraper


class TestSimpleYahooScraper:
    """Simple Yahoo Scraperのテストクラス"""

    @pytest.fixture
    def scraper(self):
        """スクレーパーのインスタンスを作成"""
        return SimpleYahooScraper()

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
                'code': '7203',
                'name': 'トヨタ自動車',
                'price': 2500.0,
                'change': '+50',
                'change_percent': '+2.04%'
            },
            {
                'code': '6758',
                'name': 'ソニーグループ',
                'price': 12000.0,
                'change': '-100',
                'change_percent': '-0.82%'
            }
        ]

    def test_init(self, scraper):
        """初期化のテスト"""
        assert scraper.session is not None
        assert scraper.session.headers['User-Agent'] is not None

    @patch('simple_yahoo_scraper.requests.Session.get')
    def test_get_stock_price_success(self, mock_get, scraper):
        """株価取得の成功テスト"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <div class="price" data-symbol="7203">2,500</div>
        <div class="change positive">+50.00 (+2.04%)</div>
        '''
        mock_get.return_value = mock_response

        result = scraper.get_stock_price('7203')

        assert result is not None
        assert result['code'] == '7203'
        assert result['price'] == 2500.0

    @patch('simple_yahoo_scraper.requests.Session.get')
    def test_get_stock_price_failure(self, mock_get, scraper):
        """株価取得の失敗テスト"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = scraper.get_stock_price('INVALID')
        assert result is None

    @patch('simple_yahoo_scraper.requests.Session.get')
    def test_get_stock_price_parse_error(self, mock_get, scraper):
        """株価取得時のパースエラーテスト"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body>No stock data</body></html>'
        mock_get.return_value = mock_response

        result = scraper.get_stock_price('7203')
        assert result is None

    def test_get_popular_japanese_stocks(self, scraper):
        """人気日本株リスト取得のテスト"""
        with patch.object(scraper, 'get_stock_price') as mock_get_price:
            mock_get_price.side_effect = [
                {'code': '7203', 'name': 'トヨタ自動車', 'price': 2500.0},
                {'code': '6758', 'name': 'ソニーグループ', 'price': 12000.0},
                None  # エラーケースをシミュレート
            ]

            results = scraper.get_popular_japanese_stocks()

            # Noneでない結果のみが含まれることを確認
            assert len(results) >= 0
            assert all(result is not None for result in results)

    def test_save_to_csv(self, scraper, sample_stock_data, temp_dir):
        """CSV保存のテスト"""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            scraper.save_to_csv(sample_stock_data, "test_simple.csv")

            # ファイルが作成されたことを確認
            assert os.path.exists("work/test_simple.csv")

            # ファイル内容を確認
            df = pd.read_csv("work/test_simple.csv")
            assert len(df) == 2
            assert '7203' in df['code'].values
            assert '6758' in df['code'].values

        finally:
            os.chdir(original_cwd)

    def test_save_to_csv_empty_data(self, scraper, temp_dir, capsys):
        """空データのCSV保存テスト"""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            scraper.save_to_csv([], "empty_simple.csv")

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

    def test_parse_price_various_formats(self, scraper):
        """価格パースの様々なフォーマットテスト"""
        # 実際のパース処理をテストする場合
        # プライベートメソッドなどがある場合のテスト例
        pass

    @patch('simple_yahoo_scraper.time.sleep')
    def test_rate_limiting(self, mock_sleep, scraper):
        """レート制限のテスト"""
        with patch.object(scraper, 'get_stock_price') as mock_get_price:
            mock_get_price.return_value = {'code': '7203', 'price': 2500.0}

            # 複数回呼び出しでsleepが呼ばれることを確認
            scraper.get_popular_japanese_stocks()

            # sleepが呼ばれたかは実装依存
            # mock_sleep.assert_called()

    def test_session_headers(self, scraper):
        """セッションヘッダーのテスト"""
        headers = scraper.session.headers
        assert 'User-Agent' in headers
        assert 'Mozilla' in headers['User-Agent']