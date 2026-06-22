"""
示例外部采集器插件。

该插件位于独立的 pip 包 urban-pulse-demo 中，
通过 pyproject.toml 的 [project.entry-points."urban_pulse.collectors"]
注册到 Urban Pulse 插件系统。
"""

from __future__ import annotations

from typing import Any

from backend.data_collection.base_collector import DataCollector


class DemoCollector(DataCollector):
    """演示用外部采集器。"""

    def metadata(self) -> dict[str, Any]:
        return {
            "description": "Urban Pulse 外部插件包示例，返回固定演示数据。",
            "version": "0.1.0",
            "author": "Urban Pulse Team",
            "tags": ["demo", "external"],
            "parameters": [],
            "example": {"city": "demo_city"},
        }

    def __init__(self):
        super().__init__()
        self.source_name = "demo"

    def name(self) -> str:
        return "demo_collector"

    def supported_cities(self) -> list[str]:
        return ["demo_city"]

    def fetch_data(self, **kwargs) -> list[dict[str, Any]]:
        return [{"city": "demo_city", "indicator": "demo", "value": 42}]

    def fetch_all(self, indicators: list[str] | None = None) -> dict[str, list[dict]]:
        return {"demo": self.fetch_data()}
