"""Tests for backend.data_collection modules."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest

from backend.data_collection.base_collector import BaseCollector, DataCollector
from backend.data_collection.data_source_manager import (
    CSVFileDataSource,
    DataSourceConfig,
    DataSourceType,
    JSONFileDataSource,
    MockDataSource,
    data_source_manager,
    fetch_from_source,
    list_all_sources,
    register_data_source,
)
from backend.data_collection.finance_collector import FinanceCollector
from backend.data_collection.industry_collector import IndustryCollector
from backend.data_collection.nbs_collector import NBSCollector


class ConcreteBaseCollector(BaseCollector):
    def fetch_data(self, **kwargs) -> list[dict[str, Any]]:
        return [{"value": kwargs.get("value", 1)}]

    def fetch_all(self, indicators: list[str] | None = None) -> dict[str, list[dict]]:
        return {"default": [{"value": 1}]}


class ConcreteDataCollector(DataCollector):
    def name(self) -> str:
        return "test"

    def supported_cities(self) -> list[str]:
        return ["sz"]

    def fetch_data(self, **kwargs) -> list[dict[str, Any]]:
        return []

    def fetch_all(self, indicators: list[str] | None = None) -> dict[str, list[dict]]:
        return {
            "gdp": [
                {"city": "sz", "value": 100},
                {"city": "gz", "value": 90},
            ]
        }


class TestBaseCollector:
    def test_base_collector_fetch_data(self):
        collector = ConcreteBaseCollector()
        assert collector.fetch_data(value=42) == [{"value": 42}]

    def test_data_collector_name_and_cities(self):
        collector = ConcreteDataCollector()
        assert collector.name() == "test"
        assert collector.supported_cities() == ["sz"]
        assert collector.source_name() == "ConcreteDataCollector"

    def test_data_collector_collect(self):
        collector = ConcreteDataCollector()
        result = collector.collect()
        assert "sz" in result
        assert "gz" in result
        assert isinstance(result["sz"], pd.DataFrame)
        assert "indicator" in result["sz"].columns

    def test_data_collector_collect_no_city_column(self):
        class NoCityCollector(DataCollector):
            def name(self) -> str:
                return "no-city"

            def supported_cities(self) -> list[str]:
                return []

            def fetch_data(self, **kwargs) -> list[dict[str, Any]]:
                return []

            def fetch_all(self, indicators: list[str] | None = None) -> dict[str, list[dict]]:
                return {"metric": [{"value": 1}]}

        result = NoCityCollector().collect()
        assert "unknown" in result


class TestFinanceCollector:
    def test_name_and_cities(self):
        collector = FinanceCollector()
        assert collector.name() == "pbc"
        assert collector.supported_cities() == ["CN"]

    def test_fetch_data_unknown_indicator(self):
        collector = FinanceCollector()
        assert collector.fetch_data(indicator="unknown") == []

    def test_get_money_supply_success(self, monkeypatch):
        collector = FinanceCollector()
        df = pd.DataFrame(
            {
                "日期": ["2024-01-01", "2024-02-01"],
                "今值": [8.5, 8.7],
            }
        )
        fake_ak = SimpleNamespace(macro_china_m2_yearly=lambda: df)
        monkeypatch.setattr("backend.data_collection.finance_collector.ak", fake_ak)
        results = collector.get_money_supply()
        assert len(results) == 2
        assert results[0]["code"] == "m2_yoy"
        assert results[0]["year"] == 2024

    def test_get_money_supply_bad_row_skipped(self, monkeypatch):
        collector = FinanceCollector()
        df = pd.DataFrame(
            {
                "日期": ["2024-01-01", "bad-date"],
                "今值": [8.5, "not-a-number"],
            }
        )
        fake_ak = SimpleNamespace(macro_china_m2_yearly=lambda: df)
        monkeypatch.setattr("backend.data_collection.finance_collector.ak", fake_ak)
        results = collector.get_money_supply()
        assert len(results) == 1

    def test_get_money_supply_failure(self, monkeypatch):
        collector = FinanceCollector()

        def raise_error():
            raise RuntimeError("network error")

        fake_ak = SimpleNamespace(macro_china_m2_yearly=raise_error)
        monkeypatch.setattr("backend.data_collection.finance_collector.ak", fake_ak)
        results = collector.get_money_supply()
        assert results == []

    def test_fetch_all(self, monkeypatch):
        collector = FinanceCollector()

        def fake():
            return [{"value": 1}]

        monkeypatch.setattr(collector, "get_money_supply", fake)
        result = collector.fetch_all()
        assert "money_supply" in result


class TestDataSourceManager:
    @pytest.fixture(autouse=True)
    def reset_manager(self):
        """Reset the singleton manager state between tests."""
        data_source_manager._sources.clear()
        data_source_manager._configs.clear()
        data_source_manager._data_cache.clear()
        data_source_manager._last_update.clear()
        yield
        data_source_manager._sources.clear()
        data_source_manager._configs.clear()
        data_source_manager._data_cache.clear()
        data_source_manager._last_update.clear()

    def test_register_and_get_source(self, tmp_path):
        path = tmp_path / "data.json"
        path.write_text('{"key": [{"x": 1}]}', encoding="utf-8")
        ok = data_source_manager.register_source(
            name="json",
            source_type=DataSourceType.JSON_FILE,
            connection_info={"path": str(path)},
        )
        assert ok is True
        source = data_source_manager.get_source("json")
        assert source is not None
        assert "json" in data_source_manager.list_sources()

    def test_register_csv_source(self, tmp_path):
        path = tmp_path / "data.csv"
        path.write_text("x,y\n1,2\n3,4\n", encoding="utf-8")
        ok = data_source_manager.register_source(
            name="csv",
            source_type=DataSourceType.CSV_FILE,
            connection_info={"path": str(path)},
        )
        assert ok is True

    def test_register_unsupported_type(self):
        ok = data_source_manager.register_source(
            name="db",
            source_type=DataSourceType.DATABASE,
            connection_info={},
        )
        assert ok is False

    def test_register_source_connection_fails(self, tmp_path):
        ok = data_source_manager.register_source(
            name="missing",
            source_type=DataSourceType.JSON_FILE,
            connection_info={"path": str(tmp_path / "missing.json")},
        )
        assert ok is False

    def test_unregister_source(self, tmp_path):
        path = tmp_path / "data.json"
        path.write_text("{}", encoding="utf-8")
        data_source_manager.register_source(
            name="json",
            source_type=DataSourceType.JSON_FILE,
            connection_info={"path": str(path)},
        )
        assert data_source_manager.unregister_source("json") is True
        assert data_source_manager.unregister_source("json") is False

    def test_fetch_data_by_source(self, tmp_path):
        path = tmp_path / "data.json"
        path.write_text('{"gdp": [{"city": "深圳", "value": 100}]}', encoding="utf-8")
        data_source_manager.register_source(
            name="json",
            source_type=DataSourceType.JSON_FILE,
            connection_info={"path": str(path)},
        )
        data = data_source_manager.fetch_data("gdp", source_name="json")
        assert isinstance(data, list)
        assert data[0]["city"] == "深圳"

    def test_fetch_data_with_cache(self, tmp_path):
        path = tmp_path / "data.json"
        path.write_text('{"gdp": [{"value": 1}]}', encoding="utf-8")
        data_source_manager.register_source(
            name="json",
            source_type=DataSourceType.JSON_FILE,
            connection_info={"path": str(path)},
        )
        first = data_source_manager.fetch_data("gdp", source_name="json")
        second = data_source_manager.fetch_data("gdp", source_name="json")
        assert first is second

    def test_fetch_data_auto_select_source(self, tmp_path):
        path = tmp_path / "data.json"
        path.write_text('{"gdp": [{"value": 1}]}', encoding="utf-8")
        data_source_manager.register_source(
            name="json",
            source_type=DataSourceType.JSON_FILE,
            connection_info={"path": str(path)},
            tables=["gdp"],
            priority=10,
        )
        data = data_source_manager.fetch_data("gdp")
        assert data is not None

    def test_fetch_data_no_source(self):
        assert data_source_manager.fetch_data("gdp") is None
        assert data_source_manager.fetch_data("gdp", source_name="missing") is None

    def test_clear_cache(self, tmp_path):
        path = tmp_path / "data.json"
        path.write_text('{"gdp": [{"value": 1}]}', encoding="utf-8")
        data_source_manager.register_source(
            name="json",
            source_type=DataSourceType.JSON_FILE,
            connection_info={"path": str(path)},
        )
        data_source_manager.fetch_data("gdp", source_name="json")
        data_source_manager.clear_cache(pattern="gdp")
        assert len(data_source_manager._data_cache) == 0

    def test_get_status(self, tmp_path):
        path = tmp_path / "data.json"
        path.write_text("{}", encoding="utf-8")
        data_source_manager.register_source(
            name="json",
            source_type=DataSourceType.JSON_FILE,
            connection_info={"path": str(path)},
        )
        status = data_source_manager.get_status()
        assert status["total_sources"] == 1

    def test_load_and_save_sources_config(self, tmp_path):
        config_path = tmp_path / "sources.json"
        config = {
            "sources": [
                {
                    "name": "mock",
                    "type": "mock",
                    "connection": {"data": {"gdp": [{"value": 1}]}},
                    "tables": ["gdp"],
                    "priority": 1,
                    "enabled": True,
                }
            ]
        }
        config_path.write_text(__import__("json").dumps(config), encoding="utf-8")
        data_source_manager.load_sources_from_config(str(config_path))
        assert "mock" in data_source_manager.list_sources()

        save_path = tmp_path / "saved.json"
        data_source_manager.save_sources_config(str(save_path))
        saved = __import__("json").loads(save_path.read_text(encoding="utf-8"))
        assert len(saved["sources"]) == 1

    def test_convenience_functions(self, tmp_path):
        path = tmp_path / "data.json"
        path.write_text('{"gdp": [{"value": 1}]}', encoding="utf-8")
        assert register_data_source("json", "json_file", path=str(path)) is True
        data = fetch_from_source("gdp", source_name="json")
        assert data is not None
        assert "json" in list_all_sources()


class TestDataSources:
    def test_json_file_source(self, tmp_path):
        path = tmp_path / "data.json"
        path.write_text('{"gdp": [{"value": 1}]}', encoding="utf-8")
        config = DataSourceConfig(
            name="json", source_type=DataSourceType.JSON_FILE, connection_info={"path": str(path)}
        )
        source = JSONFileDataSource(config)
        assert source.connect() is True
        assert source.test_connection() is True
        assert source.fetch_data("gdp") == [{"value": 1}]
        source.disconnect()

    def test_json_file_source_missing(self, tmp_path):
        config = DataSourceConfig(
            name="json",
            source_type=DataSourceType.JSON_FILE,
            connection_info={"path": str(tmp_path / "missing.json")},
        )
        source = JSONFileDataSource(config)
        assert source.connect() is False
        assert source.fetch_data("gdp") == []

    def test_csv_file_source(self, tmp_path):
        path = tmp_path / "data.csv"
        path.write_text("x,y\n1,2\n3,4\n", encoding="utf-8")
        config = DataSourceConfig(name="csv", source_type=DataSourceType.CSV_FILE, connection_info={"path": str(path)})
        source = CSVFileDataSource(config)
        assert source.connect() is True
        df = source.fetch_data("x", value=1)
        assert len(df) == 1

    def test_csv_file_source_read_error(self, tmp_path):
        path = tmp_path / "data.csv"
        path.write_text("x,y\n1,2\n", encoding="utf-8")
        config = DataSourceConfig(name="csv", source_type=DataSourceType.CSV_FILE, connection_info={"path": str(path)})
        source = CSVFileDataSource(config)
        result = source.fetch_data("x", value="no-match")
        assert isinstance(result, pd.DataFrame)

    def test_mock_source(self):
        config = DataSourceConfig(
            name="mock",
            source_type=DataSourceType.MOCK,
            connection_info={"data": {"gdp": [{"value": 1}]}},
        )
        source = MockDataSource(config)
        assert source.connect() is True
        assert source.test_connection() is True
        assert source.fetch_data("gdp") == [{"value": 1}]


class TestIndustryCollector:
    def test_name_and_cities(self):
        collector = IndustryCollector()
        assert collector.name() == "industry"
        assert collector.supported_cities() == ["CN"]
        assert collector.source_name() == "industry"

    def test_fetch_data_with_ak(self, monkeypatch):
        collector = IndustryCollector()
        df = pd.DataFrame(
            {
                "指标": ["高技术制造业", "装备制造业"],
                "累计值": ["1000.5", "2000.7"],
            }
        )
        fake_ak = SimpleNamespace(macro_china_industry_profit=lambda: df)
        monkeypatch.setattr("backend.data_collection.industry_collector.ak", fake_ak)
        results = collector.fetch_data(industry="半导体", year=2024)
        assert len(results) == 2
        assert results[0]["industry"] == "半导体"
        assert results[0]["year"] == 2024
        assert results[0]["source"] == "akshare"

    def test_fetch_data_ak_failure_uses_fallback(self, monkeypatch):
        collector = IndustryCollector()

        def raise_error():
            raise RuntimeError("network error")

        fake_ak = SimpleNamespace(macro_china_industry_profit=raise_error)
        monkeypatch.setattr("backend.data_collection.industry_collector.ak", fake_ak)
        results = collector.fetch_data()
        assert len(results) == 3
        assert results[0]["source"] == "statistical_yearbook"

    def test_fetch_data_no_ak(self, monkeypatch):
        collector = IndustryCollector()
        monkeypatch.setattr("backend.data_collection.industry_collector.ak", None)
        results = collector.fetch_data()
        assert len(results) == 3

    def test_fetch_all(self):
        collector = IndustryCollector()
        result = collector.fetch_all()
        assert "industry_output" in result
        assert len(result["industry_output"]) == 3

        result_named = collector.fetch_all(indicators=["custom"])
        assert "custom" in result_named


class TestNBSCollector:
    @pytest.fixture
    def gdp_df(self):
        return pd.DataFrame(
            {
                "季度": ["2024年第1-4季度", "2023年第1-4季度"],
                "国内生产总值-绝对值": [126000.0, 120000.0],
                "第一产业-绝对值": [8000.0, 7500.0],
                "第二产业-绝对值": [48000.0, 46000.0],
                "第三产业-绝对值": [70000.0, 66500.0],
            }
        )

    @pytest.fixture
    def fake_ak(self, gdp_df):
        return SimpleNamespace(
            macro_china_gdp=lambda: gdp_df,
            macro_china_cpi_yearly=lambda: pd.DataFrame({"日期": ["2024-01-01", "2024-02-01"], "今值": [0.5, 0.6]}),
            macro_china_pmi_yearly=lambda: pd.DataFrame({"日期": ["2024-01-01"], "制造业-指数": [50.1]}),
        )

    def test_name_and_cities(self):
        collector = NBSCollector()
        assert collector.name() == "nbs"
        assert collector.supported_cities() == ["CN"]
        assert collector.source_name() == "nbs"

    def test_fetch_data_unknown(self):
        collector = NBSCollector()
        assert collector.fetch_data(indicator="unknown") == []

    def test_get_gdp(self, monkeypatch, fake_ak):
        collector = NBSCollector()
        monkeypatch.setattr("backend.data_collection.nbs_collector.ak", fake_ak)
        results = collector.get_gdp()
        assert len(results) == 8  # 2 rows * 4 indicators
        assert results[0]["code"] == "gdp"

    def test_get_gdp_failure(self, monkeypatch):
        collector = NBSCollector()

        def raise_error():
            raise RuntimeError("network")

        fake_ak = SimpleNamespace(macro_china_gdp=raise_error)
        monkeypatch.setattr("backend.data_collection.nbs_collector.ak", fake_ak)
        assert collector.get_gdp() == []

    def test_get_cpi(self, monkeypatch, fake_ak):
        collector = NBSCollector()
        monkeypatch.setattr("backend.data_collection.nbs_collector.ak", fake_ak)
        results = collector.get_cpi()
        assert len(results) == 2
        assert results[0]["code"] == "cpi_yoy"

    def test_get_pmi(self, monkeypatch, fake_ak):
        collector = NBSCollector()
        monkeypatch.setattr("backend.data_collection.nbs_collector.ak", fake_ak)
        results = collector.get_pmi()
        assert len(results) == 1
        assert results[0]["code"] == "pmi_manufacturing"

    def test_get_fiscal_revenue_with_ak(self, monkeypatch, fake_ak):
        collector = NBSCollector()
        monkeypatch.setattr("backend.data_collection.nbs_collector.ak", fake_ak)
        results = collector.get_fiscal_revenue()
        assert len(results) == 2
        assert results[0]["code"] == "fiscal_revenue"

    def test_get_fiscal_revenue_no_ak(self, monkeypatch):
        collector = NBSCollector()
        monkeypatch.setattr("backend.data_collection.nbs_collector.ak", None)
        results = collector.get_fiscal_revenue()
        assert len(results) == 5
        assert results[0]["code"] == "fiscal_revenue"

    def test_get_industrial_output_with_ak(self, monkeypatch, fake_ak):
        collector = NBSCollector()
        monkeypatch.setattr("backend.data_collection.nbs_collector.ak", fake_ak)
        results = collector.get_industrial_output()
        assert len(results) == 2
        assert results[0]["code"] == "industrial_output"

    def test_get_industrial_output_no_ak(self, monkeypatch):
        collector = NBSCollector()
        monkeypatch.setattr("backend.data_collection.nbs_collector.ak", None)
        results = collector.get_industrial_output()
        assert len(results) == 5
        assert results[0]["code"] == "industrial_output"

    def test_fetch_all(self, monkeypatch, fake_ak):
        collector = NBSCollector()
        monkeypatch.setattr("backend.data_collection.nbs_collector.ak", fake_ak)
        results = collector.fetch_all(indicators=["gdp", "cpi"])
        assert "gdp" in results
        assert "cpi" in results
