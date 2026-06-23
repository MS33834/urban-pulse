"""Tests for backend.data_processing modules."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.data_processing.cleaner import DataCleaner
from backend.data_processing.transformer import DataTransformer
from backend.data_processing.validator import DataValidator


class TestDataCleaner:
    @pytest.fixture
    def cleaner(self):
        return DataCleaner()

    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame(
            {
                "city": ["深圳", "广州", "上海", "北京", "深圳"],
                "gdp": [100.0, np.nan, 300.0, 400.0, 500.0],
                "population": [10, 12, 15, 18, 20],
            }
        )

    def test_detect_missing(self, cleaner, sample_df):
        report = cleaner.detect_missing(sample_df)
        assert report["total_cells"] == 15
        assert report["total_missing"] == 1
        assert "gdp" in report["columns"]

    def test_fill_missing_linear(self, cleaner, sample_df):
        filled = cleaner.fill_missing(sample_df, method="linear")
        assert filled["gdp"].isna().sum() == 0

    def test_fill_missing_mean(self, cleaner, sample_df):
        filled = cleaner.fill_missing(sample_df, method="mean")
        assert filled["gdp"].isna().sum() == 0

    def test_fill_missing_zero(self, cleaner, sample_df):
        filled = cleaner.fill_missing(sample_df, method="zero")
        assert filled["gdp"].isna().sum() == 0
        assert filled.loc[1, "gdp"] == 0.0

    def test_detect_outliers_zscore(self, cleaner):
        df = pd.DataFrame({"x": [1, 2, 3, 4, 100]})
        report = cleaner.detect_outliers_zscore(df, threshold=1.5)
        assert report["columns"]["x"]["outlier_count"] == 1

    def test_detect_outliers_iqr(self, cleaner):
        df = pd.DataFrame({"x": [1, 2, 3, 4, 100]})
        report = cleaner.detect_outliers_iqr(df, multiplier=1.5)
        assert report["columns"]["x"]["outlier_count"] == 1

    def test_remove_outliers_iqr(self, cleaner):
        df = pd.DataFrame({"x": [1, 2, 3, 4, 100]})
        cleaned = cleaner.remove_outliers(df, method="iqr", threshold=1.5)
        assert len(cleaned) == 4

    def test_remove_outliers_zscore(self, cleaner):
        df = pd.DataFrame({"x": [1, 2, 3, 4, 100]})
        cleaned = cleaner.remove_outliers(df, method="zscore", threshold=1.5)
        assert len(cleaned) == 4

    def test_cap_outliers(self, cleaner):
        df = pd.DataFrame({"x": [1, 2, 3, 4, 100]})
        capped = cleaner.cap_outliers(df, method="iqr", threshold=1.5)
        assert capped["x"].max() < 100

    def test_normalize_minmax(self, cleaner):
        df = pd.DataFrame({"x": [0, 50, 100]})
        norm, params = cleaner.normalize_minmax(df)
        assert norm["x"].min() == 0.0
        assert norm["x"].max() == 1.0
        assert params["x"] == (0.0, 100.0)

    def test_normalize_minmax_constant(self, cleaner):
        df = pd.DataFrame({"x": [5, 5, 5]})
        norm, params = cleaner.normalize_minmax(df)
        assert norm["x"].eq(0.0).all()

    def test_standardize_zscore(self, cleaner):
        df = pd.DataFrame({"x": [0, 50, 100]})
        std, params = cleaner.standardize_zscore(df)
        assert pytest.approx(std["x"].mean()) == 0.0
        assert pytest.approx(std["x"].std(), rel=1e-2) == 1.0

    def test_standardize_zscore_constant(self, cleaner):
        df = pd.DataFrame({"x": [5, 5, 5]})
        std, params = cleaner.standardize_zscore(df)
        assert std["x"].eq(0.0).all()

    def test_generate_quality_report(self, cleaner, sample_df):
        report = cleaner.generate_quality_report(sample_df)
        assert report["shape"] == sample_df.shape
        assert "missing" in report
        assert "outliers_zscore" in report
        assert "statistics" in report


class TestDataTransformer:
    @pytest.fixture
    def transformer(self):
        return DataTransformer()

    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame(
            {
                "city": ["深圳", "广州", "深圳"],
                "year": [2023, 2023, 2024],
                "gdp": [100, 90, 110],
            }
        )

    def test_pivot_data(self, transformer, sample_df):
        pivoted = transformer.pivot_data(sample_df, index="city", columns="year", values="gdp")
        assert pivoted.loc["深圳", 2024] == 110

    def test_melt_data(self, transformer, sample_df):
        melted = transformer.melt_data(sample_df, id_vars=["city"], value_vars=["gdp"])
        assert "variable" in melted.columns
        assert "value" in melted.columns

    def test_aggregate_data(self, transformer, sample_df):
        agg = transformer.aggregate_data(sample_df, group_by=["city"], aggregations={"gdp": "sum"})
        assert agg.loc[agg["city"] == "深圳", "gdp"].iloc[0] == 210

    def test_merge_data(self, transformer):
        left = pd.DataFrame({"city": ["深圳", "广州"], "gdp": [100, 90]})
        right = pd.DataFrame({"city": ["深圳", "广州"], "population": [10, 12]})
        merged = transformer.merge_data(left, right, on="city")
        assert "population" in merged.columns

    def test_filter_data(self, transformer, sample_df):
        filtered = transformer.filter_data(sample_df, {"city": "深圳"})
        assert len(filtered) == 2

        filtered_list = transformer.filter_data(sample_df, {"city": ["深圳", "广州"]})
        assert len(filtered_list) == 3

    def test_sort_data(self, transformer, sample_df):
        sorted_df = transformer.sort_data(sample_df, by=["gdp"], ascending=False)
        assert sorted_df.iloc[0]["gdp"] == 110


class TestDataValidator:
    @pytest.fixture
    def validator(self):
        return DataValidator()

    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame(
            {
                "city": ["深圳", "广州", "上海"],
                "gdp": [100, 90, 80],
                "population": [10, 12, 15],
            }
        )

    def test_validate_required_columns(self, validator, sample_df):
        result = validator.validate_required_columns(sample_df, ["city", "gdp"])
        assert result["valid"] is True
        result = validator.validate_required_columns(sample_df, ["city", "missing"])
        assert result["valid"] is False

    def test_validate_data_types(self, validator, sample_df):
        result = validator.validate_data_types(sample_df, {"gdp": float, "city": str})
        assert result["valid"] is True

    def test_validate_value_ranges(self, validator, sample_df):
        result = validator.validate_value_ranges(sample_df, {"gdp": (0, 100)})
        assert result["valid"] is True
        result_invalid = validator.validate_value_ranges(sample_df, {"gdp": (0, 95)})
        assert result_invalid["valid"] is False
        assert "gdp" in result_invalid["violations"]

    def test_validate_unique_values(self, validator):
        df = pd.DataFrame({"city": ["深圳", "深圳", "广州"]})
        result = validator.validate_unique_values(df, ["city"])
        assert result["valid"] is False

    def test_validate_not_null(self, validator):
        df = pd.DataFrame({"city": ["深圳", None, "广州"]})
        result = validator.validate_not_null(df, ["city"])
        assert result["valid"] is False

    def test_generate_full_validation_report(self, validator, sample_df):
        report = validator.generate_full_validation_report(
            sample_df,
            required_columns=["city"],
            expected_types={"gdp": float},
            value_ranges={"gdp": (0, 200)},
            unique_columns=["city"],
            not_null_columns=["city"],
        )
        assert "required_columns" in report
        assert report["overall_valid"] is True
