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
import threading
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any, Protocol, TypeVar, cast

T = TypeVar("T")


class _NamedPlugin(Protocol):
    """拥有 name() 方法的插件协议，用于类型检查。"""

    def name(self) -> str: ...


logger = logging.getLogger(__name__)

# 全局锁,保护类级注册字典的并发读写(多 worker / 多线程发现插件时)。
_REGISTRY_LOCK = threading.RLock()


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
        with _REGISTRY_LOCK:
            cls._collectors[name] = plugin
        logger.debug(f"注册采集器插件: {name}")

    @classmethod
    def get_collector(cls, name: str) -> Any | None:
        with _REGISTRY_LOCK:
            return cls._collectors.get(name)

    @classmethod
    def list_collectors(cls) -> list[str]:
        with _REGISTRY_LOCK:
            return list(cls._collectors.keys())

    # ------------------------------------------------------------------
    # Analyzer
    # ------------------------------------------------------------------
    @classmethod
    def register_analyzer(cls, plugin: Any, name: str | None = None) -> None:
        name = name or plugin.name()
        with _REGISTRY_LOCK:
            cls._analyzers[name] = plugin
        logger.debug(f"注册分析器插件: {name}")

    @classmethod
    def get_analyzer(cls, name: str) -> Any | None:
        with _REGISTRY_LOCK:
            return cls._analyzers.get(name)

    @classmethod
    def list_analyzers(cls) -> list[str]:
        with _REGISTRY_LOCK:
            return list(cls._analyzers.keys())

    # ------------------------------------------------------------------
    # Forecaster
    # ------------------------------------------------------------------
    @classmethod
    def register_forecaster(cls, plugin: Any, name: str | None = None) -> None:
        name = name or plugin.name()
        with _REGISTRY_LOCK:
            cls._forecasters[name] = plugin
        logger.debug(f"注册预测器插件: {name}")

    @classmethod
    def get_forecaster(cls, name: str) -> Any | None:
        with _REGISTRY_LOCK:
            return cls._forecasters.get(name)

    @classmethod
    def list_forecasters(cls) -> list[str]:
        with _REGISTRY_LOCK:
            return list(cls._forecasters.keys())

    # ------------------------------------------------------------------
    # Visualizer
    # ------------------------------------------------------------------
    @classmethod
    def register_visualizer(cls, plugin: Any, name: str | None = None) -> None:
        name = name or plugin.name()
        with _REGISTRY_LOCK:
            cls._visualizers[name] = plugin
        logger.debug(f"注册可视化器插件: {name}")

    @classmethod
    def get_visualizer(cls, name: str) -> Any | None:
        with _REGISTRY_LOCK:
            return cls._visualizers.get(name)

    @classmethod
    def list_visualizers(cls) -> list[str]:
        with _REGISTRY_LOCK:
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
                # 对每个属性的检查与实例化单独 try/except,
                # 单个插件加载失败不影响其他插件继续发现。
                try:
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
                            with _REGISTRY_LOCK:
                                registry[named.name()] = instance
                            logger.debug(f"自动发现插件 {base_class.__name__}: {named.name()}")
                        except Exception as exc:
                            logger.warning(f"实例化插件 {attr_name} 失败: {exc}")
                except Exception as exc:
                    logger.warning(f"检查插件属性 {attr_name} 失败: {exc}")
                    continue

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

        安全策略:仅加载 settings.ALLOWED_PLUGINS 白名单中声明的插件。
        白名单为空时跳过外部插件发现,避免自动加载任意 pip 包中声明的插件。
        """
        from config.settings import settings

        allowed = settings.ALLOWED_PLUGINS
        if not allowed:
            logger.warning(
                "ALLOWED_PLUGINS 白名单为空,跳过外部插件发现。"
                "如需加载外部插件,请在环境变量 ALLOWED_PLUGINS 中显式声明(逗号分隔)。"
            )
            return

        groups = cls._entry_point_groups()
        try:
            eps = entry_points()
        except Exception as exc:
            logger.warning(f"读取 entry points 失败: {exc}")
            return

        allowed_set = set(allowed)
        for group, (base_class, registry) in groups.items():
            group_eps = eps.select(group=group) if hasattr(eps, "select") else []
            for ep in group_eps:
                if ep.name not in allowed_set:
                    logger.debug(f"外部插件 {ep.name} 不在白名单中,跳过")
                    continue
                try:
                    loaded = ep.load()
                    plugin_cls = cast(type[Any], loaded)
                    if not isinstance(plugin_cls, type) or not issubclass(plugin_cls, base_class):
                        logger.warning(f"Entry point {ep.name} 不是有效的 {base_class.__name__} 子类")
                        continue
                    instance = plugin_cls()
                    named = cast(_NamedPlugin, instance)
                    version = cls._plugin_version(ep)
                    dist_name = cls._plugin_source(ep)
                    with _REGISTRY_LOCK:
                        registry[named.name()] = instance
                    logger.info(
                        f"已加载外部插件: name={named.name()}, entry_point={ep.name}, "
                        f"version={version}, source={dist_name}, group={group}"
                    )
                except Exception as exc:
                    logger.warning(f"加载外部插件 {ep.name} 失败: {exc}")

    @staticmethod
    def _plugin_version(ep: Any) -> str:
        """从 entry point 的 dist 元数据获取插件版本。"""
        try:
            dist = getattr(ep, "dist", None)
            if dist is not None:
                return getattr(dist, "version", "unknown") or "unknown"
        except Exception:
            pass
        return "unknown"

    @staticmethod
    def _plugin_source(ep: Any) -> str:
        """从 entry point 的 dist 元数据获取插件来源(发行包名称)。"""
        try:
            dist = getattr(ep, "dist", None)
            if dist is not None:
                return getattr(dist, "name", None) or "unknown"
        except Exception:
            pass
        return "unknown"

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
        with _REGISTRY_LOCK:
            cls._collectors.clear()
            cls._analyzers.clear()
            cls._forecasters.clear()
            cls._visualizers.clear()
