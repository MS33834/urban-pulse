"""
安全响应头中间件测试
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def client_production(monkeypatch):
    """模拟生产环境 + HTTPS 请求的 TestClient"""
    monkeypatch.setenv("APP_ENV", "production")
    # base_url=https 会让 ASGI scheme=https,SecurityHeadersMiddleware 据此启用 HSTS
    yield TestClient(app, base_url="https://testserver")


def test_basic_security_headers(client: TestClient):
    """所有响应都应携带基础安全头。"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"
    assert response.headers["X-DNS-Prefetch-Control"] == "off"
    assert response.headers["Origin-Agent-Cluster"] == "?1"


def test_csp_header(client: TestClient):
    """默认返回 Content-Security-Policy。"""
    response = client.get("/")
    assert "Content-Security-Policy" in response.headers
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]


def test_write_method_cache_control_no_store(client: TestClient):
    """写操作响应默认禁止缓存。"""
    response = client.post("/api/v1/health/calculate", json={"city_name": "深圳", "year": 2024})
    assert response.headers.get("Cache-Control") == "no-store"


def test_hsts_in_production_https(client_production: TestClient):
    """生产环境 + HTTPS 请求应返回 HSTS。"""
    response = client_production.get("/")
    assert response.status_code == 200
    hsts = response.headers.get("Strict-Transport-Security")
    assert hsts is not None
    assert "max-age=31536000" in hsts
    assert "includeSubDomains" in hsts


def test_hsts_not_in_dev_http(client: TestClient):
    """开发环境 HTTP 请求不应返回 HSTS。"""
    response = client.get("/")
    assert "Strict-Transport-Security" not in response.headers
