"""
插件注册表 - 自动发现与管理 Collector / Analyzer / Forecaster / Visualizer 插件。

设计遵循 docs/PLUGIN_ARCHITECTURE.md 的 Phase 1 规划：
- 每类插件有独立的注册字典
- discover() 扫描指定包下所有继承基类的非抽象类并实例化注册
- discover_all() 在应用启动时一次性完成全量发现
"""

from __future__ import annotations

import importlib.util
import logging
import pkgutil
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any, Protocol, TypeVar, cast

T = TypeVar("T")


class _NamedPlugin(Protocol):
    """拥有 name() 方法的插件协议，用于类型检查。"""

    def name(self) -> str: ...


logger = logging.getLogger(__name__)


class PluginRegistry:
    """Urban Pulse 插件注册表。"""

    _collectors: dict[str, Any] = {}
    _analyzers: dict[str, Any] = {}
    _forecasters: dict[str, Any] = {}
    _visualizers: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Collector
    # ------------------------------------------------------------------
    @classmethod
    def register_collector(cls, plugin: Any, name: str | None = None) -> None:
        name = name or plugin.name()
        cls._collectors[name] = plugin
        logger.debug(f"注册采集器插件: {name}")

    @classmethod
    def get_collector(cls, name: str) -> Any | None:
        return cls._collectors.get(name)

    @classmethod
    def list_collectors(cls) -> list[str]:
        return list(cls._collectors.keys())

    # ------------------------------------------------------------------
    # Analyzer
    # ------------------------------------------------------------------
    @classmethod
    def register_analyzer(cls, plugin: Any, name: str | None = None) -> None:
        name = name or plugin.name()
        cls._analyzers[name] = plugin
        logger.debug(f"注册分析器插件: {name}")

    @classmethod
    def get_analyzer(cls, name: str) -> Any | None:
        return cls._analyzers.get(name)

    @classmethod
    def list_analyzers(cls) -> list[str]:
        return list(cls._analyzers.keys())

    # ------------------------------------------------------------------
    # Forecaster
    # ------------------------------------------------------------------
    @classmethod
    def register_forecaster(cls, plugin: Any, name: str | None = None) -> None:
        name = name or plugin.name()
        cls._forecasters[name] = plugin
        logger.debug(f"注册预测器插件: {name}")

    @classmethod
    def get_forecaster(cls, name: str) -> Any | None:
        return cls._forecasters.get(name)

    @classmethod
    def list_forecasters(cls) -> list[str]:
        return list(cls._forecasters.keys())

    # ------------------------------------------------------------------
    # Visualizer
    # ------------------------------------------------------------------
    @classmethod
    def register_visualizer(cls, plugin: Any, name: str | None = None) -> None:
        name = name or plugin.name()
        cls._visualizers[name] = plugin
        logger.debug(f"注册可视化器插件: {name}")

    @classmethod
    def get_visualizer(cls, name: str) -> Any | None:
        return cls._visualizers.get(name)

    @classmethod
    def list_visualizers(cls) -> list[str]:
        return list(cls._visualizers.keys())

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------
    @classmethod
    def discover(cls, package: str, base_class: type[T], registry: dict[str, T]) -> None:
        """
        扫描指定包下所有继承 base_class 的非抽象类，实例化后写入 registry。

        Args:
            package: Python 包名，例如 "backend.data_collection"
            base_class: 插件基类
            registry: 用于存放插件实例的字典
        """
        spec = importlib.util.find_spec(package)
        if spec is None or spec.origin is None:
            logger.warning(f"找不到插件包: {package}")
            return

        package_path = Path(spec.origin).parent
        if not package_path.exists() or not package_path.is_dir():
            logger.warning(f"插件包路径不存在: {package_path}")
            return

        prefix = f"{package}."
        for finder, module_name, ispkg in pkgutil.iter_modules([str(package_path)]):
            full_name = f"{prefix}{module_name}"
            try:
                module = importlib.import_module(full_name)
            except Exception as exc:
                logger.warning(f"导入插件模块失败 {full_name}: {exc}")
                continue

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, base_class)
                    and attr is not base_class
                    and not getattr(attr, "__abstractmethods__", None)
                ):
                    try:
                        instance = attr()
                        named = cast(_NamedPlugin, instance)
                        registry[named.name()] = instance
                        logger.debug(f"自动发现插件 {base_class.__name__}: {named.name()}")
                    except Exception as exc:
                        logger.warning(f"实例化插件 {attr_name} 失败: {exc}")

    # ------------------------------------------------------------------
    # External plugins via entry points
    # ------------------------------------------------------------------
    ENTRY_POINT_GROUPS: dict[str, tuple[type, dict[str, Any]]] = {}

    @classmethod
    def _entry_point_groups(cls) -> dict[str, tuple[type, dict[str, Any]]]:
        """返回 entry point group 到 (base_class, registry) 的映射。"""
        if not cls.ENTRY_POINT_GROUPS:
            from backend.analysis.base_analyzer import AnalysisPlugin
            from backend.core.forecast_base import ForecastingPlugin
            from backend.data_collection.base_collector import DataCollector
            from backend.utils.visualizer_base import VisualizerPlugin

            cls.ENTRY_POINT_GROUPS = {
                "urban_pulse.collectors": (DataCollector, cls._collectors),
                "urban_pulse.analyzers": (AnalysisPlugin, cls._analyzers),
                "urban_pulse.forecasters": (ForecastingPlugin, cls._forecasters),
                "urban_pulse.visualizers": (VisualizerPlugin, cls._visualizers),
            }
        return cls.ENTRY_POINT_GROUPS

    @classmethod
    def discover_external_plugins(cls) -> None:
        """
        通过 importlib.metadata.entry_points 发现外部 pip 包中的插件。

        第三方包在 pyproject.toml 中声明：
            [project.entry-points."urban_pulse.collectors"]
            my_collector = "my_package.module:MyCollectorClass"
        """
        groups = cls._entry_point_groups()
        try:
            eps = entry_points()
        except Exception as exc:
            logger.warning(f"读取 entry points 失败: {exc}")
            return

        for group, (base_class, registry) in groups.items():
            group_eps = eps.select(group=group) if hasattr(eps, "select") else []
            for ep in group_eps:
                try:
                    loaded = ep.load()
                    plugin_cls = cast(type[Any], loaded)
                    if not isinstance(plugin_cls, type) or not issubclass(plugin_cls, base_class):
                        logger.warning(f"Entry point {ep.name} 不是有效的 {base_class.__name__} 子类")
                        continue
                    instance = plugin_cls()
                    named = cast(_NamedPlugin, instance)
                    registry[named.name()] = instance
                    logger.debug(f"通过 entry point 注册插件 {base_class.__name__}: {named.name()}")
                except Exception as exc:
                    logger.warning(f"加载外部插件 {ep.name} 失败: {exc}")

    @classmethod
    def discover_all(cls) -> None:
        """一次性发现所有类型插件（内置 + 外部 pip 包）。"""
        from backend.analysis.base_analyzer import AnalysisPlugin
        from backend.core.forecast_base import ForecastingPlugin
        from backend.data_collection.base_collector import DataCollector
        from backend.utils.visualizer_base import VisualizerPlugin

        cls.discover("backend.data_collection", DataCollector, cls._collectors)
        cls.discover("backend.analysis", AnalysisPlugin, cls._analyzers)
        cls.discover("backend.core", ForecastingPlugin, cls._forecasters)
        cls.discover("backend.utils", VisualizerPlugin, cls._visualizers)
        cls.discover_external_plugins()

    @classmethod
    def clear(cls) -> None:
        """清空注册表，主要用于测试。"""
        cls._collectors.clear()
        cls._analyzers.clear()
        cls._forecasters.clear()
        cls._visualizers.clear()
