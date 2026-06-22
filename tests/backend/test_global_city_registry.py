"""
全球城市注册表与 World Bank 采集器集成测试
"""

from __future__ import annotations

from backend.data_collection.world_bank_collector import WorldBankCollector
from backend.models.city import GlobalCity
from backend.regions.city_registry import GlobalCityRegistry, get_global_city_registry, load_default_global_cities


class TestGlobalCityRegistry:
    def test_register_and_get(self):
        registry = GlobalCityRegistry()
        city = GlobalCity(
            code="test_city",
            name="测试城",
            name_en="Test City",
            country_code="TC",
            country_name="测试国",
            country_name_en="Test Country",
            region="测试洲",
        )
        assert registry.register(city) is True
        assert registry.get("test_city") == city
        assert registry.register(city) is False

    def test_get_by_name(self):
        registry = load_default_global_cities()
        assert registry.get_by_name("纽约") is not None
        assert registry.get_by_name("New York") is not None
        assert registry.get_by_name("NYC") is not None

    def test_list_by_country(self):
        registry = load_default_global_cities()
        cn_cities = registry.list_by_country("CN")
        codes = {c.code for c in cn_cities}
        assert "shanghai" in codes
        assert "beijing" in codes
        assert "shenzhen" in codes

    def test_list_by_region(self):
        registry = load_default_global_cities()
        asia = registry.list_by_region("亚洲")
        assert any(c.code == "tokyo" for c in asia)

    def test_list_by_tag(self):
        registry = load_default_global_cities()
        finance = registry.list_by_tag("global_finance_center")
        codes = {c.code for c in finance}
        assert "new_york" in codes
        assert "london" in codes
        assert "hong_kong" in codes

    def test_search(self):
        registry = load_default_global_cities()
        results = registry.search("中国")
        codes = {c.code for c in results}
        assert "shanghai" in codes
        assert "beijing" in codes

    def test_summary(self):
        registry = load_default_global_cities()
        summary = registry.summary()
        assert summary["total"] > 0
        assert "亚洲" in summary["by_region"]
        assert "CN" in summary["country_codes"]


class TestGlobalCitySingleton:
    def test_singleton(self):
        r1 = get_global_city_registry()
        r2 = get_global_city_registry()
        assert r1 is r2


class TestWorldBankCollectorWithRegistry:
    def test_supported_cities_come_from_registry(self):
        registry = load_default_global_cities()
        collector = WorldBankCollector(use_api=False, registry=registry)
        supported = collector.supported_cities()
        assert "shanghai" in supported
        assert "tokyo" in supported

    def test_fetch_data_for_unknown_city(self):
        registry = GlobalCityRegistry()
        collector = WorldBankCollector(use_api=False, registry=registry)
        assert collector.fetch_data(city="unknown") == []

    def test_fetch_data_fallback(self):
        collector = WorldBankCollector(use_api=False)
        data = collector.fetch_data(city="new_york")
        indicators = {record["indicator"] for record in data}
        assert "gdp_current_usd" in indicators
        assert "population" in indicators

    def test_fetch_all(self):
        collector = WorldBankCollector(use_api=False)
        all_data = collector.fetch_all()
        # fallback 仅覆盖部分城市
        assert "new_york" in all_data
        assert isinstance(all_data["new_york"], list)
