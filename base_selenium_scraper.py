#!/usr/bin/env python3
"""
Base Selenium Scraper
Provides a base class for web scraping using Selenium WebDriver
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from typing import Optional
import time


class BaseSeleniumScraper:
    """
    Base class for Selenium-based web scraping

    Provides common functionality for:
    - WebDriver initialization and cleanup
    - Headless browser configuration
    - Wait and timeout handling
    - Page loading utilities
    """

    def __init__(self, headless: bool = True, timeout: int = 10):
        """
        Initialize the Selenium scraper

        Args:
            headless: Run browser in headless mode (default: True)
            timeout: Default timeout for page loads in seconds (default: 10)
        """
        self.headless = headless
        self.timeout = timeout
        self.driver: Optional[webdriver.Chrome] = None

    def _setup_driver(self) -> webdriver.Chrome:
        """
        Setup and configure Chrome WebDriver

        Returns:
            Configured Chrome WebDriver instance
        """
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')

        # 一般的な設定
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # ログレベルを抑制
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

        # WebDriverをセットアップ
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(self.timeout)

        return driver

    def start(self):
        """
        Start the WebDriver session
        """
        if self.driver is None:
            self.driver = self._setup_driver()

    def stop(self):
        """
        Stop and cleanup the WebDriver session
        """
        if self.driver:
            self.driver.quit()
            self.driver = None

    def get_page(self, url: str, wait_time: int = 2) -> str:
        """
        Load a page and return its HTML content

        Args:
            url: URL to load
            wait_time: Time to wait after page load in seconds (default: 2)

        Returns:
            Page HTML source
        """
        if not self.driver:
            self.start()

        self.driver.get(url)
        time.sleep(wait_time)  # ページが完全に読み込まれるまで待機

        return self.driver.page_source

    def wait_for_element(self, by: By, value: str, timeout: Optional[int] = None):
        """
        Wait for an element to be present on the page

        Args:
            by: Selenium By locator type
            value: Locator value
            timeout: Timeout in seconds (uses default if not specified)

        Returns:
            WebElement when found
        """
        if not self.driver:
            self.start()

        wait_timeout = timeout if timeout is not None else self.timeout
        wait = WebDriverWait(self.driver, wait_timeout)

        return wait.until(EC.presence_of_element_located((by, value)))

    def __enter__(self):
        """
        Context manager entry
        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit - ensures cleanup
        """
        self.stop()
        return False
