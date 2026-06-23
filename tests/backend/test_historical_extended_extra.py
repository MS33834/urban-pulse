"""补充 backend.data.historical_extended 的边界与未覆盖路径测试。"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.data import historical_extended as he


class TestExtendedHelpers:
    def test_list_extended_cities(self):
        cities = he.list_extended_cities()
        assert isinstance(cities, list)
        assert "深圳" in cities
        assert cities == sorted(cities)

    def test_list_extended_indicators(self):
        indicators = he.list_extended_indicators()
        assert isinstance(indicators, list)
        assert "gdp" in indicators
        assert indicators == sorted(indicators)

    def test_get_extended_indicator_meta_existing(self):
        meta = he.get_extended_indicator_meta("gdp")
        assert meta is not None
        assert meta["unit"] == "亿元"

    def test_get_extended_indicator_meta_missing(self):
        assert he.get_extended_indicator_meta("not_exists") is None


class TestGetCityTimeseries:
    def test_existing_city_shape(self):
        df = he.get_city_timeseries("深圳")
        assert df.shape[0] == 16
        assert "year" in df.columns
        assert "gdp" in df.columns

    def test_unknown_city_returns_empty_dataframe(self):
        df = he.get_city_timeseries("不存在的城市")
        assert df.empty
        assert list(df.columns) == ["year"] + list(he.INDICATOR_META.keys())


class TestGetCityIndicator:
    def test_existing_specific_year(self):
        info = he.get_city_indicator("深圳", "gdp", 2024)
        assert info is not None
        assert info["value"] == 36500
        assert info["provenance"]["estimated"] is False

    def test_default_latest_year(self):
        info = he.get_city_indicator("深圳", "gdp")
        assert info is not None
        assert info["year"] == 2025
        assert info["value"] == 38500

    def test_unknown_city_returns_none(self):
        assert he.get_city_indicator("不存在", "gdp", 2024) is None

    def test_unknown_indicator_returns_none(self):
        assert he.get_city_indicator("深圳", "not_exists", 2024) is None

    def test_unknown_year_returns_none(self):
        assert he.get_city_indicator("深圳", "gdp", 1999) is None

    def test_methodology_change_for_population_after_2020(self):
        info = he.get_city_indicator("深圳", "population", 2020)
        assert info["provenance"]["methodology_change"] is not None
        assert "口径" in info["provenance"]["methodology_change"]

    def test_no_methodology_change_for_non_population(self):
        info = he.get_city_indicator("深圳", "gdp", 2020)
        assert info["provenance"]["methodology_change"] is None


class TestGetDataCoverage:
    def test_all_cities_coverage(self):
        cov = he.get_data_coverage()
        assert len(cov) == 10
        for city, info in cov.items():
            assert info["year_count"] == 16
            assert info["completeness"] == pytest.approx(1.0)

    def test_single_city_coverage(self):
        cov = he.get_data_coverage("深圳")
        assert set(cov.keys()) == {"深圳"}
        assert cov["深圳"]["year_count"] == 16

    def test_unknown_city_coverage(self):
        cov = he.get_data_coverage("不存在")
        assert cov == {"不存在": {"years": [], "year_count": 0, "indicators_per_year": {}, "completeness": 0.0}}


class TestMainBlock:
    def test_main_block_runs(self, capsys, monkeypatch):
        """验证 __main__ 块可以执行并输出自检信息。"""
        # 限制只打印两个城市，避免日志过长
        original_cities = he.list_extended_cities()
        monkeypatch.setattr(he, "list_extended_cities", lambda: original_cities[:2])

        module_path = Path(he.__file__)
        with patch.object(sys, "argv", [str(module_path)]):
            runpy.run_path(str(module_path), run_name="__main__")

        captured = capsys.readouterr()
        assert "Cities:" in captured.out
        assert "Coverage summary:" in captured.out
