import pytest
import pandas as pd
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from bs4 import BeautifulSoup
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from stop_low_scraper import StopLowScraper


class TestStopLowScraper:
    """ストップ安スクレイパーのテストクラス"""

    @pytest.fixture
    def scraper(self):
        """スクレーパーのインスタンスを作成"""
        return StopLowScraper()

    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_stop_low_data(self):
        """サンプルストップ安データ"""
        return [
            {
                'rank': 1,
                'stock_code': '1234',
                'stock_name': 'テスト銘柄A',
                'market': 'プライム',
                'url': 'https://finance.yahoo.co.jp/quote/1234.T',
                'current_price': '500',
                'change_value': '-80',
                'change_rate': '-13.79%',
                'volume': '1,000,000',
                'scrape_date': '2025-09-22 10:00:00'
            },
            {
                'rank': 2,
                'stock_code': '5678',
                'stock_name': 'テスト銘柄B',
                'market': 'スタンダード',
                'url': 'https://finance.yahoo.co.jp/quote/5678.T',
                'current_price': '200',
                'change_value': '-35',
                'change_rate': '-14.89%',
                'volume': '500,000',
                'scrape_date': '2025-09-22 10:00:00'
            }
        ]

    @pytest.fixture
    def mock_html_response(self):
        """モックHTMLレスポンス"""
        return """
        <html>
        <body>
        <table class="rankingTable">
            <thead>
                <tr><th>順位</th><th>銘柄</th><th>現在値</th><th>前日比</th><th>騰落率</th><th>出来高</th></tr>
            </thead>
            <tbody>
                <tr>
                    <td>1.</td>
                    <td>
                        <a href="/quote/1234.T">テスト銘柄A</a>
                        <span>プライム</span>
                    </td>
                    <td>500</td>
                    <td>-80</td>
                    <td>-13.79%</td>
                    <td>1,000,000</td>
                </tr>
                <tr>
                    <td>2.</td>
                    <td>
                        <a href="/quote/5678.T">テスト銘柄B</a>
                        <span>スタンダード</span>
                    </td>
                    <td>200</td>
                    <td>-35</td>
                    <td>-14.89%</td>
                    <td>500,000</td>
                </tr>
            </tbody>
        </table>
        </body>
        </html>
        """

    def test_init(self, scraper):
        """初期化のテスト"""
        assert scraper.session is not None
        assert scraper.base_url == "https://finance.yahoo.co.jp/stocks/ranking/stopLow"
        assert 'User-Agent' in scraper.session.headers
        assert 'Mozilla' in scraper.session.headers['User-Agent']

    @patch('stop_low_scraper.requests.Session.get')
    def test_scrape_page_success(self, mock_get, scraper, mock_html_response):
        """ページスクレイピング成功のテスト"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = mock_html_response
        mock_get.return_value = mock_response

        result = scraper._scrape_page(1, "all", "daily")

        assert len(result) == 2
        assert result[0]['stock_code'] == '1234'
        assert result[0]['stock_name'] == 'テスト銘柄A'
        assert result[1]['stock_code'] == '5678'
        assert result[1]['stock_name'] == 'テスト銘柄B'

    @patch('stop_low_scraper.requests.Session.get')
    def test_scrape_page_network_error(self, mock_get, scraper):
        """ネットワークエラーのテスト"""
        mock_get.side_effect = Exception("Network error")

        result = scraper._scrape_page(1, "all", "daily")

        assert result == []

    @patch('stop_low_scraper.requests.Session.get')
    def test_scrape_page_http_error(self, mock_get, scraper):
        """HTTPエラーのテスト"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")
        mock_get.return_value = mock_response

        result = scraper._scrape_page(1, "all", "daily")

        assert result == []

    def test_parse_stock_data_empty_html(self, scraper):
        """空のHTMLのパーステスト"""
        soup = BeautifulSoup("<html><body></body></html>", 'html.parser')
        result = scraper._parse_stock_data(soup)
        assert result == []

    def test_parse_stock_data_no_table(self, scraper):
        """テーブルなしHTMLのパーステスト"""
        soup = BeautifulSoup("<html><body><div>No table here</div></body></html>", 'html.parser')
        result = scraper._parse_stock_data(soup)
        assert result == []

    def test_parse_stock_row_valid_data(self, scraper):
        """有効な株式行データのパーステスト"""
        html = """
        <tr>
            <td>1.</td>
            <td>
                <a href="/quote/1234.T">テスト銘柄</a>
                <span>プライム</span>
            </td>
            <td>500</td>
            <td>-80</td>
            <td>-13.79%</td>
        </tr>
        """
        soup = BeautifulSoup(html, 'html.parser')
        row = soup.find('tr')

        result = scraper._parse_stock_row(row, 1)

        assert result is not None
        assert result['rank'] == 1
        assert result['stock_code'] == '1234'
        assert result['stock_name'] == 'テスト銘柄'
        assert result['market'] == 'プライム'
        assert result['current_price'] == '500'

    def test_parse_stock_row_invalid_data(self, scraper):
        """無効な株式行データのパーステスト"""
        html = "<tr><td>invalid</td></tr>"
        soup = BeautifulSoup(html, 'html.parser')
        row = soup.find('tr')

        result = scraper._parse_stock_row(row, 1)

        assert result is None

    def test_extract_stock_code_from_url(self, scraper):
        """URLからの銘柄コード抽出テスト"""
        href = "/quote/1234.T"
        cell = BeautifulSoup("<td></td>", 'html.parser').find('td')

        code = scraper._extract_stock_code(href, cell, 1)

        assert code == "1234"

    def test_extract_stock_code_from_cell(self, scraper):
        """セルからの銘柄コード抽出テスト"""
        href = "/invalid"
        cell = BeautifulSoup("<td>5678 テスト銘柄</td>", 'html.parser').find('td')

        code = scraper._extract_stock_code(href, cell, 1)

        assert code == "5678"

    def test_extract_stock_code_fallback(self, scraper):
        """銘柄コード抽出のフォールバックテスト"""
        href = "/invalid"
        cell = BeautifulSoup("<td>no code here</td>", 'html.parser').find('td')

        code = scraper._extract_stock_code(href, cell, 5)

        assert code == "UNKNOWN_5"

    def test_extract_price_data(self, scraper):
        """価格データ抽出のテスト"""
        html = """
        <div>
            <td>500</td>
            <td>-80</td>
            <td>-13.79%</td>
            <td>1,000,000</td>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        cells = soup.find_all('td')

        result = scraper._extract_price_data(cells)

        assert result['current_price'] == '500'
        assert result['change_value'] == '-80'
        assert result['change_rate'] == '-13.79%'
        assert result['volume'] == '1,000,000'

    @patch('stop_low_scraper.StopLowScraper._scrape_page')
    def test_get_stop_low_stocks_success(self, mock_scrape, scraper, sample_stop_low_data):
        """ストップ安銘柄取得成功のテスト"""
        mock_scrape.side_effect = [
            sample_stop_low_data[:1],  # 1ページ目
            sample_stop_low_data[1:],  # 2ページ目
            []  # 3ページ目は空
        ]

        with patch('time.sleep'):
            result = scraper.get_stop_low_stocks(pages=3)

        assert len(result) == 2
        assert result[0]['stock_code'] == '1234'
        assert result[1]['stock_code'] == '5678'

    @patch('stop_low_scraper.StopLowScraper._scrape_page')
    def test_get_stop_low_stocks_empty_first_page(self, mock_scrape, scraper):
        """最初のページが空の場合のテスト"""
        mock_scrape.return_value = []

        result = scraper.get_stop_low_stocks(pages=1)

        assert result == []

    def test_save_to_csv(self, scraper, sample_stop_low_data, temp_dir):
        """CSV保存のテスト"""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            scraper.save_to_csv(sample_stop_low_data, "test_stop_low.csv")

            # ファイルが作成されたことを確認
            assert os.path.exists("work/test_stop_low.csv")

            # ファイル内容を確認
            df = pd.read_csv("work/test_stop_low.csv")
            assert len(df) == 2
            assert '1234' in df['stock_code'].values
            assert '5678' in df['stock_code'].values

        finally:
            os.chdir(original_cwd)

    def test_save_to_csv_empty_data(self, scraper, temp_dir, capsys):
        """空データのCSV保存テスト"""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            scraper.save_to_csv([], "empty_stop_low.csv")

            captured = capsys.readouterr()
            assert "保存するデータがありません" in captured.out

        finally:
            os.chdir(original_cwd)

    def test_print_summary(self, scraper, sample_stop_low_data, capsys):
        """サマリー表示のテスト"""
        scraper.print_summary(sample_stop_low_data)

        captured = capsys.readouterr()
        assert "ストップ安銘柄 取得結果" in captured.out
        assert "総銘柄数: 2" in captured.out
        assert "テスト銘柄A" in captured.out
        assert "テスト銘柄B" in captured.out

    def test_print_summary_empty_data(self, scraper, capsys):
        """空データのサマリー表示テスト"""
        scraper.print_summary([])

        captured = capsys.readouterr()
        assert "データがありません" in captured.out

    def test_analyze_stop_low_patterns(self, scraper, sample_stop_low_data):
        """ストップ安パターン分析のテスト"""
        result = scraper.analyze_stop_low_patterns(sample_stop_low_data)

        assert result['total_count'] == 2
        assert 'market_distribution' in result
        assert result['market_distribution']['プライム'] == 1
        assert result['market_distribution']['スタンダード'] == 1
        assert 'volume_analysis' in result
        assert result['volume_analysis']['average_volume'] == 750000.0

    def test_analyze_stop_low_patterns_empty_data(self, scraper):
        """空データの分析テスト"""
        result = scraper.analyze_stop_low_patterns([])

        assert result == {}

    def test_print_analysis_report(self, scraper, capsys):
        """分析レポート表示のテスト"""
        analysis = {
            'timestamp': '2025-09-22 10:00:00',
            'total_count': 10,
            'market_distribution': {'プライム': 6, 'スタンダード': 4},
            'volume_analysis': {
                'average_volume': 1000000.0,
                'max_volume': 2000000,
                'min_volume': 500000,
                'sample_size': 8
            }
        }

        scraper.print_analysis_report(analysis)

        captured = capsys.readouterr()
        assert "ストップ安銘柄 分析レポート" in captured.out
        assert "対象銘柄数: 10" in captured.out
        assert "プライム: 6 銘柄" in captured.out
        assert "平均出来高: 1,000,000 株" in captured.out

    def test_print_analysis_report_empty_data(self, scraper, capsys):
        """空分析データのレポート表示テスト"""
        scraper.print_analysis_report({})

        captured = capsys.readouterr()
        assert "分析データがありません" in captured.out

    @patch('stop_low_scraper.datetime')
    def test_timestamp_in_stock_data(self, mock_datetime, scraper):
        """株式データのタイムスタンプテスト"""
        mock_datetime.now.return_value.strftime.return_value = '2025-09-22 15:30:00'

        html = """
        <tr>
            <td>1.</td>
            <td><a href="/quote/1234.T">テスト銘柄</a></td>
            <td>500</td>
        </tr>
        """
        soup = BeautifulSoup(html, 'html.parser')
        row = soup.find('tr')

        result = scraper._parse_stock_row(row, 1)

        assert result['scrape_date'] == '2025-09-22 15:30:00'

    def test_session_configuration(self, scraper):
        """セッション設定のテスト"""
        headers = scraper.session.headers
        assert 'User-Agent' in headers
        assert 'Accept' in headers
        assert 'Accept-Language' in headers
        assert 'Connection' in headers
        assert 'Referer' in headers

    @patch('stop_low_scraper.time.sleep')
    @patch('stop_low_scraper.StopLowScraper._scrape_page')
    def test_rate_limiting(self, mock_scrape, mock_sleep, scraper):
        """レート制限のテスト"""
        mock_scrape.side_effect = [
            [{'rank': 1, 'stock_code': '1234'}],
            [{'rank': 2, 'stock_code': '5678'}],
            []
        ]

        scraper.get_stop_low_stocks(pages=3)

        # sleepが各ページ間で呼ばれることを確認
        assert mock_sleep.call_count >= 2

    def test_url_construction_in_parse_stock_row(self, scraper):
        """株式行パース時のURL構築テスト"""
        html = """
        <tr>
            <td>1.</td>
            <td><a href="/quote/1234.T">テスト銘柄</a></td>
            <td>500</td>
        </tr>
        """
        soup = BeautifulSoup(html, 'html.parser')
        row = soup.find('tr')

        result = scraper._parse_stock_row(row, 1)

        assert result['url'] == "https://finance.yahoo.co.jp/quote/1234.T"

    def test_robust_parsing_with_missing_elements(self, scraper):
        """要素不足時の堅牢なパーステスト"""
        html = """
        <tr>
            <td>1.</td>
            <td><a href="/quote/1234.T">テスト銘柄</a></td>
        </tr>
        """
        soup = BeautifulSoup(html, 'html.parser')
        row = soup.find('tr')

        result = scraper._parse_stock_row(row, 1)

        assert result is not None
        assert result['stock_code'] == '1234'
        # 価格データが不足していても処理が継続されることを確認