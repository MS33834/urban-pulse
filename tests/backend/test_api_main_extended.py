"""补充 backend.api.main 中未覆盖函数的测试。"""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from backend.api.main import (
    _seed_city_manager,
    app,
    run,
)
from backend.regions import Region, RegionLevel, RegionRegistry


class TestDashboard:
    def test_dashboard_without_frontend(self, monkeypatch):
        """当前端 index.html 不存在时返回 JSON 提示。"""
        monkeypatch.setattr("backend.api.main.frontend_index", MagicMock(exists=lambda: False))
        client = TestClient(app)
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        body = resp.json()
        assert body["error"] == "frontend not built"


class TestFavicon:
    def test_favicon_fallback_svg(self, monkeypatch):
        """当 favicon.ico 不存在时返回内置 SVG。"""
        monkeypatch.setattr("backend.api.main.FAVICON_PATH", MagicMock(exists=lambda: False))
        client = TestClient(app)
        resp = client.get("/favicon.ico")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/svg+xml"
        assert b"<svg" in resp.content


class TestSeedCityManager:
    def test_seed_city_manager_with_regions(self, monkeypatch):
        from backend.core.multi_city import city_manager

        registry = RegionRegistry()
        registry.register(
            Region(
                code="CN-TEST-T1",
                name="测试城",
                level=RegionLevel.CITY,
                parent_code="CN-TEST",
                region="华东",
                indicators={
                    "year": 2024,
                    "population": 1000,
                    "gdp_rank": 5,
                    "gdp": 5000,
                },
                historical_data=[{"year": 2022, "gdp": 4000}, {"year": 2023, "gdp": 4500}],
                metadata={"latitude": 30.0, "longitude": 120.0, "data_source": "test"},
            )
        )
        # 清理本次可能残留的城市
        city_manager.unregister_city("CN-TEST-T1")

        monkeypatch.setattr("backend.regions.get_registry", lambda: registry)
        _seed_city_manager()

        assert "CN-TEST-T1" in city_manager.cities
        config = city_manager.cities["CN-TEST-T1"]
        assert config.name == "测试城"
        assert config.latitude == 30.0
        assert config.metadata["parent_code"] == "CN-TEST"

        # 快照 + 历史时序都已加入
        assert 2024 in city_manager.city_data["CN-TEST-T1"]
        assert 2022 in city_manager.city_data["CN-TEST-T1"]
        assert 2023 in city_manager.city_data["CN-TEST-T1"]

    def test_seed_city_manager_no_registry(self, monkeypatch, caplog):
        monkeypatch.setattr("backend.regions.get_registry", lambda: None)
        _seed_city_manager()
        assert "Region registry not available" in caplog.text

    def test_seed_city_manager_skips_yearless_historical(self, monkeypatch):
        from backend.core.multi_city import city_manager

        registry = RegionRegistry()
        registry.register(
            Region(
                code="CN-TEST-T2",
                name="测试城二",
                level=RegionLevel.CITY,
                indicators={"year": 2024, "population": 100},
                historical_data=[{"gdp": 100}],  # 缺少 year，应被跳过
            )
        )
        city_manager.unregister_city("CN-TEST-T2")

        monkeypatch.setattr("backend.regions.get_registry", lambda: registry)
        _seed_city_manager()

        assert "CN-TEST-T2" in city_manager.cities
        # 当前年份快照仍会被加入，缺少 year 的历史记录被跳过
        assert 2024 in city_manager.city_data["CN-TEST-T2"]


class TestRunFunction:
    def test_run_entry_point(self, monkeypatch):
        captured = {}

        def fake_uvicorn_run(app_name, host, port, workers, reload):
            captured.update({"app": app_name, "host": host, "port": port, "workers": workers, "reload": reload})

        monkeypatch.setattr("uvicorn.run", fake_uvicorn_run)
        monkeypatch.setenv("APP_HOST", "0.0.0.0")
        monkeypatch.setenv("APP_PORT", "8080")
        monkeypatch.setenv("WORKERS", "2")
        monkeypatch.setenv("APP_RELOAD", "true")

        run()

        assert captured["app"] == "backend.api.main:app"
        assert captured["host"] == "0.0.0.0"
        assert captured["port"] == 8080
        assert captured["workers"] == 1  # reload=True 时 workers 强制为 1
        assert captured["reload"] is True
