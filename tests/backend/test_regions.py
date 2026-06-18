"""区域管理模块测试"""

from __future__ import annotations

import pytest

from backend.regions import Region, RegionLevel, RegionRegistry, get_registry
from backend.regions.loader import RegionLoader, load_default_regions
from backend.regions.survey_integration import attach_survey_records


class TestRegionModel:
    def test_region_creation(self):
        r = Region(code="CN-GD-SZ", name="深圳", level=RegionLevel.CITY, parent_code="CN-GD", region="华南")
        assert r.code == "CN-GD-SZ"
        assert r.name == "深圳"
        assert r.level == RegionLevel.CITY
        assert r.has_time_series is False

    def test_region_time_series(self):
        r = Region(
            code="CN-GD-SZ",
            name="深圳",
            level=RegionLevel.CITY,
            historical_data=[
                {"year": 2020, "gdp": 100.0},
                {"year": 2021, "gdp": 110.0},
                {"year": 2022, "gdp": 120.0},
            ],
        )
        assert r.has_time_series is True
        assert r.get_time_series("gdp") == [100.0, 110.0, 120.0]
        assert r.latest_year == 2022

    def test_region_summary(self):
        r = Region(code="CN", name="中国", level=RegionLevel.COUNTRY)
        summary = r.to_summary()
        assert summary["code"] == "CN"
        assert summary["level"] == "country"


class TestRegionRegistry:
    def test_register_and_get(self):
        registry = RegionRegistry()
        r = Region(code="test", name="测试", level=RegionLevel.CITY)
        assert registry.register(r) is True
        assert registry.get("test") == r
        assert registry.register(r) is False

    def test_list_by_level(self):
        registry = RegionRegistry()
        registry.register(Region(code="CN", name="中国", level=RegionLevel.COUNTRY))
        registry.register(Region(code="CN-GD", name="广东", level=RegionLevel.PROVINCE))
        registry.register(Region(code="CN-GD-SZ", name="深圳", level=RegionLevel.CITY))
        assert len(registry.list_all(RegionLevel.COUNTRY)) == 1
        assert len(registry.list_all(RegionLevel.PROVINCE)) == 1
        assert len(registry.list_all(RegionLevel.CITY)) == 1

    def test_list_by_parent(self):
        registry = RegionRegistry()
        registry.register(Region(code="CN-GD", name="广东", level=RegionLevel.PROVINCE))
        registry.register(Region(code="CN-GD-SZ", name="深圳", level=RegionLevel.CITY, parent_code="CN-GD"))
        children = registry.list_by_parent("CN-GD")
        assert len(children) == 1
        assert children[0].name == "深圳"

    def test_forecastable(self):
        registry = RegionRegistry()
        registry.register(
            Region(
                code="CN-GD-SZ",
                name="深圳",
                level=RegionLevel.CITY,
                historical_data=[
                    {"year": 2020, "gdp": 100.0},
                    {"year": 2021, "gdp": 110.0},
                    {"year": 2022, "gdp": 120.0},
                ],
            )
        )
        registry.register(Region(code="CN-BJ", name="北京", level=RegionLevel.CITY))
        assert len(registry.list_forecastable("gdp")) == 1


class TestRegionLoader:
    def test_load_default_regions(self):
        registry = load_default_regions()
        summary = registry.region_summary()
        assert summary["total"] > 0
        assert summary["by_level"]["city"] >= 10
        assert summary["by_level"]["province"] >= 10
        assert summary["forecastable"] >= 10

    def test_get_registry_singleton(self):
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2


class TestRegionLoaderYaml:
    def test_parse_city_format(self, tmp_path):
        yaml_path = tmp_path / "cities.yaml"
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
        loader = RegionLoader(yaml_path)
        regions = loader.load()
        assert len(regions) == 1
        assert regions[0].name == "深圳"
        assert regions[0].code == "CN-GD-SZ"


class TestSurveyUploadAPI:
    def test_upload_survey_csv(self, api_client):
        csv_content = (
            "region_code,year,indicator,value,source\n"
            "CN-GD-SZ,2023,social_satisfaction,78.5,test\n"
            "CN-GD-SZ,2023,environment_satisfaction,82.1,test\n"
        )
        response = api_client.post(
            "/api/v1/regions/survey/upload",
            files={"file": ("survey.csv", csv_content, "text/csv")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "social_satisfaction" in data["indicators"]
        assert data["stats"]["attached"] == 2

    def test_get_region_survey_indicators(self, api_client):
        registry = get_registry()
        registry.register(Region(code="CN-TEST", name="测试区", level=RegionLevel.CITY))
        attach_survey_records(
            registry,
            [
                {"region_code": "CN-TEST", "year": 2023, "indicator": "social_satisfaction", "value": 78.5},
            ],
        )
        response = api_client.get("/api/v1/regions/CN-TEST/survey")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "social_satisfaction" in data["survey_indicators"]

    def test_get_region_survey_time_series(self, api_client):
        registry = get_registry()
        registry.register(Region(code="CN-TEST2", name="测试区2", level=RegionLevel.CITY))
        attach_survey_records(
            registry,
            [
                {"region_code": "CN-TEST2", "year": 2022, "indicator": "social_satisfaction", "value": 76.0},
                {"region_code": "CN-TEST2", "year": 2023, "indicator": "social_satisfaction", "value": 78.5},
            ],
        )
        response = api_client.get("/api/v1/regions/CN-TEST2/survey?indicator=social_satisfaction")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        assert data["data"][-1]["value"] == 78.5
