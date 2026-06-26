"""
响应压缩中间件测试
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_gzip_compresses_json_response(client: TestClient):
    """JSON 响应在 Accept-Encoding: gzip 时应被压缩。"""
    response = client.get("/api/v1/cities/list", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers.get("content-encoding") == "gzip"
    assert response.headers.get("vary") == "accept-encoding"
    # httpx TestClient 会自动解压,response.content 已是原始 JSON
    assert b"cities" in response.content


def test_no_compression_without_accept_encoding(client: TestClient):
    """客户端未声明支持压缩时不应返回压缩内容。"""
    response = client.get("/")
    assert response.status_code == 200
    assert "content-encoding" not in response.headers
    assert b"Urban Pulse" in response.content


def test_small_response_not_compressed(client: TestClient):
    """极小的响应不应被压缩,避免越压越大。"""
    response = client.get("/health", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    # /health 响应很小,不应触发压缩
    assert response.headers.get("content-encoding") != "gzip"


def test_static_js_compressed(client: TestClient):
    """JS 静态资源应支持 gzip 压缩。"""
    response = client.get("/js/viz-engine.js", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers.get("content-encoding") == "gzip"
