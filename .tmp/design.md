# 要件定義: webdriverとseleniumの導入

## 概要
既存のスクレーピングコードにSeleniumとWebDriverを導入し、動的コンテンツのスクレイピングに対応する。

## 背景
現在のスクレーパーは`requests`と`BeautifulSoup`を使用しているが、Yahoo Finance Japanのような動的にコンテンツを生成するサイトでは、JavaScriptで生成されるコンテンツを取得できない可能性がある。

## 目標
1. Selenium WebDriverをプロジェクトに導入
2. 既存のスクレーピングコードをSeleniumベースに移行
3. 動的コンテンツの取得を可能にする

## 技術要件

### 1. 依存関係の追加
- `selenium>=4.0.0`: WebDriver制御用
- `webdriver-manager>=4.0.0`: WebDriverの自動管理用

### 2. 対象ファイル
- `base_selenium_scraper.py`: Selenium WebDriverの共通ベースクラス（新規作成）
- `simple_yahoo_scraper.py`: 簡易版Yahoo Financeスクレーパー
- `yahoo_finance_scraper.py`: Yahoo Financeスクレーパー
- `ytd_high_analyzer.py`: 年初来高値分析スクリプト
- `ytd_low_analyzer.py`: 年初来安値分析スクリプト
- `stop_low_scraper.py`: ストップ安スクレーパー

### 3. 実装方針
- Chrome WebDriverを使用（ヘッドレスモード対応）
- ベースクラス(`BaseSeleniumScraper`)を作成し、共通機能を提供
  - WebDriverの初期化と設定
  - コンテキストマネージャー対応（自動クリーンアップ）
  - ページ取得の共通メソッド
- 既存のスクレーパークラスをベースクラスから継承
- HTMLスクレイピング部分をSeleniumに置き換え（BeautifulSoupは引き続き使用）
- API呼び出しなど軽量な処理はrequestsを維持

### 4. 互換性
- 既存のインターフェース（メソッド名、戻り値）を維持
- CSVファイル保存機能は変更なし
- yfinanceによる詳細データ取得は変更なし

## 実装結果

### ベースクラス
`base_selenium_scraper.py`に以下の機能を実装：
- WebDriverの初期化と設定（ヘッドレスモード、タイムアウト設定）
- コンテキストマネージャー対応（`with`文でのリソース管理）
- ページ取得メソッド（`get_page`）
- 要素待機メソッド（`wait_for_element`）

### 移行済みスクレーパー
すべてのスクレーパーを`BaseSeleniumScraper`を継承するように変更：
1. `SimpleYahooFinanceJapanScraper`
2. `YahooFinanceJapanScraper`
3. `YearToDateHighAnalyzer`
4. `YearToDateLowAnalyzer`
5. `StopLowScraper`

### テスト
- `tests/test_base_selenium_scraper.py`: ベースクラスのユニットテスト
- `tests/test_selenium_integration.py`: 全スクレーパーの統合テスト

## 非機能要件
- パフォーマンス: Seleniumによるオーバーヘッドがあるが、動的コンテンツ取得の信頼性を優先
- 保守性: ベースクラスによる共通化でコードの保守性を向上
- テスタビリティ: テストを実装し、動作を確認

## 使用方法
```python
# コンテキストマネージャーを使用（推奨）
with SimpleYahooFinanceJapanScraper(headless=True) as scraper:
    stocks = scraper.get_stocks_from_html(page=1)
    # WebDriverは自動的にクリーンアップされる

# 手動での制御も可能
scraper = SimpleYahooFinanceJapanScraper(headless=True)
scraper.start()
stocks = scraper.get_stocks_from_html(page=1)
scraper.stop()
```
