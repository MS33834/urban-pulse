"""
可观测性中间件测试
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.observability import get_request_metrics


@pytest.fixture
def client():
    return TestClient(app)


def test_request_id_generated(client: TestClient):
    """未提供 X-Request-ID 时中间件应自动生成并回写。"""
    response = client.get("/")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 36
    uuid.UUID(request_id)  # 验证是合法 UUID


def test_request_id_propagated(client: TestClient):
    """提供 X-Request-ID 时应原样透传。"""
    provided = "req-123-abc"
    response = client.get("/", headers={"X-Request-ID": provided})
    assert response.headers["X-Request-ID"] == provided


def test_metrics_collected(client: TestClient):
    """请求后指标计数器应增加。"""
    # 先清空内存计数(单进程测试安全)
    from backend.api import observability

    observability._request_counts.clear()
    observability._request_durations.clear()

    response = client.get("/api/v1/cities/list")
    assert response.status_code == 200

    metrics = get_request_metrics()
    counts = metrics["counts"]
    assert any("/api/v1/cities/list" in key and "200" in key for key in counts)
    assert sum(counts.values()) >= 1


def test_health_not_logged_as_metric(client: TestClient):
    """/health 在 skip_paths 中,不应污染指标。"""
    from backend.api import observability

    observability._request_counts.clear()
    observability._request_durations.clear()

    response = client.get("/health")
    assert response.status_code == 200

    metrics = get_request_metrics()
    assert not any("/health" in key for key in metrics["counts"])
