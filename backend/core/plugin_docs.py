"""
插件文档生成器（Phase 4 — Auto-generated API docs per plugin）

自动收集 Urban Pulse 所有已注册插件的元数据，并导出为结构化字典、
Markdown 或 JSON，方便开发者浏览与集成。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from backend.core.plugin_registry import PluginRegistry

logger = logging.getLogger(__name__)


class PluginMetadataMixin:
    """
    插件元数据 Mixin。

    插件可选择继承此类（或自行实现 metadata() 方法）来提供结构化文档信息。
    未覆盖 metadata() 时，文档生成器会从 docstring 与已有方法中推断基础信息。
    """

    def metadata(self) -> dict[str, Any]:
        """
        返回插件元数据。

        推荐字段：
            - description: 插件功能描述
            - version: 版本号
            - author: 作者/组织
            - tags: 标签列表
            - parameters: 参数说明列表，每项为 {name, type, required, default, description}
            - example: 调用示例（dict 或 str）
        """
        return {
            "description": (self.__doc__ or "").strip(),
            "version": "0.1.0",
            "author": "community",
            "tags": [],
            "parameters": [],
            "example": None,
        }


@dataclass
class PluginInfo:
    """单个插件的文档信息。"""

    name: str
    plugin_type: str
    description: str = ""
    version: str = "0.1.0"
    author: str = "community"
    tags: list[str] = field(default_factory=list)
    parameters: list[dict[str, Any]] = field(default_factory=list)
    required_inputs: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
    example: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.plugin_type,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "parameters": self.parameters,
            "required_inputs": self.required_inputs,
            "extra": self.extra,
            "example": self.example,
        }


class PluginDocsGenerator:
    """插件文档生成器。"""

    PLUGIN_TYPE_LABELS = {
        "collector": "Collector",
        "analyzer": "Analyzer",
        "forecaster": "Forecaster",
        "visualizer": "Visualizer",
    }

    def __init__(self, registry: PluginRegistry | None = None) -> None:
        self.registry = registry or PluginRegistry

    def collect(self) -> list[PluginInfo]:
        """收集所有已注册插件的文档信息。"""
        infos: list[PluginInfo] = []
        infos.extend(self._collect_type("collector", self.registry.list_collectors, self.registry.get_collector))
        infos.extend(self._collect_type("analyzer", self.registry.list_analyzers, self.registry.get_analyzer))
        infos.extend(self._collect_type("forecaster", self.registry.list_forecasters, self.registry.get_forecaster))
        infos.extend(self._collect_type("visualizer", self.registry.list_visualizers, self.registry.get_visualizer))
        return sorted(infos, key=lambda p: (p.plugin_type, p.name))

    def _collect_type(
        self,
        plugin_type: str,
        list_fn: callable,
        get_fn: callable,
    ) -> list[PluginInfo]:
        infos: list[PluginInfo] = []
        for name in list_fn():
            plugin = get_fn(name)
            if plugin is None:
                continue
            infos.append(self._build_info(plugin, plugin_type))
        return infos

    def _build_info(self, plugin: Any, plugin_type: str) -> PluginInfo:
        meta: dict[str, Any] = {}
        if hasattr(plugin, "metadata") and callable(plugin.metadata):
            try:
                meta = plugin.metadata() or {}
            except Exception as exc:
                logger.warning(f"获取插件 {plugin.name()} metadata 失败: {exc}")

        description = meta.get("description") or (plugin.__doc__ or "").strip()
        info = PluginInfo(
            name=plugin.name(),
            plugin_type=self.PLUGIN_TYPE_LABELS.get(plugin_type, plugin_type),
            description=description,
            version=str(meta.get("version", "0.1.0")),
            author=str(meta.get("author", "community")),
            tags=list(meta.get("tags", [])),
            parameters=list(meta.get("parameters", [])),
            example=meta.get("example"),
        )
        info.required_inputs = self._extract_required_inputs(plugin, plugin_type)
        info.extra = self._extract_extra(plugin, plugin_type)
        return info

    def _extract_required_inputs(self, plugin: Any, plugin_type: str) -> list[str]:
        if plugin_type == "collector" and hasattr(plugin, "supported_cities"):
            try:
                cities = plugin.supported_cities()
                if isinstance(cities, list):
                    return cities[:10]
            except Exception:
                pass
        if plugin_type == "analyzer" and hasattr(plugin, "required_indicators"):
            try:
                return plugin.required_indicators()
            except Exception:
                pass
        if plugin_type == "forecaster" and hasattr(plugin, "min_data_points"):
            try:
                return [f"min_data_points:{plugin.min_data_points()}"]
            except Exception:
                pass
        if plugin_type == "visualizer" and hasattr(plugin, "supported_data_types"):
            try:
                return plugin.supported_data_types()
            except Exception:
                pass
        return []

    def _extract_extra(self, plugin: Any, plugin_type: str) -> dict[str, Any]:
        extra: dict[str, Any] = {}
        if plugin_type == "collector" and hasattr(plugin, "source_name"):
            try:
                extra["source_name"] = plugin.source_name() if callable(plugin.source_name) else plugin.source_name
            except Exception:
                pass
        return extra

    def generate(self) -> list[dict[str, Any]]:
        """生成结构化文档列表。"""
        return [info.to_dict() for info in self.collect()]

    def to_json(self, indent: int = 2) -> str:
        """导出为 JSON 字符串。"""
        return json.dumps(self.generate(), indent=indent, ensure_ascii=False, default=str)

    def to_markdown(self) -> str:
        """导出为 Markdown 字符串。"""
        lines: list[str] = ["# Urban Pulse 插件 API 文档\n"]
        current_type: str | None = None
        for info in self.collect():
            if info.plugin_type != current_type:
                current_type = info.plugin_type
                lines.append(f"## {current_type} Plugins\n")
            lines.append(f"### `{info.name}`\n")
            lines.append(f"**版本**: {info.version} | **作者**: {info.author}\n")
            if info.description:
                lines.append(f"{info.description}\n")
            if info.tags:
                lines.append(f"**标签**: {', '.join(info.tags)}\n")
            if info.required_inputs:
                lines.append(f"**所需输入**: {', '.join(str(x) for x in info.required_inputs)}\n")
            if info.parameters:
                lines.append("**参数**:\n")
                lines.append("| 名称 | 类型 | 必填 | 默认值 | 说明 |")
                lines.append("|------|------|------|--------|------|")
                for param in info.parameters:
                    lines.append(
                        f"| {param.get('name', '')} | {param.get('type', '')} | "
                        f"{param.get('required', '')} | {param.get('default', '')} | {param.get('description', '')} |"
                    )
                lines.append("")
            if info.example:
                lines.append("**示例**:\n")
                lines.append(f"```json\n{json.dumps(info.example, ensure_ascii=False, indent=2, default=str)}\n```\n")
            lines.append("---\n")
        return "\n".join(lines)


def generate_plugin_docs(format: str = "dict") -> Any:
    """
    一键生成插件文档。

    Args:
        format: "dict" | "json" | "markdown"

    Returns:
        对应格式的文档内容
    """
    generator = PluginDocsGenerator()
    generator.registry.discover_all()
    if format == "json":
        return generator.to_json()
    if format == "markdown":
        return generator.to_markdown()
    return generator.generate()
