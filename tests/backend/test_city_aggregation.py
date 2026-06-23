"""Tests for backend.core.city_aggregation."""

from __future__ import annotations

import math

import pytest

from backend.core.city_aggregation import (
    AggregationConfig,
    CityDataAggregator,
    ComparisonResult,
)


@pytest.fixture
def aggregator():
    return CityDataAggregator()


@pytest.fixture
def sample_data():
    return [
        {"city": "深圳", "province": "广东", "year": 2023, "indicator": "gdp", "value": 100.0},
        {"city": "深圳", "province": "广东", "year": 2024, "indicator": "gdp", "value": 110.0},
        {"city": "广州", "province": "广东", "year": 2023, "indicator": "gdp", "value": 90.0},
        {"city": "广州", "province": "广东", "year": 2024, "indicator": "gdp", "value": 95.0},
        {"city": "上海", "province": "上海", "year": 2024, "indicator": "gdp", "value": 120.0},
    ]


class TestCityDataAggregator:
    def test_aggregate_count_sum_avg(self, aggregator, sample_data):
        config = AggregationConfig(
            group_by=["province"],
            metrics=["count", "sum", "avg", "min", "max", "median", "std"],
        )
        result = aggregator.aggregate(sample_data, config)
        assert len(result.groups) == 2
        by_province = {g["province"]: g for g in result.groups}
        assert by_province["广东"]["count"] == 4
        assert by_province["广东"]["sum"] == pytest.approx(395.0)
        assert by_province["上海"]["count"] == 1
        assert "std" in result.groups[0]

    def test_aggregate_with_filters_sort_limit(self, aggregator, sample_data):
        config = AggregationConfig(
            group_by=["city"],
            metrics=["sum"],
            filters={"province": "广东"},
            sort_by="sum",
            sort_order="desc",
            limit=1,
        )
        result = aggregator.aggregate(sample_data, config)
        assert len(result.groups) == 1
        assert result.groups[0]["city"] == "深圳"

    def test_aggregate_range_filter(self, aggregator, sample_data):
        config = AggregationConfig(
            group_by=["city"],
            metrics=["count"],
            filters={"value": {"min": 100}},
        )
        result = aggregator.aggregate(sample_data, config)
        cities = {g["city"] for g in result.groups}
        assert cities == {"深圳", "上海"}

    def test_compare_cities(self, aggregator, sample_data):
        result = aggregator.compare_cities(sample_data)
        assert isinstance(result, ComparisonResult)
        assert len(result.cities) == 3
        assert "gdp" in result.cities[0]["indicators"]
        assert len(result.rankings["gdp"]) == 3
        assert len(result.insights) == 1

    def test_time_series_analysis_simple(self, aggregator, sample_data):
        result = aggregator.time_series_analysis(sample_data)
        assert "time_points" in result
        assert len(result["time_points"]) == 2
        assert result["trend"] in {"increasing", "decreasing", "stable"}

    def test_time_series_analysis_grouped(self, aggregator, sample_data):
        result = aggregator.time_series_analysis(sample_data, group_by=["city"])
        assert len(result) == 3
        key = next(iter(result))
        assert "time_points" in result[key]
        assert "trend" in result[key]

    def test_regional_analysis(self, aggregator, sample_data):
        result = aggregator.regional_analysis(sample_data)
        assert result["total_regions"] == 2
        assert result["regions"][0]["region"] in {"广东", "上海"}

    def test_correlation_analysis(self, aggregator):
        data = [
            {"city": "深圳", "year": 2023, "indicator": "gdp", "value": 100.0},
            {"city": "深圳", "year": 2023, "indicator": "population", "value": 10.0},
            {"city": "广州", "year": 2023, "indicator": "gdp", "value": 90.0},
            {"city": "广州", "year": 2023, "indicator": "population", "value": 12.0},
        ]
        result = aggregator.correlation_analysis(data, ["gdp", "population"])
        matrix = result["correlation_matrix"]
        assert matrix["gdp"]["gdp"] == 1.0
        assert matrix["population"]["population"] == 1.0
        assert not math.isnan(matrix["gdp"]["population"])

    def test_correlation_insufficient_data(self, aggregator):
        data = [
            {"city": "深圳", "year": 2023, "indicator": "gdp", "value": 100.0},
            {"city": "深圳", "year": 2023, "indicator": "population", "value": 10.0},
        ]
        result = aggregator.correlation_analysis(data, ["gdp", "population"])
        assert math.isnan(result["correlation_matrix"]["gdp"]["population"])

    def test_pearson_constant(self, aggregator):
        assert aggregator._pearson_correlation([1, 1, 1], [1, 2, 3]) == 0.0
        assert math.isnan(aggregator._pearson_correlation([1], [2]))

    def test_calculate_trend(self, aggregator):
        assert aggregator._calculate_trend([1, 2, 3]) == "increasing"
        assert aggregator._calculate_trend([3, 2, 1]) == "decreasing"
        assert aggregator._calculate_trend([1, 1, 1]) in {"stable", "insufficient_data"}
        assert aggregator._calculate_trend([1]) == "insufficient_data"

    def test_apply_filters(self, aggregator, sample_data):
        filtered = aggregator._apply_filters(sample_data, {"city": "深圳"})
        assert len(filtered) == 2

    def test_global_instance(self):
        from backend.core.city_aggregation import city_aggregator

        assert isinstance(city_aggregator, CityDataAggregator)
