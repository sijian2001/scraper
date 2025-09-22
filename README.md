# Yahoo Finance Japan 株式分析ツール

Yahoo Finance Japan から年初来高値・安値データを取得し、詳細な分析を行うPythonツール集です。

## 概要

このツールセットは、Yahoo Finance Japan から以下のデータを取得・分析します：

1. **年初来高値更新銘柄**の取得と詳細分析
2. **年初来安値更新銘柄**の取得と回復ポテンシャル分析

各ツールは独立して動作し、投資判断の補助となる詳細な分析レポートを提供します。

## 主要機能

### 年初来高値分析
- 年初来高値更新銘柄の自動取得
- 銘柄の詳細情報（セクター、時価総額、PER等）
- 年初来リターン率の計算と分析
- パフォーマンストップランキング

### 年初来安値分析
- 年初来安値更新銘柄の自動取得
- 回復ポテンシャルの独自スコア算出
- バリュー投資候補の発見
- 安値からの回復率分析
- 技術指標を使用した総合評価

### 共通機能
- CSV形式での詳細データ保存
- コンソールでの分析レポート表示
- 複数のフィルタリング条件
- エラーハンドリング機能

## 必要な環境

- Python 3.7以上
- 仮想環境（推奨）

## セットアップ

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd login
```

### 2. 仮想環境の作成とアクティベート

```bash
# 仮想環境の作成（初回のみ）
python -m venv venv

# 仮想環境のアクティベート
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. 依存関係のインストール

```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 年初来高値分析

#### 簡易版スクレイパー
```bash
python simple_yahoo_scraper.py
```

#### 詳細分析版
```bash
python ytd_high_analyzer.py
```

### 2. 年初来安値分析・回復ポテンシャル分析

```bash
python ytd_low_analyzer.py
```

### 実行結果

各スクリプトを実行すると以下の処理が行われます：

#### 年初来高値分析
1. Yahoo Finance Japan から年初来高値更新銘柄を取得
2. yfinanceを使用した詳細な価格データ取得
3. 年初来リターン率と基本指標の計算
4. パフォーマンスランキングの表示
5. `ytd_high_basic.csv` および `ytd_high_detailed.csv` に保存

#### 年初来安値分析
1. Yahoo Finance Japan から年初来安値更新銘柄を取得
2. 安値からの回復率と回復ポテンシャルスコアを計算
3. バリュー投資候補の抽出
4. 回復可能性ランキングの表示
5. `ytd_low_basic.csv` および `ytd_low_detailed.csv` に保存

### 出力データ形式

#### 基本データ（全スクリプト共通）
| 項目名 | 説明 |
|--------|------|
| rank | ランキング順位 |
| stock_code | 銘柄コード（例：1305） |
| stock_name | 銘柄名（例：iFreeETF TOPIX） |
| market | 市場名 |
| yahoo_url | Yahoo Finance詳細ページURL |

#### 詳細分析データ（高値・安値分析）
| 項目名 | 説明 |
|--------|------|
| company_name | 会社名 |
| sector | セクター |
| industry | 業界 |
| current_price | 現在価格 |
| ytd_high/ytd_low | 年初来高値/安値 |
| ytd_return_pct | 年初来リターン率 |
| market_cap | 時価総額 |
| pe_ratio | PER（株価収益率） |
| pb_ratio | PBR（株価純資産倍率） |
| dividend_yield | 配当利回り |

#### 安値分析専用データ
| 項目名 | 説明 |
|--------|------|
| recovery_from_low_pct | 安値からの回復率 |
| recovery_score | 回復ポテンシャルスコア（0-100） |
| max_drawdown_pct | 最大ドローダウン |
| volatility_pct | 年率ボラティリティ |
| sma_20/sma_50 | 移動平均線（20日/50日） |

## ファイル構成

```
login/
├── README.md                    # このファイル
├── CLAUDE.md                   # 開発ガイダンス
├── requirements.txt            # 依存関係
├── simple_yahoo_scraper.py     # 簡易版年初来高値スクレイパー
├── ytd_high_analyzer.py        # 年初来高値詳細分析ツール
├── ytd_low_analyzer.py         # 年初来安値・回復ポテンシャル分析ツール
├── yahoo_finance_scraper.py    # 開発用スクリプト
├── yahoo_finance_ytd_highs.csv # 年初来高値データ
├── ytd_high_basic.csv          # 年初来高値基本データ
├── ytd_high_detailed.csv       # 年初来高値詳細分析データ
├── ytd_low_basic.csv           # 年初来安値基本データ
├── ytd_low_detailed.csv        # 年初来安値詳細分析データ
└── venv/                       # 仮想環境
```

## 主要な依存関係

- `requests` - HTTPリクエスト処理
- `beautifulsoup4` - HTMLパース
- `pandas` - データ処理とCSV出力
- `lxml` - XMLパーサー
- `yfinance` - 株価データ取得
- `numpy` - 数値計算

## 注意事項

### レート制限

- Yahoo Finance Japan のサーバーに負荷をかけないよう、適切な間隔でリクエストを送信してください
- 連続実行する場合は間隔を空けることを推奨します

### データの正確性

- 取得されるデータはスクレイピング時点の情報です
- リアルタイムデータではないため、投資判断には注意が必要です
- 公式のAPIやデータフィードの使用を検討してください

### ウェブサイトの変更

- Yahoo Finance Japan のHTML構造が変更された場合、スクリプトが動作しなくなる可能性があります
- その場合はスクリプトの修正が必要です

## トラブルシューティング

### よくある問題

1. **データが取得できない**
   - インターネット接続を確認
   - Yahoo Finance Japan のサイトがアクセス可能か確認
   - User-Agentの更新が必要な場合があります

2. **文字化けが発生する**
   - CSVファイルはUTF-8（BOM付き）で保存されています
   - Excelで開く場合は文字エンコーディングを確認してください

3. **依存関係のエラー**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt --force-reinstall
   ```

## 開発情報

### 主なクラスとメソッド

#### SimpleYahooFinanceJapanScraper（簡易版）
- `get_stocks_from_html()`: HTMLからの株式データ抽出
- `save_to_csv()`: CSVファイルへの保存
- `print_summary()`: 結果の表示

#### YearToDateHighAnalyzer（高値分析）
- `get_ytd_high_stocks()`: 年初来高値更新銘柄取得
- `get_detailed_stock_info()`: 個別銘柄詳細情報取得
- `analyze_ytd_performance()`: パフォーマンス分析
- `filter_stocks()`: 銘柄フィルタリング

#### YearToDateLowAnalyzer（安値分析）
- `get_ytd_low_stocks()`: 年初来安値更新銘柄取得
- `analyze_recovery_potential()`: 回復ポテンシャル分析
- `calculate_recovery_score()`: 回復スコア算出
- `filter_recovery_candidates()`: 回復候補フィルタリング

### 回復スコア算出ロジック

年初来安値分析では、独自の回復ポテンシャルスコア（0-100点）を算出します：

- **ベーススコア**: 50点
- **安値からの回復率**: +15点（20%以上）、+10点（10%以上）、+5点（5%以上）
- **PBR**: +15点（1.0未満）、+10点（1.5未満）
- **PER**: +10点（5-15の適正範囲）
- **配当利回り**: +10点（3%以上）
- **移動平均線**: +15点（上昇トレンド）、+5点（短期上昇）
- **ボラティリティ**: +5点（30%未満の安定性）
- **下落率**: +10点（50%以上の深い下落）、+5点（30%以上）

### カスタマイズ

スクリプトは以下の点でカスタマイズ可能です：

- 取得ページ数・銘柄数の変更
- フィルタリング条件の調整
- 回復スコアアルゴリズムの修正
- 出力フォーマットの変更
- 追加指標の計算

## ライセンス

このプロジェクトは教育および個人利用目的で作成されています。商用利用の場合は適切なライセンスを確認してください。

## 使用例とヒント

### 投資戦略への活用例

#### 1. 成長株の発見（年初来高値分析）
```bash
python ytd_high_analyzer.py
```
- 年初来リターン20%以上の銘柄を特定
- セクター別パフォーマンス比較
- 時価総額や流動性による絞り込み

#### 2. バリュー投資候補の発見（年初来安値分析）
```bash
python ytd_low_analyzer.py
```
- PBR 1.5未満の割安銘柄を抽出
- 回復スコア70点以上の有望候補を特定
- 配当利回り3%以上の銘柄をピックアップ

#### 3. 市場トレンドの把握
- セクター別の高値・安値更新銘柄数を比較
- 全体的な市場センチメントの把握
- ETFの動向による指数の健全性確認

### パフォーマンス最適化のコツ

- **レート制限**: 大量データ取得時は `time.sleep()` の値を調整
- **メモリ使用量**: 大きなデータセットの場合は分割処理
- **ネットワーク**: 安定したインターネット接続で実行

## 免責事項

- このツールは情報提供目的のみです
- 投資判断における使用は自己責任でお願いします
- Yahoo Finance Japan の利用規約を遵守してください
- データの正確性については保証いたしません
- 回復スコアは独自アルゴリズムによる参考値です

## サポート

問題が発生した場合は、以下の情報と共にお問い合わせください：

- Python バージョン
- エラーメッセージ
- 実行環境（OS等）
- 実行時の状況

---

## 更新履歴

- **2025年9月21日 v2.0**: 年初来安値分析・回復ポテンシャル分析機能を追加
- **2025年9月21日 v1.1**: 年初来高値詳細分析機能を追加
- **2025年9月21日 v1.0**: 初期リリース（簡易版スクレイパー）

**最終更新日**: 2025年9月21日