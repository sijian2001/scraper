"""
pytest共通設定ファイル
全テストで共有されるフィクスチャや設定を定義
"""

import pytest
import os
import sys
import tempfile
import shutil
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def project_root_dir():
    """プロジェクトルートディレクトリのパスを返す"""
    return Path(__file__).parent


@pytest.fixture(scope="session")
def test_data_dir(project_root_dir):
    """テストデータディレクトリのパスを返す"""
    test_data_path = project_root_dir / "tests" / "data"
    test_data_path.mkdir(exist_ok=True)
    return test_data_path


@pytest.fixture
def temp_work_dir():
    """一時的なworkディレクトリを作成"""
    temp_dir = tempfile.mkdtemp()
    work_dir = os.path.join(temp_dir, "work")
    os.makedirs(work_dir, exist_ok=True)

    original_cwd = os.getcwd()
    os.chdir(temp_dir)

    yield temp_dir

    os.chdir(original_cwd)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_csv_data():
    """テスト用のサンプルCSVデータを返す"""
    return [
        {
            "code": "7203",
            "name": "トヨタ自動車",
            "price": 2500.0,
            "ytd_high": 2600.0,
            "ytd_low": 2000.0,
            "volume": 1000000,
            "market_cap": 35000000000000,
            "sector": "自動車・輸送機器",
        },
        {
            "code": "6758",
            "name": "ソニーグループ",
            "price": 12000.0,
            "ytd_high": 13000.0,
            "ytd_low": 10000.0,
            "volume": 500000,
            "market_cap": 15000000000000,
            "sector": "電気機器",
        },
    ]


@pytest.fixture
def mock_stock_response():
    """Yahoo FinanceのHTMLレスポンスをモック"""
    return """
    <html>
    <body>
        <div class="price" data-symbol="7203">2,500</div>
        <div class="change positive">+50.00 (+2.04%)</div>
        <td>年初来高値</td><td>2,600</td>
        <td>年初来安値</td><td>2,000</td>
        <span>出来高</span><span>1,000,000</span>
    </body>
    </html>
    """


def pytest_configure(config):
    """pytest設定の初期化"""
    # カスタムマーカーの登録
    config.addinivalue_line("markers", "slow: 時間のかかるテスト")
    config.addinivalue_line("markers", "integration: 統合テスト")
    config.addinivalue_line("markers", "unit: 単体テスト")
    config.addinivalue_line("markers", "network: ネットワーク接続が必要なテスト")


def pytest_collection_modifyitems(config, items):
    """テスト収集時の修正"""
    # ネットワークテストにマーカーを自動追加
    for item in items:
        if "network" in item.nodeid:
            item.add_marker(pytest.mark.network)


@pytest.fixture(autouse=True)
def cleanup_work_files():
    """テスト後にworkディレクトリをクリーンアップ"""
    yield

    # workディレクトリが存在する場合、テストで作成されたファイルを削除
    work_dir = Path("work")
    if work_dir.exists():
        for file_path in work_dir.glob("test_*.csv"):
            try:
                file_path.unlink()
            except Exception:
                pass  # ファイル削除に失敗しても続行


@pytest.fixture
def disable_network():
    """ネットワーク接続を無効にするフィクスチャ"""
    import socket

    def guard(*args, **kwargs):
        raise Exception("ネットワーク接続は無効になっています")

    original_socket = socket.socket
    socket.socket = guard

    yield

    socket.socket = original_socket
