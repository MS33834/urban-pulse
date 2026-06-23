"""Extended tests for backend.regions registry, loader and models."""

from __future__ import annotations

import json

import pytest

from backend.regions import Region, RegionLevel, RegionRegistry, get_registry
from backend.regions.loader import RegionLoader, load_default_regions


class TestRegionModelExtended:
    def test_to_dict(self):
        r = Region(
            code="CN-GD-SZ",
            name="深圳",
            level=RegionLevel.CITY,
            parent_code="CN-GD",
            region="华南",
            indicators={"gdp": 100},
            historical_data=[{"year": 2020, "gdp": 100}],
            metadata={"foo": "bar"},
        )
        d = r.to_dict()
        assert d["code"] == "CN-GD-SZ"
        assert d["indicators"]["gdp"] == 100
        assert d["historical_data"][0]["year"] == 2020

    def test_get_indicator(self):
        r = Region(code="CN", name="中国", level=RegionLevel.COUNTRY, indicators={"gdp": 100})
        assert r.get_indicator("gdp") == 100
        assert r.get_indicator("missing", "default") == "default"

    def test_province_code_for_province(self):
        r = Region(code="CN-GD", name="广东", level=RegionLevel.PROVINCE)
        assert r.province_code == "CN-GD"

    def test_province_code_for_city(self):
        r = Region(code="CN-GD-SZ", name="深圳", level=RegionLevel.CITY, parent_code="CN-GD")
        assert r.province_code == "CN-GD"

    def test_province_code_for_district(self):
        r = Region(
            code="CN-GD-SZ-NS",
            name="南山",
            level=RegionLevel.DISTRICT,
            parent_code="CN-GD-SZ",
            metadata={"province_code": "CN-GD"},
        )
        assert r.province_code == "CN-GD"

    def test_province_code_none(self):
        r = Region(code="CN-GD-SZ", name="深圳", level=RegionLevel.CITY)
        assert r.province_code is None

    def test_latest_year_from_indicators(self):
        r = Region(code="CN", name="中国", level=RegionLevel.COUNTRY, indicators={"year": 2025})
        assert r.latest_year == 2025

    def test_get_time_series_missing_indicator(self):
        r = Region(
            code="CN-GD-SZ",
            name="深圳",
            level=RegionLevel.CITY,
            historical_data=[{"year": 2020, "gdp": 100}],
        )
        assert r.get_time_series("population") == []


class TestRegionRegistryExtended:
    def test_unregister(self):
        registry = RegionRegistry()
        registry.register(Region(code="x", name="X", level=RegionLevel.CITY))
        assert registry.unregister("x") is True
        assert registry.unregister("x") is False

    def test_get_by_name(self):
        registry = RegionRegistry()
        registry.register(Region(code="a", name="深圳", level=RegionLevel.CITY))
        assert registry.get_by_name("深圳") is not None
        assert registry.get_by_name("深圳", RegionLevel.PROVINCE) is None
        assert registry.get_by_name("不存在") is None

    def test_list_by_region(self):
        registry = RegionRegistry()
        registry.register(Region(code="a", name="A", level=RegionLevel.CITY, region="华南"))
        registry.register(Region(code="b", name="B", level=RegionLevel.CITY, region="华东"))
        assert len(registry.list_by_region("华南")) == 1
        assert registry.list_by_region("华北") == []

    def test_list_provinces_and_cities(self):
        registry = RegionRegistry()
        registry.register(Region(code="CN-GD", name="广东", level=RegionLevel.PROVINCE))
        registry.register(
            Region(code="CN-GD-SZ", name="深圳", level=RegionLevel.CITY, parent_code="CN-GD")
        )
        registry.register(
            Region(code="CN-SH-SH", name="上海", level=RegionLevel.CITY, parent_code="CN-SH")
        )
        assert len(registry.list_provinces()) == 1
        assert len(registry.list_cities()) == 2
        assert len(registry.list_cities("CN-GD")) == 1

    def test_region_summary(self):
        registry = RegionRegistry()
        registry.register(Region(code="CN", name="中国", level=RegionLevel.COUNTRY))
        summary = registry.region_summary()
        assert summary["total"] == 1
        assert summary["by_level"]["country"] == 1

    def test_add_loader_and_load_all(self):
        registry = RegionRegistry()

        def loader(reg):
            reg.register(Region(code="loaded", name="Loaded", level=RegionLevel.CITY))
            return 1

        registry.add_loader(loader)
        assert registry.load_all() == 1
        assert registry.get("loaded") is not None

    def test_load_all_logs_exception(self, caplog):
        registry = RegionRegistry()

        def bad_loader(_reg):
            raise RuntimeError("boom")

        registry.add_loader(bad_loader)
        count = registry.load_all()
        assert count == 0
        assert "自定义加载器失败" in caplog.text

    def test_load_from_yaml(self, tmp_path):
        yaml_path = tmp_path / "regions.yaml"
        yaml_path.write_text(
            "cities:\n"
            "  - name: 深圳\n"
            "    code: CN-GD-SZ\n"
            "    province: 广东\n"
            "    parent_code: CN-GD\n"
            "    region: 华南\n"
            "    year: 2024\n"
            "    gdp: 34606.4\n",
            encoding="utf-8",
        )
        registry = RegionRegistry()
        count = registry.load_from_yaml(yaml_path)
        assert count == 1
        assert registry.get("CN-GD-SZ") is not None

    def test_register_duplicate_returns_false(self, caplog):
        registry = RegionRegistry()
        r = Region(code="x", name="X", level=RegionLevel.CITY)
        assert registry.register(r) is True
        assert registry.register(r) is False


class TestRegionLoaderExtended:
    def test_load_level_based_format(self, tmp_path):
        yaml_path = tmp_path / "levels.yaml"
        yaml_path.write_text(
            "countries:\n"
            "  - {code: CN, name: 中国}\n"
            "provinces:\n"
            "  - {code: CN-GD, name: 广东, region: 华南}\n"
            "cities:\n"
            "  - {code: CN-GD-SZ, name: 深圳, parent_code: CN-GD, region: 华南}\n"
            "districts:\n"
            "  - {code: CN-GD-SZ-NS, name: 南山, parent_code: CN-GD-SZ}\n",
            encoding="utf-8",
        )
        loader = RegionLoader(yaml_path)
        regions = loader.load()
        codes = {r.code for r in regions}
        assert codes == {"CN", "CN-GD", "CN-GD-SZ", "CN-GD-SZ-NS"}

    def test_load_nested_provinces(self, tmp_path):
        yaml_path = tmp_path / "nested.yaml"
        yaml_path.write_text(
            "provinces:\n"
            "  - name: 广东\n"
            "    code: CN-GD\n"
            "    region: 华南\n"
            "    cities:\n"
            "      - name: 深圳\n"
            "        code: CN-GD-SZ\n"
            "        region: 华南\n"
            "        year: 2024\n"
            "        gdp: 34606.4\n",
            encoding="utf-8",
        )
        loader = RegionLoader(yaml_path)
        regions = loader.load()
        codes = {r.code for r in regions}
        assert "CN-GD" in codes
        assert "CN-GD-SZ" in codes
        sz = next(r for r in regions if r.code == "CN-GD-SZ")
        assert sz.parent_code == "CN-GD"

    def test_load_json(self, tmp_path):
        json_path = tmp_path / "regions.json"
        data = {
            "cities": [
                {
                    "name": "深圳",
                    "code": "CN-GD-SZ",
                    "province": "广东",
                    "parent_code": "CN-GD",
                    "region": "华南",
                    "year": 2024,
                    "gdp": 34606.4,
                }
            ]
        }
        json_path.write_text(json.dumps(data), encoding="utf-8")
        loader = RegionLoader(json_path)
        regions = loader.load()
        assert len(regions) == 1
        assert regions[0].name == "深圳"

    def test_load_unsupported_extension(self, tmp_path):
        bad_path = tmp_path / "regions.txt"
        bad_path.write_text("x")
        loader = RegionLoader(bad_path)
        with pytest.raises(ValueError, match="不支持"):
            loader.load()

    def test_load_missing_file(self, tmp_path):
        missing = tmp_path / "missing.yaml"
        loader = RegionLoader(missing)
        assert loader.load() == []

    def test_name_to_code_known(self):
        assert RegionLoader._name_to_code("深圳") == "shenzhen"
        assert RegionLoader._name_to_code("拉萨") == "lasa"

    def test_name_to_code_unknown(self):
        assert RegionLoader._name_to_code("未知城") == "未知城"


class TestLoaderDefaultRegions:
    def test_singleton(self):
        # Reset global singleton to test fresh load
        import backend.regions.registry as reg_module

        original = reg_module._registry
        reg_module._registry = None
        try:
            r1 = get_registry()
            r2 = get_registry()
            assert r1 is r2
            assert len(r1.list_all(RegionLevel.CITY)) >= 10
        finally:
            reg_module._registry = original

    def test_load_default_regions_has_country(self):
        registry = load_default_regions()
        assert registry.get("CN") is not None
