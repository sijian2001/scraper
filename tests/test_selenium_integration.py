#!/usr/bin/env python3
"""
Selenium統合の簡易動作確認スクリプト
各スクレーパーの初期化とWebDriver起動のテスト
"""

from simple_yahoo_scraper import SimpleYahooFinanceJapanScraper
from yahoo_finance_scraper import YahooFinanceJapanScraper
from ytd_high_analyzer import YearToDateHighAnalyzer
from ytd_low_analyzer import YearToDateLowAnalyzer
from stop_low_scraper import StopLowScraper


def test_scraper_initialization():
    """
    各スクレーパーの初期化をテスト
    """
    print("=== Selenium統合テスト ===\n")

    scrapers = [
        ("SimpleYahooFinanceJapanScraper", SimpleYahooFinanceJapanScraper),
        ("YahooFinanceJapanScraper", YahooFinanceJapanScraper),
        ("YearToDateHighAnalyzer", YearToDateHighAnalyzer),
        ("YearToDateLowAnalyzer", YearToDateLowAnalyzer),
        ("StopLowScraper", StopLowScraper),
    ]

    for name, scraper_class in scrapers:
        print(f"テスト中: {name}")

        # context managerでWebDriverを起動・停止
        with scraper_class(headless=True) as scraper:
            print(f"  OK: {name}: WebDriverの起動・停止に成功")
            # WebDriverが正常に初期化されているか確認
            assert scraper.driver is not None, f"{name}: WebDriverが初期化されていません"

        # context manager終了後、WebDriverがクリーンアップされているか確認
        assert scraper.driver is None, f"{name}: WebDriverがクリーンアップされていません"

    print("\n=== すべてのテストが成功しました ===")
