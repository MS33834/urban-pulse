"""
API 契约测试 — 使用 FastAPI 生成的 OpenAPI schema 校验关键响应。

标记: contract
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.contract


# --------------------------------------------------------------------------- #
# 共享 helper
# --------------------------------------------------------------------------- #


def _extract_schema(openapi: dict[str, Any]) -> dict[str, Any]:
    """构造可用于 jsonschema.validate 的 schema 字典(包含内部 $ref 解析)。"""
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "components": openapi.get("components", {}),
    }
    return schema


def _get_response_schema(openapi: dict[str, Any], path: str, method: str, status: str) -> dict[str, Any] | None:
    """从 OpenAPI 文档中提取指定路径/方法/状态码的 response schema。"""
    path_item = openapi["paths"].get(path)
    if path_item is None:
        return None
    op = path_item.get(method.lower())
    if op is None:
        return None
    responses = op.get("responses", {})
    response = responses.get(str(status), responses.get("default", {}))
    content = response.get("content", {})
    media = content.get("application/json", {})
    return media.get("schema")


def _validate_json(data: Any, schema: dict[str, Any], openapi: dict[str, Any]) -> None:
    """使用 OpenAPI components 作为参考解析 $ref 后校验 JSON。"""
    resolver = jsonschema.RefResolver(
        base_uri="",
        referrer=openapi,
        store={"": openapi},
    )
    jsonschema.validate(instance=data, schema=schema, resolver=resolver)


@pytest.fixture
def openapi_doc(api_client: TestClient) -> dict[str, Any]:
    """获取 /openapi.json 并解析为字典。"""
    response = api_client.get("/openapi.json")
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def seeded_client(api_client: TestClient) -> TestClient:
    """触发 lifespan 的客户端,保证路由依赖(如 city_manager)已初始化。"""
    with api_client:
        yield api_client


# --------------------------------------------------------------------------- #
# 根路径 / 系统
# --------------------------------------------------------------------------- #


def test_root_contract(seeded_client: TestClient, openapi_doc: dict[str, Any]):
    schema = _get_response_schema(openapi_doc, "/", "get", "200")
    assert schema is not None, "/ schema 未在 OpenAPI 中声明"
    response = seeded_client.get("/")
    assert response.status_code == 200
    _validate_json(response.json(), schema, openapi_doc)


def test_health_contract(seeded_client: TestClient, openapi_doc: dict[str, Any]):
    schema = _get_response_schema(openapi_doc, "/health", "get", "200")
    assert schema is not None, "/health schema 未在 OpenAPI 中声明"
    response = seeded_client.get("/health")
    assert response.status_code == 200
    _validate_json(response.json(), schema, openapi_doc)


# --------------------------------------------------------------------------- #
# 城市
# --------------------------------------------------------------------------- #


def test_cities_list_contract(seeded_client: TestClient, openapi_doc: dict[str, Any]):
    schema = _get_response_schema(openapi_doc, "/api/v1/cities/list", "get", "200")
    assert schema is not None, "/api/v1/cities/list schema 未声明"
    response = seeded_client.get("/api/v1/cities/list")
    assert response.status_code == 200
    _validate_json(response.json(), schema, openapi_doc)


def test_cities_rankings_contract(seeded_client: TestClient, openapi_doc: dict[str, Any]):
    schema = _get_response_schema(openapi_doc, "/api/v1/cities/rankings", "get", "200")
    assert schema is not None
    response = seeded_client.get("/api/v1/cities/rankings?indicator=gdp&year=2024&limit=5")
    assert response.status_code == 200
    _validate_json(response.json(), schema, openapi_doc)


def test_cities_compare_contract(seeded_client: TestClient, openapi_doc: dict[str, Any]):
    schema = _get_response_schema(openapi_doc, "/api/v1/cities/compare", "post", "200")
    assert schema is not None
    payload = {
        "city_codes": ["CN-GD-SZ", "CN-SH-SH"],
        "indicators": ["gdp"],
        "year_start": 2020,
        "year_end": 2025,
    }
    response = seeded_client.post("/api/v1/cities/compare", json=payload)
    assert response.status_code == 200
    _validate_json(response.json(), schema, openapi_doc)


# --------------------------------------------------------------------------- #
# 分析
# --------------------------------------------------------------------------- #


def test_analysis_enterprise_contract(seeded_client: TestClient, openapi_doc: dict[str, Any]):
    schema = _get_response_schema(openapi_doc, "/api/v1/analysis/enterprise", "post", "200")
    assert schema is not None
    payload = {"region": "深圳", "industry": "半导体", "year": 2025}
    response = seeded_client.post("/api/v1/analysis/enterprise", json=payload)
    assert response.status_code == 200
    _validate_json(response.json(), schema, openapi_doc)


def test_analysis_government_contract(seeded_client: TestClient, openapi_doc: dict[str, Any]):
    schema = _get_response_schema(openapi_doc, "/api/v1/analysis/government", "post", "200")
    assert schema is not None
    payload = {"region": "深圳", "industry": "半导体", "year": 2025}
    response = seeded_client.post("/api/v1/analysis/government", json=payload)
    assert response.status_code == 200
    _validate_json(response.json(), schema, openapi_doc)


def test_analysis_config_contract(seeded_client: TestClient, openapi_doc: dict[str, Any]):
    schema = _get_response_schema(openapi_doc, "/api/v1/analysis/config", "get", "200")
    assert schema is not None
    response = seeded_client.get("/api/v1/analysis/config")
    assert response.status_code == 200
    _validate_json(response.json(), schema, openapi_doc)


# --------------------------------------------------------------------------- #
# 产业 / 区域 / 预测
# --------------------------------------------------------------------------- #


def test_industries_list_contract(seeded_client: TestClient, openapi_doc: dict[str, Any]):
    schema = _get_response_schema(openapi_doc, "/api/v1/industries", "get", "200")
    assert schema is not None
    response = seeded_client.get("/api/v1/industries")
    assert response.status_code == 200
    _validate_json(response.json(), schema, openapi_doc)


def test_regions_list_contract(seeded_client: TestClient, openapi_doc: dict[str, Any]):
    schema = _get_response_schema(openapi_doc, "/api/v1/regions", "get", "200")
    assert schema is not None
    response = seeded_client.get("/api/v1/regions")
    assert response.status_code == 200
    _validate_json(response.json(), schema, openapi_doc)


def test_forecast_indicator_contract(seeded_client: TestClient, openapi_doc: dict[str, Any]):
    schema = _get_response_schema(openapi_doc, "/api/v1/forecast/indicator/{city_name}", "get", "200")
    assert schema is not None
    response = seeded_client.get("/api/v1/forecast/indicator/深圳?indicator=gdp&forecast_years=3")
    assert response.status_code == 200
    _validate_json(response.json(), schema, openapi_doc)


def test_forecast_compare_contract(seeded_client: TestClient, openapi_doc: dict[str, Any]):
    schema = _get_response_schema(openapi_doc, "/api/v1/forecast/compare", "post", "200")
    assert schema is not None
    payload = {"city_names": ["深圳", "上海"], "indicator": "gdp", "forecast_years": 3}
    response = seeded_client.post("/api/v1/forecast/compare", json=payload)
    assert response.status_code == 200
    _validate_json(response.json(), schema, openapi_doc)


# --------------------------------------------------------------------------- #
# OpenAPI 文档自身完整性
# --------------------------------------------------------------------------- #


def test_openapi_json_is_valid(openapi_doc: dict[str, Any]):
    assert "openapi" in openapi_doc
    assert openapi_doc["info"]["title"] == "Urban Pulse"
    assert "paths" in openapi_doc and openapi_doc["paths"]


def test_openapi_json_can_be_written_and_reloaded(openapi_doc: dict[str, Any], tmp_path: Path):
    """确保 OpenAPI 文档可被序列化,供前端/外部 SDK 使用。"""
    output = tmp_path / "openapi.json"
    output.write_text(json.dumps(openapi_doc, ensure_ascii=False), encoding="utf-8")
    reloaded = json.loads(output.read_text(encoding="utf-8"))
    assert reloaded["info"]["version"] == openapi_doc["info"]["version"]
