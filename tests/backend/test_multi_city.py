"""Tests for backend.core.multi_city."""

from __future__ import annotations

import json

import pytest
import yaml

from backend.core.multi_city import CityConfig, CityData, CityDataManager


@pytest.fixture
def manager():
    return CityDataManager()


@pytest.fixture
def sz_config():
    return CityConfig(
        code="sz",
        name="深圳",
        province="广东",
        latitude=22.5,
        longitude=114.0,
        population=1750,
        gdp_rank=3,
        tags=["一线城市", "科技"],
    )


@pytest.fixture
def gz_config():
    return CityConfig(
        code="gz",
        name="广州",
        province="广东",
        latitude=23.1,
        longitude=113.2,
        population=1800,
        gdp_rank=4,
        tags=["一线城市"],
    )


class TestCityDataManager:
    def test_register_and_get_city(self, manager, sz_config):
        assert manager.register_city(sz_config) is True
        assert manager.get_city("sz") == sz_config
        assert manager.register_city(sz_config) is False

    def test_unregister_city(self, manager, sz_config):
        manager.register_city(sz_config)
        assert manager.unregister_city("sz") is True
        assert manager.get_city("sz") is None
        assert manager.unregister_city("sz") is False

    def test_list_cities_with_filters(self, manager, sz_config, gz_config):
        manager.register_city(sz_config)
        manager.register_city(gz_config)
        assert len(manager.list_cities()) == 2
        assert len(manager.list_cities({"province": "广东"})) == 2
        assert len(manager.list_cities({"tags": "科技"})) == 1
        assert len(manager.list_cities({"tags": ["一线城市"]})) == 2
        assert len(manager.list_cities({"gdp_rank_le": 3})) == 1

    def test_add_and_get_city_data(self, manager, sz_config):
        manager.register_city(sz_config)
        data = CityData(
            city_code="sz",
            city_name="深圳",
            year=2024,
            indicators={"gdp": 35000.0},
        )
        assert manager.add_city_data(data) is True
        assert len(manager.get_city_data("sz")) == 1
        assert len(manager.get_city_data("sz", 2024)) == 1
        assert len(manager.get_city_data("sz", 2023)) == 0
        assert manager.get_city_data("missing") == []

    def test_add_city_data_missing_city(self, manager):
        data = CityData(city_code="missing", city_name="Missing", year=2024)
        assert manager.add_city_data(data) is False

    def test_compare_cities(self, manager, sz_config, gz_config):
        manager.register_city(sz_config)
        manager.register_city(gz_config)
        manager.add_city_data(
            CityData(city_code="sz", city_name="深圳", year=2024, indicators={"gdp": 35000.0})
        )
        manager.add_city_data(
            CityData(city_code="gz", city_name="广州", year=2024, indicators={"gdp": 30000.0})
        )
        result = manager.compare_cities(["sz", "gz"], 2024, ["gdp"])
        assert result["sz"]["indicators"]["gdp"] == 35000.0
        assert result["gz"]["indicators"]["gdp"] == 30000.0

    def test_export_city_summary(self, manager, sz_config, tmp_path):
        manager.register_city(sz_config)
        path = tmp_path / "summary.json"
        assert manager.export_city_summary(path) is True
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["total_cities"] == 1
        assert data["cities"][0]["code"] == "sz"

    def test_load_custom_cities(self, manager, tmp_path):
        config = {
            "cities": [
                {
                    "code": "hz",
                    "name": "杭州",
                    "province": "浙江",
                    "latitude": 30.2,
                    "longitude": 120.1,
                    "population": 1200,
                    "gdp_rank": 8,
                    "tags": ["新一线"],
                }
            ]
        }
        path = tmp_path / "cities.yaml"
        path.write_text(yaml.safe_dump(config), encoding="utf-8")
        count = manager.load_custom_cities(path)
        assert count == 1
        assert manager.get_city("hz") is not None

    def test_load_custom_cities_failure(self, manager, tmp_path):
        path = tmp_path / "bad.yaml"
        path.write_text("not yaml: [", encoding="utf-8")
        assert manager.load_custom_cities(path) == 0

    def test_global_instance(self):
        from backend.core.multi_city import city_manager

        assert isinstance(city_manager, CityDataManager)
