import pytest
import pandas as pd
import numpy as np
import os
import tempfile
import shutil
from unittest.mock import Mock, patch
from ytd_low_analyzer import YTDLowAnalyzer


class TestYTDLowAnalyzer:
    """YTD Low Analyzerのテストクラス"""

    @pytest.fixture
    def analyzer(self):
        """アナライザーのインスタンスを作成"""
        return YTDLowAnalyzer()

    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_df(self):
        """サンプルDataFrame"""
        return pd.DataFrame([
            {
                'code': '7203',
                'name': 'トヨタ自動車',
                'price': 2200.0,
                'ytd_high': 2600.0,
                'ytd_low': 2000.0,
                'volume': 1000000,
                'market_cap': 35000000000000,
                'sector': '自動車・輸送機器',
                'pe_ratio': 12.5,
                'pb_ratio': 1.2
            },
            {
                'code': '6758',
                'name': 'ソニーグループ',
                'price': 10500.0,
                'ytd_high': 13000.0,
                'ytd_low': 10000.0,
                'volume': 500000,
                'market_cap': 15000000000000,
                'sector': '電気機器',
                'pe_ratio': 15.2,
                'pb_ratio': 2.1
            },
            {
                'code': '8058',
                'name': '三菱商事',
                'price': 4200.0,
                'ytd_high': 5000.0,
                'ytd_low': 4000.0,
                'volume': 800000,
                'market_cap': 6000000000000,
                'sector': '卸売業',
                'pe_ratio': 8.5,
                'pb_ratio': 0.9
            }
        ])

    def test_init(self, analyzer):
        """初期化のテスト"""
        assert analyzer is not None

    def test_calculate_ytd_low_distance(self, analyzer, sample_df):
        """年初来安値からの距離計算のテスト"""
        result_df = analyzer.calculate_ytd_low_distance(sample_df)

        assert 'ytd_low_distance' in result_df.columns
        assert len(result_df) == len(sample_df)

        # 計算結果の確認
        toyota_distance = result_df[result_df['code'] == '7203']['ytd_low_distance'].iloc[0]
        expected_distance = ((2200.0 - 2000.0) / 2000.0) * 100
        assert abs(toyota_distance - expected_distance) < 0.01

    def test_calculate_ytd_low_distance_zero_division(self, analyzer):
        """年初来安値距離計算でゼロ除算のテスト"""
        df_with_zero = pd.DataFrame([
            {
                'code': '0000',
                'name': 'テスト',
                'price': 100.0,
                'ytd_high': 120.0,
                'ytd_low': 0.0,  # ゼロ除算を引き起こす
                'volume': 1000
            }
        ])

        result_df = analyzer.calculate_ytd_low_distance(df_with_zero)
        # ゼロ除算の場合の適切な処理がされているかを確認
        assert pd.isna(result_df['ytd_low_distance'].iloc[0]) or result_df['ytd_low_distance'].iloc[0] == float('inf')

    def test_calculate_recovery_potential(self, analyzer, sample_df):
        """回復ポテンシャル計算のテスト"""
        result_df = analyzer.calculate_recovery_potential(sample_df)

        assert 'recovery_potential' in result_df.columns
        assert len(result_df) == len(sample_df)

        # 回復ポテンシャルが正の値であることを確認
        assert all(result_df['recovery_potential'] >= 0)

    def test_calculate_value_metrics(self, analyzer, sample_df):
        """バリュー指標計算のテスト"""
        result_df = analyzer.calculate_value_metrics(sample_df)

        expected_columns = ['value_score']
        for col in expected_columns:
            assert col in result_df.columns

        # バリュースコアが適切な範囲にあることを確認
        assert all(result_df['value_score'] >= 0)

    def test_add_recovery_analysis(self, analyzer, sample_df):
        """回復分析指標追加のテスト"""
        result_df = analyzer.add_recovery_analysis(sample_df)

        expected_columns = ['ytd_low_distance', 'recovery_potential', 'value_score', 'overall_score']
        for col in expected_columns:
            assert col in result_df.columns

        # 総合スコアが適切な範囲にあることを確認
        assert all(result_df['overall_score'] >= 0)
        assert all(result_df['overall_score'] <= 100)

    def test_filter_by_recovery_criteria_ytd_low_distance(self, analyzer, sample_df):
        """年初来安値距離フィルタリングのテスト"""
        df_with_analysis = analyzer.add_recovery_analysis(sample_df)

        criteria = {
            'max_ytd_low_distance': 15.0  # 15%以下
        }

        result_df = analyzer.filter_by_recovery_criteria(df_with_analysis, criteria)

        # 年初来安値距離が15%以下の銘柄のみが残ることを確認
        assert all(result_df['ytd_low_distance'] <= 15.0)

    def test_filter_by_recovery_criteria_pe_ratio(self, analyzer, sample_df):
        """PERフィルタリングのテスト"""
        df_with_analysis = analyzer.add_recovery_analysis(sample_df)

        criteria = {
            'max_pe_ratio': 10.0  # PER 10倍以下
        }

        result_df = analyzer.filter_by_recovery_criteria(df_with_analysis, criteria)

        # PER10倍以下の銘柄のみが残ることを確認
        assert all(result_df['pe_ratio'] <= 10.0)

    def test_filter_by_recovery_criteria_market_cap(self, analyzer, sample_df):
        """時価総額フィルタリングのテスト"""
        df_with_analysis = analyzer.add_recovery_analysis(sample_df)

        criteria = {
            'min_market_cap': 10000000000000,  # 10兆円以上
            'max_market_cap': 40000000000000   # 40兆円以下
        }

        result_df = analyzer.filter_by_recovery_criteria(df_with_analysis, criteria)

        # 指定範囲の時価総額の銘柄のみが残ることを確認
        assert all(result_df['market_cap'] >= 10000000000000)
        assert all(result_df['market_cap'] <= 40000000000000)

    def test_filter_by_recovery_criteria_sectors(self, analyzer, sample_df):
        """セクターフィルタリングのテスト"""
        df_with_analysis = analyzer.add_recovery_analysis(sample_df)

        criteria = {
            'sectors': ['自動車・輸送機器', '電気機器']
        }

        result_df = analyzer.filter_by_recovery_criteria(df_with_analysis, criteria)

        # 指定されたセクターの銘柄のみが残ることを確認
        assert all(result_df['sector'].isin(['自動車・輸送機器', '電気機器']))

    def test_save_analysis_results(self, analyzer, sample_df, temp_dir):
        """分析結果保存のテスト"""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            analyzer.save_analysis_results(sample_df, "test_ytd_low.csv")

            # ファイルが作成されたことを確認
            assert os.path.exists("work/test_ytd_low.csv")

            # ファイル内容を確認
            df = pd.read_csv("work/test_ytd_low.csv")
            assert len(df) == len(sample_df)

        finally:
            os.chdir(original_cwd)

    def test_save_analysis_results_empty_df(self, analyzer, temp_dir, capsys):
        """空DataFrameの保存テスト"""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            empty_df = pd.DataFrame()
            analyzer.save_analysis_results(empty_df, "empty_ytd_low.csv")

            # エラーメッセージが出力されることを確認
            captured = capsys.readouterr()
            assert "保存するデータがありません" in captured.out

        finally:
            os.chdir(original_cwd)

    def test_print_recovery_candidates(self, analyzer, sample_df, capsys):
        """回復候補銘柄表示のテスト"""
        df_with_analysis = analyzer.add_recovery_analysis(sample_df)

        analyzer.print_recovery_candidates(df_with_analysis, top_n=2)

        captured = capsys.readouterr()
        assert "回復候補銘柄" in captured.out

    def test_analyze_ytd_lows_integration(self, analyzer):
        """年初来安値分析の統合テスト"""
        with patch('ytd_low_analyzer.pd.read_csv') as mock_read_csv:
            # モックデータを設定
            mock_df = pd.DataFrame([
                {
                    'code': '7203',
                    'name': 'トヨタ自動車',
                    'price': 2200.0,
                    'ytd_high': 2600.0,
                    'ytd_low': 2000.0,
                    'volume': 1000000,
                    'market_cap': 35000000000000,
                    'sector': '自動車・輸送機器',
                    'pe_ratio': 12.5,
                    'pb_ratio': 1.2
                }
            ])
            mock_read_csv.return_value = mock_df

            result_basic, result_detailed = analyzer.analyze_ytd_lows("dummy.csv")

            assert result_basic is not None
            assert 'ytd_low_distance' in result_basic.columns

            if result_detailed is not None:
                assert 'overall_score' in result_detailed.columns

    def test_edge_cases_same_high_low(self, analyzer):
        """年初来高値と安値が同じ場合のエッジケースのテスト"""
        df_same = pd.DataFrame([
            {
                'code': '0000',
                'name': 'テスト',
                'price': 1000.0,
                'ytd_high': 1000.0,
                'ytd_low': 1000.0,  # 高値と安値が同じ
                'volume': 1000,
                'market_cap': 1000000000,
                'sector': 'テスト',
                'pe_ratio': 10.0,
                'pb_ratio': 1.0
            }
        ])

        result_df = analyzer.calculate_recovery_potential(df_same)

        # 適切な処理がされているかを確認
        assert not pd.isna(result_df['recovery_potential'].iloc[0])

    def test_missing_financial_data(self, analyzer):
        """財務データが欠損している場合のテスト"""
        df_missing = pd.DataFrame([
            {
                'code': '0000',
                'name': 'テスト',
                'price': 1000.0,
                'ytd_high': 1200.0,
                'ytd_low': 800.0,
                'volume': 1000,
                'market_cap': 1000000000,
                'sector': 'テスト',
                'pe_ratio': np.nan,  # 欠損データ
                'pb_ratio': np.nan   # 欠損データ
            }
        ])

        result_df = analyzer.calculate_value_metrics(df_missing)

        # 欠損データに対する適切な処理がされているかを確認
        assert 'value_score' in result_df.columns
        # NaNまたは適切なデフォルト値が設定されているかを確認
        assert not pd.isna(result_df['value_score'].iloc[0]) or result_df['value_score'].iloc[0] == 0

    def test_extreme_values(self, analyzer):
        """極端な値に対するテスト"""
        df_extreme = pd.DataFrame([
            {
                'code': '0000',
                'name': 'テスト',
                'price': 1000000.0,  # 極端に高い価格
                'ytd_high': 1200000.0,
                'ytd_low': 1.0,       # 極端に低い安値
                'volume': 1,
                'market_cap': 1e15,   # 極端に大きい時価総額
                'sector': 'テスト',
                'pe_ratio': 1000.0,   # 極端に高いPER
                'pb_ratio': 100.0     # 極端に高いPBR
            }
        ])

        # 例外が発生しないことを確認
        result_df = analyzer.add_recovery_analysis(df_extreme)
        assert len(result_df) == 1
        assert 'overall_score' in result_df.columns

    def test_large_dataset_performance(self, analyzer):
        """大きなデータセットでのパフォーマンステスト"""
        # 1000行のデータセットを作成
        large_df = pd.DataFrame({
            'code': [f'{i:04d}' for i in range(1000)],
            'name': [f'テスト会社{i}' for i in range(1000)],
            'price': np.random.uniform(100, 10000, 1000),
            'ytd_high': np.random.uniform(150, 12000, 1000),
            'ytd_low': np.random.uniform(50, 8000, 1000),
            'volume': np.random.randint(1000, 10000000, 1000),
            'market_cap': np.random.uniform(1e9, 1e13, 1000),
            'sector': np.random.choice(['テクノロジー', '金融', '小売'], 1000),
            'pe_ratio': np.random.uniform(5, 50, 1000),
            'pb_ratio': np.random.uniform(0.5, 5, 1000)
        })

        # 回復分析の計算が正常に完了することを確認
        result_df = analyzer.add_recovery_analysis(large_df)
        assert len(result_df) == 1000
        assert 'overall_score' in result_df.columns