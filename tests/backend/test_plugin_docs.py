"""
插件文档生成器测试（Phase 4）
"""

from __future__ import annotations

from backend.core.plugin_docs import PluginDocsGenerator, generate_plugin_docs
from backend.core.plugin_registry import PluginRegistry


class TestPluginDocsGenerator:
    def setup_method(self):
        PluginRegistry.clear()

    def teardown_method(self):
        PluginRegistry.clear()

    def test_collect_includes_builtin_plugins(self):
        PluginRegistry.discover_all()
        generator = PluginDocsGenerator()
        docs = generator.generate()
        names = {d["name"] for d in docs}
        assert "housing_affordability" in names
        assert "linear_trend" in names
        assert "html_table" in names

    def test_external_demo_plugin_has_metadata(self):
        PluginRegistry.discover_all()
        generator = PluginDocsGenerator()
        docs = generator.generate()
        demo = next((d for d in docs if d["name"] == "demo_collector"), None)
        assert demo is not None
        assert demo["type"] == "Collector"
        assert "Urban Pulse 外部插件包示例" in demo["description"]

    def test_world_bank_collector_metadata(self):
        PluginRegistry.discover_all()
        generator = PluginDocsGenerator()
        docs = generator.generate()
        wb = next((d for d in docs if d["name"] == "world_bank"), None)
        assert wb is not None
        assert wb["type"] == "Collector"
        assert "世界银行" in wb["description"]
        assert any(p["name"] == "city" for p in wb["parameters"])

    def test_to_markdown_contains_headers(self):
        PluginRegistry.discover_all()
        generator = PluginDocsGenerator()
        md = generator.to_markdown()
        assert "# Urban Pulse 插件 API 文档" in md
        assert "## Collector Plugins" in md
        assert "`housing_affordability`" in md

    def test_to_json_is_valid(self):
        PluginRegistry.discover_all()
        generator = PluginDocsGenerator()
        json_str = generator.to_json()
        assert '"name"' in json_str
        assert '"type"' in json_str

    def test_generate_plugin_docs_helper(self):
        PluginRegistry.discover_all()
        docs = generate_plugin_docs()
        assert isinstance(docs, list)
        assert len(docs) > 0
        assert all("name" in d and "type" in d for d in docs)
