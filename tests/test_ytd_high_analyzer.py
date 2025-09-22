import pytest
import pandas as pd
import numpy as np
import os
import tempfile
import shutil
from unittest.mock import Mock, patch
from ytd_high_analyzer import YTDHighAnalyzer


class TestYTDHighAnalyzer:
    """YTD High Analyzerのテストクラス"""

    @pytest.fixture
    def analyzer(self):
        """アナライザーのインスタンスを作成"""
        return YTDHighAnalyzer()

    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_df(self):
        """サンプルDataFrame"""
        return pd.DataFrame(
            [
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
                {
                    "code": "9984",
                    "name": "ソフトバンクグループ",
                    "price": 5000.0,
                    "ytd_high": 5100.0,
                    "ytd_low": 4000.0,
                    "volume": 800000,
                    "market_cap": 7000000000000,
                    "sector": "情報・通信業",
                },
            ]
        )

    def test_init(self, analyzer):
        """初期化のテスト"""
        assert analyzer is not None

    def test_calculate_ytd_high_ratio(self, analyzer, sample_df):
        """年初来高値比率計算のテスト"""
        result_df = analyzer.calculate_ytd_high_ratio(sample_df)

        assert "ytd_high_ratio" in result_df.columns
        assert len(result_df) == len(sample_df)

        # 計算結果の確認
        toyota_ratio = result_df[result_df["code"] == "7203"]["ytd_high_ratio"].iloc[0]
        expected_ratio = (2500.0 / 2600.0) * 100
        assert abs(toyota_ratio - expected_ratio) < 0.01

    def test_calculate_ytd_high_ratio_zero_division(self, analyzer):
        """年初来高値比率計算でゼロ除算のテスト"""
        df_with_zero = pd.DataFrame(
            [
                {
                    "code": "0000",
                    "name": "テスト",
                    "price": 100.0,
                    "ytd_high": 0.0,  # ゼロ除算を引き起こす
                    "ytd_low": 90.0,
                }
            ]
        )

        result_df = analyzer.calculate_ytd_high_ratio(df_with_zero)
        assert (
            pd.isna(result_df["ytd_high_ratio"].iloc[0])
            or result_df["ytd_high_ratio"].iloc[0] == 0
        )

    def test_calculate_volatility(self, analyzer, sample_df):
        """ボラティリティ計算のテスト"""
        result_df = analyzer.calculate_volatility(sample_df)

        assert "volatility" in result_df.columns
        assert len(result_df) == len(sample_df)

        # ボラティリティが正の値であることを確認
        assert all(result_df["volatility"] >= 0)

    def test_add_performance_metrics(self, analyzer, sample_df):
        """パフォーマンス指標追加のテスト"""
        result_df = analyzer.add_performance_metrics(sample_df)

        expected_columns = ["ytd_high_ratio", "volatility", "risk_score"]
        for col in expected_columns:
            assert col in result_df.columns

        # リスクスコアが適切な範囲にあることを確認
        assert all(result_df["risk_score"] >= 0)
        assert all(result_df["risk_score"] <= 100)

    def test_filter_by_criteria_market_cap(self, analyzer, sample_df):
        """時価総額フィルタリングのテスト"""
        # パフォーマンス指標を追加
        df_with_metrics = analyzer.add_performance_metrics(sample_df)

        criteria = {
            "min_market_cap": 10000000000000,  # 10兆円以上
            "max_market_cap": 40000000000000,  # 40兆円以下
        }

        result_df = analyzer.filter_by_criteria(df_with_metrics, criteria)

        # トヨタとソニーのみが残るはず
        assert len(result_df) == 2
        assert "7203" in result_df["code"].values
        assert "6758" in result_df["code"].values

    def test_filter_by_criteria_ytd_high_ratio(self, analyzer, sample_df):
        """年初来高値比率フィルタリングのテスト"""
        df_with_metrics = analyzer.add_performance_metrics(sample_df)

        criteria = {"min_ytd_high_ratio": 95.0}  # 95%以上

        result_df = analyzer.filter_by_criteria(df_with_metrics, criteria)

        # 年初来高値比率が95%以上の銘柄のみが残ることを確認
        assert all(result_df["ytd_high_ratio"] >= 95.0)

    def test_filter_by_criteria_sectors(self, analyzer, sample_df):
        """セクターフィルタリングのテスト"""
        df_with_metrics = analyzer.add_performance_metrics(sample_df)

        criteria = {"sectors": ["自動車・輸送機器", "電気機器"]}

        result_df = analyzer.filter_by_criteria(df_with_metrics, criteria)

        # 指定されたセクターの銘柄のみが残ることを確認
        assert len(result_df) == 2
        assert all(result_df["sector"].isin(["自動車・輸送機器", "電気機器"]))

    def test_save_analysis_results(self, analyzer, sample_df, temp_dir):
        """分析結果保存のテスト"""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            analyzer.save_analysis_results(sample_df, "test_ytd_high.csv")

            # ファイルが作成されたことを確認
            assert os.path.exists("work/test_ytd_high.csv")

            # ファイル内容を確認
            df = pd.read_csv("work/test_ytd_high.csv")
            assert len(df) == len(sample_df)

        finally:
            os.chdir(original_cwd)

    def test_save_analysis_results_empty_df(self, analyzer, temp_dir, capsys):
        """空DataFrameの保存テスト"""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            empty_df = pd.DataFrame()
            analyzer.save_analysis_results(empty_df, "empty_ytd_high.csv")

            # エラーメッセージが出力されることを確認
            captured = capsys.readouterr()
            assert "保存するデータがありません" in captured.out

        finally:
            os.chdir(original_cwd)

    def test_print_top_performers(self, analyzer, sample_df, capsys):
        """トップパフォーマー表示のテスト"""
        df_with_metrics = analyzer.add_performance_metrics(sample_df)

        analyzer.print_top_performers(df_with_metrics, top_n=2)

        captured = capsys.readouterr()
        assert "トップパフォーマー" in captured.out

    def test_analyze_ytd_highs_integration(self, analyzer):
        """年初来高値分析の統合テスト"""
        with patch("ytd_high_analyzer.pd.read_csv") as mock_read_csv:
            # モックデータを設定
            mock_df = pd.DataFrame(
                [
                    {
                        "code": "7203",
                        "name": "トヨタ自動車",
                        "price": 2500.0,
                        "ytd_high": 2600.0,
                        "ytd_low": 2000.0,
                        "volume": 1000000,
                        "market_cap": 35000000000000,
                        "sector": "自動車・輸送機器",
                    }
                ]
            )
            mock_read_csv.return_value = mock_df

            result_basic, result_detailed = analyzer.analyze_ytd_highs("dummy.csv")

            assert result_basic is not None
            assert "ytd_high_ratio" in result_basic.columns

            if result_detailed is not None:
                assert "risk_score" in result_detailed.columns

    def test_edge_cases_negative_prices(self, analyzer):
        """負の価格に対するエッジケースのテスト"""
        df_negative = pd.DataFrame(
            [
                {
                    "code": "0000",
                    "name": "テスト",
                    "price": -100.0,  # 負の価格
                    "ytd_high": 200.0,
                    "ytd_low": -150.0,
                    "volume": 1000,
                    "market_cap": 1000000000,
                    "sector": "テスト",
                }
            ]
        )

        result_df = analyzer.calculate_ytd_high_ratio(df_negative)

        # 負の価格に対する適切な処理がされているかを確認
        assert not pd.isna(result_df["ytd_high_ratio"].iloc[0])

    def test_large_dataset_performance(self, analyzer):
        """大きなデータセットでのパフォーマンステスト"""
        # 1000行のデータセットを作成
        large_df = pd.DataFrame(
            {
                "code": [f"{i:04d}" for i in range(1000)],
                "name": [f"テスト会社{i}" for i in range(1000)],
                "price": np.random.uniform(100, 10000, 1000),
                "ytd_high": np.random.uniform(150, 12000, 1000),
                "ytd_low": np.random.uniform(50, 8000, 1000),
                "volume": np.random.randint(1000, 10000000, 1000),
                "market_cap": np.random.uniform(1e9, 1e13, 1000),
                "sector": np.random.choice(["テクノロジー", "金融", "小売"], 1000),
            }
        )

        # パフォーマンス指標の計算が正常に完了することを確認
        result_df = analyzer.add_performance_metrics(large_df)
        assert len(result_df) == 1000
        assert "ytd_high_ratio" in result_df.columns
