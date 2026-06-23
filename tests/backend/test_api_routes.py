"""
FastAPI 路由集成测试

覆盖 backend/api/routes/ 下各模块的主要端点，包含成功与错误/校验场景。
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi import status
from fastapi.testclient import TestClient

# --------------------------------------------------------------------------- #
# 共享常量
# --------------------------------------------------------------------------- #

CITY_CODES = ["CN-GD-SZ", "CN-SH-SH", "CN-BJ-BJ"]
CITY_NAMES = ["深圳", "上海", "北京"]
PROVINCE_NAME = "广东"
SUPPORTED_INDICATORS = ["gdp", "population", "rd_intensity"]


# --------------------------------------------------------------------------- #
# 夹具
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def _clear_sample_data():
    """清空 data.py 的内存示例数据，避免测试间互相污染。"""
    from backend.api.routes import data as data_module

    data_module._sample_data.clear()
    yield
    data_module._sample_data.clear()


@pytest.fixture
def seeded_api_client(api_client: TestClient) -> TestClient:
    """触发 lifespan 的 TestClient，确保路由与 city_manager/SQLite 初始化完成。"""
    with api_client:
        yield api_client


@pytest.fixture
def chart_dir(project_root_path: Path) -> Path:
    """确保静态图表目录存在，并在测试后清理创建的示例文件。"""
    charts = project_root_path / "data" / "charts"
    charts.mkdir(parents=True, exist_ok=True)
    yield charts


@pytest.fixture
def sample_csv() -> bytes:
    """生成可用于数据集上传的 CSV 字节。"""
    return ("city,year,gdp\n深圳,2023,32000\n深圳,2024,34606\n上海,2023,45000\n上海,2024,47218\n").encode("utf-8-sig")


@pytest.fixture
def sample_json() -> bytes:
    """生成可用于数据集上传的 JSON 字节。"""
    payload = [
        {"city": "深圳", "year": 2023, "indicator": "gdp", "value": 32000},
        {"city": "深圳", "year": 2024, "indicator": "gdp", "value": 34606},
    ]
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


@pytest.fixture
def survey_csv() -> bytes:
    """生成可用于调查数据上传的 CSV 字节。"""
    return (
        "region_code,year,indicator,value\nCN-GD-SZ,2024,community_happiness,85\nCN-GD-SZ,2025,community_happiness,87\n"
    ).encode("utf-8-sig")


# --------------------------------------------------------------------------- #
# 根路径 / 系统
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestMainRoutes:
    """测试 backend/api/main.py 中的根路径与系统端点。"""

    def test_root(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["status"] == "running"
        assert "Urban Pulse" in body["name"]

    def test_health_check(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/health")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["status"] == "healthy"
        assert "timestamp" in body

    def test_dashboard(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/dashboard")
        # frontend/index.html 存在时返回 200，否则返回 JSON 提示
        assert resp.status_code in (status.HTTP_200_OK, status.HTTP_200_OK)

    def test_favicon(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/favicon.ico")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.headers["content-type"] in ("image/x-icon", "image/svg+xml")


# --------------------------------------------------------------------------- #
# analysis.py
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestAnalysisRoutes:
    """测试产业分析相关端点。"""

    def test_enterprise_analysis(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/analysis/enterprise",
            json={"region": "深圳", "industry": "半导体", "year": 2025},
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["status"] == "success"
        assert "data" in body

    def test_enterprise_analysis_with_custom_data(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/analysis/enterprise",
            json={
                "region": "深圳",
                "industry": "半导体",
                "year": 2025,
                "data": {"land_price": 1000, "salary_level": 12000},
            },
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "success"

    def test_enterprise_sample_default(self, seeded_api_client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "backend.api.routes.analysis.real_data_analyzer.fetch_macro_data",
            lambda: pd.DataFrame({"gdp": [100, 110, 120]}),
        )
        resp = seeded_api_client.get("/api/v1/analysis/enterprise/sample")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["region"] == "深圳"
        assert "macro_reference" in body
        assert body["macro_reference"]["latest_gdp"] == 120.0

    def test_enterprise_sample_fallback_when_macro_fails(self, seeded_api_client: TestClient, monkeypatch):
        def _raise():
            raise RuntimeError("network down")

        monkeypatch.setattr(
            "backend.api.routes.analysis.real_data_analyzer.fetch_macro_data",
            _raise,
        )
        resp = seeded_api_client.get("/api/v1/analysis/enterprise/sample")
        assert resp.status_code == status.HTTP_200_OK
        assert "macro_reference" not in resp.json()

    def test_enterprise_location_success(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/analysis/enterprise/location/深圳")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["city"] == "深圳"
        assert "total_score" in body
        assert "details" in body

    def test_enterprise_location_not_found(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/analysis/enterprise/location/不存在的城市")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_enterprise_compare_success(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post("/api/v1/analysis/enterprise/compare", json=["深圳", "上海"])
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert set(body["cities"]) == {"深圳", "上海"}
        assert "comparison" in body

    def test_enterprise_compare_invalid_cities(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post("/api/v1/analysis/enterprise/compare", json=["不存在的城市"])
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_enterprise_case_semiconductor(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/analysis/enterprise/case/semiconductor")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["case_title"] == "半导体制造企业选址分析"
        assert "candidate_cities" in body

    def test_government_analysis(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/analysis/government",
            json={"region": "深圳", "industry": "半导体", "year": 2025},
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["status"] == "success"
        assert "fiscal_leverage" in body["data"]

    def test_analysis_config(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/analysis/config")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert "default_year" in body
        assert "score_weights" in body


# --------------------------------------------------------------------------- #
# cities.py
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestCitiesRoutes:
    """测试城市数据相关端点。"""

    def test_aggregate_success(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/cities/aggregate",
            json={
                "group_by": ["city"],
                "metrics": ["sum"],
                "sort_by": "sum",
                "sort_order": "desc",
                "limit": 5,
            },
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["success"] is True
        assert "groups" in body["result"]

    def test_aggregate_validation_error(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/cities/aggregate",
            json={"group_by": [], "metrics": ["sum"]},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_compare_success(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/cities/compare",
            json={
                "city_codes": CITY_CODES[:2],
                "indicators": ["gdp"],
                "year_start": 2020,
                "year_end": 2025,
            },
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["success"] is True
        assert "cities" in body["comparison"]

    def test_compare_unknown_city(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/cities/compare",
            json={
                "city_codes": ["CN-XX-XX"],
                "indicators": ["gdp"],
                "year_start": 2020,
                "year_end": 2025,
            },
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_compare_year_range_validation(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/cities/compare",
            json={
                "city_codes": CITY_CODES[:2],
                "indicators": ["gdp"],
                "year_start": 2025,
                "year_end": 2020,
            },
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_time_series_success(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/cities/time-series",
            json={
                "city_codes": CITY_CODES[:2],
                "indicator": "gdp",
                "year_start": 2020,
                "year_end": 2025,
            },
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["success"] is True
        assert "groups" in body["time_series"]

    def test_time_series_unknown_city(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/cities/time-series",
            json={
                "city_codes": ["CN-XX-XX"],
                "indicator": "gdp",
                "year_start": 2020,
                "year_end": 2025,
            },
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_regional_success(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/cities/regional",
            json={"region_field": "province", "indicators": ["gdp"]},
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["success"] is True
        assert "regional_analysis" in body

    def test_correlation_success(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/cities/correlation",
            json={
                "city_codes": CITY_CODES[:2],
                "indicators": ["gdp", "population"],
                "year_start": 2020,
                "year_end": 2025,
            },
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["success"] is True
        assert "correlation" in body

    def test_correlation_validation_min_cities(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/cities/correlation",
            json={
                "city_codes": [CITY_CODES[0]],
                "indicators": ["gdp", "population"],
                "year_start": 2020,
                "year_end": 2025,
            },
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_rankings_success(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/cities/rankings?indicator=gdp&year=2024&limit=5")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["success"] is True
        assert len(body["rankings"]) <= 5

    def test_dashboard_success(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get(f"/api/v1/cities/dashboard?city_code={CITY_CODES[0]}")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["success"] is True
        assert body["dashboard"]["city_info"]["code"] == CITY_CODES[0]

    def test_dashboard_city_not_found(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/cities/dashboard?city_code=CN-XX-XX")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_list_cities(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/cities/list")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert "cities" in body
        assert body["total"] == len(body["cities"])

    def test_benchmarks_scores(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/cities/benchmarks/scores")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert "benchmarks" in body
        assert "weights" in body

    def test_quality_report(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/cities/quality/report")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert "total_cities" in body
        assert "quality_by_city" in body

    def test_city_detail_success(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/cities/深圳")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["city"] == "深圳"
        assert "data" in body

    def test_city_detail_not_found(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/cities/不存在的城市")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_city_historical_success(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/cities/深圳/historical")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["city"] == "深圳"
        assert "historical_data" in body

    def test_city_historical_not_found(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/cities/不存在的城市/historical")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# --------------------------------------------------------------------------- #
# data.py
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestDataRoutes:
    """测试数据管理相关端点。"""

    def test_create_indicator(self, seeded_api_client: TestClient):
        payload = {
            "code": "gdp",
            "name": "GDP",
            "value": 35000.0,
            "unit": "亿元",
            "year": 2025,
            "category": "经济",
            "region": "深圳",
            "source": "test",
        }
        resp = seeded_api_client.post("/api/v1/data/", json=payload)
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["code"] == "gdp"
        assert body["id"] == 1

    def test_list_indicators(self, seeded_api_client: TestClient):
        seeded_api_client.post(
            "/api/v1/data/",
            json={"code": "gdp", "name": "GDP", "value": 35000, "category": "经济"},
        )
        resp = seeded_api_client.get("/api/v1/data/?category=经济&page=1&page_size=10")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["total"] >= 1
        assert body["page"] == 1

    def test_list_indicators_filter_by_code(self, seeded_api_client: TestClient):
        seeded_api_client.post(
            "/api/v1/data/",
            json={"code": "population", "name": "人口", "value": 1800},
        )
        resp = seeded_api_client.get("/api/v1/data/?code=population")
        assert resp.status_code == status.HTTP_200_OK
        assert all(d["code"] == "population" for d in resp.json()["data"])

    def test_get_indicator_success(self, seeded_api_client: TestClient):
        seeded_api_client.post(
            "/api/v1/data/",
            json={"code": "gdp", "name": "GDP", "value": 35000},
        )
        resp = seeded_api_client.get("/api/v1/data/1")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["id"] == 1

    def test_get_indicator_not_found(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/data/9999")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_list_categories(self, seeded_api_client: TestClient):
        seeded_api_client.post(
            "/api/v1/data/",
            json={"code": "gdp", "name": "GDP", "value": 35000, "category": "经济"},
        )
        resp = seeded_api_client.get("/api/v1/data/categories/list")
        assert resp.status_code == status.HTTP_200_OK
        assert "经济" in resp.json()["categories"]

    def test_list_codes(self, seeded_api_client: TestClient):
        seeded_api_client.post(
            "/api/v1/data/",
            json={"code": "gdp", "name": "GDP", "value": 35000, "category": "经济"},
        )
        resp = seeded_api_client.get("/api/v1/data/codes/list?category=经济")
        assert resp.status_code == status.HTTP_200_OK
        codes = [c["code"] for c in resp.json()["codes"]]
        assert "gdp" in codes

    def test_basic_data(self, seeded_api_client: TestClient, project_root_path: Path):
        # 确保示例数据文件存在
        basic_file = project_root_path / "examples" / "shenzhen_semiconductor_2025" / "data" / "basic_data.json"
        basic_file.parent.mkdir(parents=True, exist_ok=True)
        if not basic_file.exists():
            basic_file.write_text(json.dumps({"region": "深圳", "year": 2025}), encoding="utf-8")
        resp = seeded_api_client.get("/api/v1/data/basic")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["region"] == "深圳"

    def test_basic_data_not_found(self, seeded_api_client: TestClient, project_root_path: Path, monkeypatch):
        # 临时让示例文件路径指向不存在目录
        monkeypatch.setattr(
            "backend.api.routes.data.get_example_data_path",
            lambda _filename: project_root_path / "__nonexistent__" / "basic_data.json",
        )
        resp = seeded_api_client.get("/api/v1/data/basic")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_trend_data_default(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/data/trend")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["region"] == "深圳"
        assert len(body["years"]) == 6

    def test_trend_data_invalid_range(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/data/trend?start_year=2025&end_year=2020")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_map_data(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/data/map?indicator=output&year=2025")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["indicator"] == "output"
        assert len(body["values"]) > 0


# --------------------------------------------------------------------------- #
# datasets.py
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestDatasetsRoutes:
    """测试数据集上传与管理相关端点。"""

    def test_upload_csv(self, seeded_api_client: TestClient, sample_csv: bytes):
        resp = seeded_api_client.post(
            "/api/v1/datasets/upload",
            files={"file": ("test.csv", io.BytesIO(sample_csv), "text/csv")},
            data={"name": "测试CSV", "description": "unit test"},
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["message"] == "imported"
        assert "dataset" in body

    def test_upload_json(self, seeded_api_client: TestClient, sample_json: bytes):
        resp = seeded_api_client.post(
            "/api/v1/datasets/upload",
            files={"file": ("test.json", io.BytesIO(sample_json), "application/json")},
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["message"] == "imported"

    def test_upload_invalid_extension(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/datasets/upload",
            files={"file": ("test.txt", io.BytesIO(b"x"), "text/plain")},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_empty_filename(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/datasets/upload",
            files={"file": ("", io.BytesIO(b"x"), "text/csv")},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_list_datasets(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/datasets")
        assert resp.status_code == status.HTTP_200_OK
        assert "datasets" in resp.json()

    def test_dataset_crud_flow(self, seeded_api_client: TestClient, sample_csv: bytes):
        # upload
        upload_resp = seeded_api_client.post(
            "/api/v1/datasets/upload",
            files={"file": ("crud.csv", io.BytesIO(sample_csv), "text/csv")},
            data={"name": "CRUD测试"},
        )
        ds_id = upload_resp.json()["dataset"]["id"]

        # detail
        detail_resp = seeded_api_client.get(f"/api/v1/datasets/{ds_id}")
        assert detail_resp.status_code == status.HTTP_200_OK
        assert detail_resp.json()["dataset"]["id"] == ds_id

        # update
        update_resp = seeded_api_client.put(
            f"/api/v1/datasets/{ds_id}",
            json={"name": "CRUD已更新", "description": "updated"},
        )
        assert update_resp.status_code == status.HTTP_200_OK
        assert update_resp.json()["dataset"]["name"] == "CRUD已更新"

        # data
        data_resp = seeded_api_client.get(f"/api/v1/datasets/{ds_id}/data")
        assert data_resp.status_code == status.HTTP_200_OK
        assert data_resp.json()["count"] >= 4

        # entities / indicators
        entities_resp = seeded_api_client.get(f"/api/v1/datasets/{ds_id}/entities")
        assert entities_resp.status_code == status.HTTP_200_OK
        assert "深圳" in entities_resp.json()["entities"]

        indicators_resp = seeded_api_client.get(f"/api/v1/datasets/{ds_id}/indicators")
        assert indicators_resp.status_code == status.HTTP_200_OK
        assert "gdp" in indicators_resp.json()["indicators"]

        # pivot
        pivot_resp = seeded_api_client.get(f"/api/v1/datasets/{ds_id}/pivot?indicators=gdp")
        assert pivot_resp.status_code == status.HTTP_200_OK
        assert pivot_resp.json()["count"] >= 2

        # delete
        delete_resp = seeded_api_client.delete(f"/api/v1/datasets/{ds_id}")
        assert delete_resp.status_code == status.HTTP_200_OK
        assert delete_resp.json()["message"] == "deleted"

        # verify 404
        get_resp = seeded_api_client.get(f"/api/v1/datasets/{ds_id}")
        assert get_resp.status_code == status.HTTP_404_NOT_FOUND

    def test_dataset_detail_not_found(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/datasets/__missing__")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_dataset_data_filters(self, seeded_api_client: TestClient, sample_csv: bytes):
        upload_resp = seeded_api_client.post(
            "/api/v1/datasets/upload",
            files={"file": ("filter.csv", io.BytesIO(sample_csv), "text/csv")},
        )
        ds_id = upload_resp.json()["dataset"]["id"]
        resp = seeded_api_client.get(
            f"/api/v1/datasets/{ds_id}/data?entity=深圳&indicator=gdp&year_start=2024&year_end=2024"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["count"] == 1


# --------------------------------------------------------------------------- #
# forecast.py
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestForecastRoutes:
    """测试预测相关端点。"""

    def test_list_supported_indicators(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/forecast/indicators")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert "gdp" in body["supported_indicators"]

    def test_list_supported_provinces(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/forecast/provinces")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert any(p["province"] == PROVINCE_NAME for p in body["provinces"])

    def test_forecast_city_gdp(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/forecast/gdp/深圳?forecast_years=3")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["city"] == "深圳"
        assert len(body["forecast_data"]) == 3

    def test_forecast_city_gdp_not_found(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/forecast/gdp/不存在的城市")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_forecast_city_indicator(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/forecast/indicator/上海?indicator=population&forecast_years=3")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["city"] == "上海"
        assert body["indicator"] == "population"

    def test_forecast_city_indicator_unsupported(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/forecast/indicator/深圳?indicator=not_a_metric")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_compare_forecasts(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/forecast/compare",
            json={"city_names": ["深圳", "上海"], "indicator": "gdp", "forecast_years": 3},
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert "forecasts" in body
        assert "comparison" in body

    def test_compare_forecasts_invalid_indicator(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/forecast/compare",
            json={"city_names": ["深圳"], "indicator": "not_a_metric", "forecast_years": 3},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_forecast_all_provinces(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/forecast/province/all?indicator=gdp&forecast_years=3")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert "provinces" in body
        assert "comparison" in body

    def test_forecast_province(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/forecast/province/广东",
            json={"indicator": "gdp", "forecast_years": 3},
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["province"] == "广东"
        assert body["indicator"] == "gdp"

    def test_forecast_province_not_found(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/forecast/province/不存在的省",
            json={"indicator": "gdp", "forecast_years": 3},
        )
        assert resp.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_forecast_full_report(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/forecast/report/full?indicator=gdp&forecast_years=3")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert "city_forecasts" in body
        assert "comparison_by_cagr" in body


# --------------------------------------------------------------------------- #
# health.py
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestHealthRoutes:
    """测试 CEHI 健康指数相关端点。"""

    def test_get_indicators(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/health/indicators")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert "dimensions" in body
        assert "indicators" in body
        assert "health_levels" in body

    def test_calculate_cehi(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/health/calculate",
            json={"city_name": "深圳", "year": 2024},
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["city_name"] == "深圳"
        assert "total_score" in body

    def test_calculate_cehi_with_values(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/health/calculate",
            json={
                "city_name": "深圳",
                "year": 2024,
                "indicator_values": {"gdp_growth": 6.0, "rd_intensity": 3.0},
            },
        )
        assert resp.status_code == status.HTTP_200_OK
        assert "total_score" in resp.json()

    def test_benchmark_cehi(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/health/benchmark",
            json={
                "target_city": "深圳",
                "year": 2024,
                "peers": {
                    "上海": {"gdp_growth": 5.0, "rd_intensity": 2.5},
                    "北京": {"gdp_growth": 5.2, "rd_intensity": 3.5},
                },
            },
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["target_city"] == "深圳"
        assert "rankings" in body

    def test_get_demo(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/health/demo")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert "total_score" in body

    def test_download_template_xlsx(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/health/template?format=xlsx")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.headers["content-type"].startswith("application/vnd.openxmlformats")

    def test_download_template_csv(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/health/template?format=csv")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.headers["content-type"].startswith("text/csv")

    def test_download_template_invalid(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/health/template?format=pdf")
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_import_indicators_csv(self, seeded_api_client: TestClient):
        from backend.core.health_data_io import export_indicator_template

        content = export_indicator_template("csv")
        resp = seeded_api_client.post(
            "/api/v1/health/import",
            files={"file": ("indicators.csv", io.BytesIO(content), "text/csv")},
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert "indicator_values" in body
        assert isinstance(body["missing"], list)

    def test_import_indicators_empty(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/health/import",
            files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_export_pdf(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/health/report/pdf",
            json={"city_name": "深圳", "year": 2024},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.headers["content-type"] == "application/pdf"
        assert "Content-Disposition" in resp.headers


# --------------------------------------------------------------------------- #
# index.py
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestIndexRoutes:
    """测试竞争力指数相关端点。"""

    def test_compute_index_default(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post("/api/v1/index/compute", json={})
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert "rankings" in body
        assert "overall" in body["rankings"]

    def test_compute_index_with_cities(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/index/compute",
            json={"city_codes": ["深圳", "上海"], "method": "entropy"},
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert "rankings" in body

    def test_compute_index_invalid_method_fallback(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/index/compute",
            json={"method": "invalid"},
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_rankings_overall(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/index/rankings")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["dimension"] == "overall"
        assert "rankings" in body

    def test_rankings_by_dimension(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/index/rankings?dimension=科技力")
        # 维度是否存在取决于 IndicatorFramework，不存在应返回 404
        assert resp.status_code in (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND)

    def test_city_report_success(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post("/api/v1/index/report/深圳", json={})
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert "city" in body or "error" not in body

    def test_city_report_not_found(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post("/api/v1/index/report/不存在的城市", json={})
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# --------------------------------------------------------------------------- #
# regions.py
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestRegionsRoutes:
    """测试区域相关端点。"""

    def test_region_summary(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/regions/summary")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["success"] is True
        assert "summary" in body

    def test_list_regions(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/regions?limit=10")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["success"] is True
        assert "regions" in body

    def test_list_regions_by_level(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/regions?level=city&limit=5")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["success"] is True
        assert all(r.get("level") == "city" for r in body["regions"])

    def test_list_regions_forecastable(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/regions?forecastable=true&limit=5")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["success"] is True

    def test_get_region_success(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get(f"/api/v1/regions/{CITY_CODES[0]}")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["success"] is True
        assert body["region"]["code"] == CITY_CODES[0]

    def test_get_region_not_found(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/regions/CN-XX-XX")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_get_region_time_series(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get(f"/api/v1/regions/{CITY_CODES[0]}/time-series/gdp?start_year=2020&end_year=2024")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["success"] is True
        assert body["indicator"] == "gdp"
        assert body["count"] > 0

    def test_forecast_region_indicator(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get(f"/api/v1/regions/{CITY_CODES[0]}/forecast/gdp?forecast_years=3")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["success"] is True
        assert "forecast_values" in body

    def test_forecast_region_not_found(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/regions/CN-XX-XX/forecast/gdp")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_batch_forecast(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/regions/batch/forecast",
            json={"codes": CITY_CODES[:2], "indicator": "gdp", "forecast_years": 3},
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["success"] is True
        assert "results" in body
        assert "comparison" in body

    def test_upload_survey_data(self, seeded_api_client: TestClient, survey_csv: bytes):
        resp = seeded_api_client.post(
            "/api/v1/regions/survey/upload?overwrite=true",
            files={"file": ("survey.csv", io.BytesIO(survey_csv), "text/csv")},
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["success"] is True
        assert "stats" in body

    def test_upload_survey_invalid_format(self, seeded_api_client: TestClient):
        resp = seeded_api_client.post(
            "/api/v1/regions/survey/upload",
            files={"file": ("survey.txt", io.BytesIO(b"x"), "text/plain")},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_region_survey_indicators(self, seeded_api_client: TestClient, survey_csv: bytes):
        seeded_api_client.post(
            "/api/v1/regions/survey/upload?overwrite=true",
            files={"file": ("survey2.csv", io.BytesIO(survey_csv), "text/csv")},
        )
        resp = seeded_api_client.get(f"/api/v1/regions/{CITY_CODES[0]}/survey")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["success"] is True
        assert "survey_indicators" in body

    def test_get_region_survey_single_indicator(self, seeded_api_client: TestClient, survey_csv: bytes):
        seeded_api_client.post(
            "/api/v1/regions/survey/upload?overwrite=true",
            files={"file": ("survey3.csv", io.BytesIO(survey_csv), "text/csv")},
        )
        resp = seeded_api_client.get(f"/api/v1/regions/{CITY_CODES[0]}/survey?indicator=community_happiness")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["success"] is True
        assert "data" in body


# --------------------------------------------------------------------------- #
# static.py
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestStaticRoutes:
    """测试静态资源相关端点。"""

    def test_list_charts_empty(self, seeded_api_client: TestClient, chart_dir: Path):
        # 清理已有 png 避免干扰
        for f in chart_dir.glob("*.png"):
            f.unlink()
        resp = seeded_api_client.get("/api/v1/static/charts/list")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["status"] == "success"
        assert body["charts"] == []

    def test_list_charts_with_file(self, seeded_api_client: TestClient, chart_dir: Path):
        chart_file = chart_dir / "test_chart.png"
        chart_file.write_bytes(b"\x89PNG\r\n\x1a\n")
        try:
            resp = seeded_api_client.get("/api/v1/static/charts/list")
            assert resp.status_code == status.HTTP_200_OK
            names = [c["filename"] for c in resp.json()["charts"]]
            assert "test_chart.png" in names
        finally:
            chart_file.unlink(missing_ok=True)

    def test_get_chart_success(self, seeded_api_client: TestClient, chart_dir: Path):
        chart_file = chart_dir / "sample.png"
        chart_file.write_bytes(b"\x89PNG\r\n\x1a\n")
        try:
            resp = seeded_api_client.get("/api/v1/static/charts/sample.png")
            assert resp.status_code == status.HTTP_200_OK
            assert resp.headers["content-type"] == "image/png"
        finally:
            chart_file.unlink(missing_ok=True)

    def test_get_chart_not_found(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/static/charts/nonexistent.png")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_get_chart_invalid_filename(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/static/charts/.hidden.png")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_chart_backslash_rejected(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/static/charts/foo%5Cbar.png")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# --------------------------------------------------------------------------- #
# industries.py (额外补充，提升路由覆盖)
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestIndustriesRoutes:
    """测试产业相关端点。"""

    def test_industry_summary(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/industries/summary")
        assert resp.status_code == status.HTTP_200_OK
        assert "summary" in resp.json()

    def test_list_industries(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/industries")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["success"] is True
        assert "industries" in body

    def test_create_and_get_industry(self, seeded_api_client: TestClient):
        payload = {
            "code": "test_semiconductor",
            "name": "测试半导体",
            "region_code": CITY_CODES[0],
            "level": "secondary",
            "category": "制造",
            "key_indicators": {"output_value": {"unit": "亿元"}},
            "historical_data": [{"year": 2022, "output_value": 1000}],
            "factors": [],
        }
        create_resp = seeded_api_client.post("/api/v1/industries", json=payload)
        assert create_resp.status_code == status.HTTP_200_OK

        get_resp = seeded_api_client.get(f"/api/v1/industries/{CITY_CODES[0]}/test_semiconductor")
        assert get_resp.status_code == status.HTTP_200_OK
        body = get_resp.json()
        assert body["success"] is True
        assert body["industry"]["code"] == "test_semiconductor"

    def test_create_industry_region_not_found(self, seeded_api_client: TestClient):
        payload = {
            "code": "test",
            "name": "测试",
            "region_code": "CN-XX-XX",
            "level": "secondary",
        }
        resp = seeded_api_client.post("/api/v1/industries", json=payload)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_get_industry_not_found(self, seeded_api_client: TestClient):
        resp = seeded_api_client.get("/api/v1/industries/CN-GD-SZ/not_exists")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_forecast_industry(self, seeded_api_client: TestClient):
        payload = {
            "code": "test_forecast",
            "name": "测试预测产业",
            "region_code": CITY_CODES[0],
            "level": "secondary",
            "historical_data": [
                {"year": 2020, "output_value": 100},
                {"year": 2021, "output_value": 110},
                {"year": 2022, "output_value": 120},
                {"year": 2023, "output_value": 130},
                {"year": 2024, "output_value": 140},
            ],
            "factors": [],
        }
        seeded_api_client.post("/api/v1/industries", json=payload)
        resp = seeded_api_client.post(
            f"/api/v1/industries/{CITY_CODES[0]}/test_forecast/forecast",
            json={"indicator": "output_value", "forecast_years": 3, "use_factors": False},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert "forecast" in resp.json() or "forecast_values" in resp.json()
