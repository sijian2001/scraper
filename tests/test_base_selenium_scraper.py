#!/usr/bin/env python3
"""
Test cases for BaseSeleniumScraper
"""

import pytest
from base_selenium_scraper import BaseSeleniumScraper


class TestBaseSeleniumScraper:
    """
    Test BaseSeleniumScraper class
    """

    def test_initialization(self):
        """
        Test scraper initialization
        """
        scraper = BaseSeleniumScraper(headless=True, timeout=5)
        assert scraper.headless is True
        assert scraper.timeout == 5
        assert scraper.driver is None

    def test_context_manager(self):
        """
        Test context manager functionality
        """
        with BaseSeleniumScraper(headless=True) as scraper:
            assert scraper.driver is not None

        # WebDriverがクリーンアップされているか確認
        assert scraper.driver is None

    def test_start_stop(self):
        """
        Test manual start and stop
        """
        scraper = BaseSeleniumScraper(headless=True)

        # start前はNone
        assert scraper.driver is None

        # startでWebDriverが初期化される
        scraper.start()
        assert scraper.driver is not None

        # stopでクリーンアップ
        scraper.stop()
        assert scraper.driver is None

    @pytest.mark.skip(reason="Requires internet connection and may be slow")
    def test_get_page(self):
        """
        Test page loading (requires internet connection)
        """
        with BaseSeleniumScraper(headless=True) as scraper:
            # Googleのページを取得してテスト
            html_content = scraper.get_page("https://www.google.com", wait_time=1)

            # HTMLコンテンツが取得できていることを確認
            assert html_content is not None
            assert len(html_content) > 0
            assert "google" in html_content.lower()
