# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

This is a Python project with a virtual environment set up.

### Virtual Environment
- **Activate**: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Linux/Mac)
- **Deactivate**: `deactivate`
- **Install dependencies**: `pip install -r requirements.txt` (when requirements.txt is created)

## Development Commands

### Python Environment
- Activate environment: `venv\Scripts\activate`
- Install packages: `pip install [package_name]`
- Generate requirements: `pip freeze > requirements.txt`
- Install from requirements: `pip install -r requirements.txt`

### Testing
- Run all tests: `pytest tests/`
- Run specific test file: `pytest tests/test_[module_name].py`
- Run specific test: `pytest tests/test_[module_name].py::test_[function_name]`
- Run tests with coverage: `pytest tests/ --cov=.`
- Run tests in parallel: `pytest tests/ -n auto`
- Generate HTML test report: `pytest tests/ --html=work/test_report.html`

### Code Quality (to be added when tools are chosen)
- Lint: `[command to be added]`
- Format: `[command to be added]`

## Architecture

This section will be updated as the codebase develops.

# プロジェクト基本情報

このプロジェクトは Python で書かれた Web アプリケーションです。

# 共通コマンド

- `npm run build`: プロジェクトのビルド実行
- `pytest tests/`: テストスイート実行
- `black .`: コードフォーマット適用

# コードスタイル

- ES6 モジュール構文（import/export）を使用
- 可能な限り分割代入を活用
- 関数名は snake_case、クラス名は PascalCase で統一

# ワークフロー

- 変更完了後は必ず型チェックを実行
- 全テストではなく単体テストを優先して実行

## タスク着手時のワークフロー

1. タスクの状態を「着手中」に変更
2. タスクの開始日時を設定 (時間まで記載すること)
3. Git で develop からブランチを作成 (ブランチ名は`feature/<タスクID>`とする)
4. 空コミットを作成 (コミットメッセージは`chore: start feature/<タスクID>`とする)
5. PR を作成 (`gh pr create --assignee @me --base develop --draft`)
  - タイトルはタスクのタイトルを参照する (`【<タスクID>】<タイトル>`)
  - ボディはタスクの内容から生成する (Notion タスクへのリンクを含める)
6. 実装計画を考えて、ユーザーに伝える
7. ユーザーにプロンプトを返す

## タスク完了時のワークフロー

1. PR のステータスを ready にする
2. PR をマージ (`gh pr merge --merge --auto --delete-branch`)
3. タスクの開始日時を設定 (時間まで記載すること)
4. タスクに「サマリー」を追加
  - コマンドライン履歴とコンテキストを参照して、振り返りを効率かするための文章を作成
  - Notion の見出しは「振り返り」とする
5. タスクの状態を「完了」に変更
6. タスクの完了日時を記載 (時間まで記載すること)
7. ユーザーにプロンプトを返す
