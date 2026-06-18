"""区域注册表：统一管理所有区域及其数据"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from backend.regions.models import Region, RegionLevel

logger = logging.getLogger(__name__)


class RegionRegistry:
    """
    区域注册表

    - 维护 country / province / city / district 四级区域
    - 支持从 YAML/JSON/数据库/外部 API 动态加载
    - 提供按层级、地理大区、父区域等维度的查询
    """

    def __init__(self) -> None:
        self._regions: dict[str, Region] = {}
        self._custom_loaders: list[Callable[[RegionRegistry], int]] = []

    # ── 注册与注销 ──
    def register(self, region: Region) -> bool:
        """注册一个区域"""
        if region.code in self._regions:
            logger.warning(f"区域已存在: {region.code}")
            return False
        self._regions[region.code] = region
        logger.debug(f"区域注册成功: {region.name} ({region.code})")
        return True

    def register_many(self, regions: list[Region]) -> int:
        """批量注册，返回成功数量"""
        return sum(1 for r in regions if self.register(r))

    def unregister(self, code: str) -> bool:
        """注销区域"""
        if code not in self._regions:
            return False
        del self._regions[code]
        return True

    # ── 查询 ──
    def get(self, code: str) -> Region | None:
        """按编码获取区域"""
        return self._regions.get(code)

    def get_by_name(self, name: str, level: RegionLevel | None = None) -> Region | None:
        """按名称获取区域，可选层级"""
        for region in self._regions.values():
            if region.name == name and (level is None or region.level == level):
                return region
        return None

    def list_all(self, level: RegionLevel | None = None) -> list[Region]:
        """列出所有区域，可按层级过滤"""
        regions = list(self._regions.values())
        if level:
            regions = [r for r in regions if r.level == level]
        return sorted(regions, key=lambda r: (r.level.value, r.code))

    def list_by_region(self, region_name: str) -> list[Region]:
        """按地理大区列出区域，如华东、华南"""
        return sorted(
            [r for r in self._regions.values() if r.region == region_name],
            key=lambda r: r.code,
        )

    def list_by_parent(self, parent_code: str) -> list[Region]:
        """列出某父区域下的所有子区域"""
        return sorted(
            [r for r in self._regions.values() if r.parent_code == parent_code],
            key=lambda r: r.code,
        )

    def list_provinces(self) -> list[Region]:
        """列出所有省份/直辖市"""
        return self.list_all(RegionLevel.PROVINCE)

    def list_cities(self, province_code: str | None = None) -> list[Region]:
        """列出所有城市，可按省份过滤"""
        cities = self.list_all(RegionLevel.CITY)
        if province_code:
            cities = [c for c in cities if c.province_code == province_code]
        return cities

    def list_forecastable(self, indicator: str = "gdp") -> list[Region]:
        """列出可用于预测的区域（有足够时序数据且含指定指标）"""
        return sorted(
            [r for r in self._regions.values() if r.has_time_series and r.get_time_series(indicator)],
            key=lambda r: r.code,
        )

    # ── 聚合与统计 ──
    def region_summary(self) -> dict[str, Any]:
        """区域覆盖统计"""
        counts = {level: 0 for level in RegionLevel}
        for r in self._regions.values():
            counts[r.level] += 1
        return {
            "total": len(self._regions),
            "by_level": {level.value: count for level, count in counts.items()},
            "forecastable": len(self.list_forecastable()),
            "regions": sorted(set(r.region for r in self._regions.values() if r.region)),
        }

    # ── 自定义加载器 ──
    def add_loader(self, loader: Callable[[RegionRegistry], int]) -> None:
        """添加自定义数据加载器"""
        self._custom_loaders.append(loader)

    def load_all(self) -> int:
        """执行所有自定义加载器，返回新增区域总数"""
        total = 0
        for loader in self._custom_loaders:
            try:
                total += loader(self)
            except Exception:
                logger.exception(f"自定义加载器失败: {loader}")
        return total

    def load_from_yaml(self, path: Path | str) -> int:
        """从 YAML 文件加载区域"""
        from backend.regions.loader import RegionLoader

        loader = RegionLoader(Path(path))
        return loader.load_into(self)


# 全局单例
_registry: RegionRegistry | None = None


def get_registry() -> RegionRegistry:
    """获取全局区域注册表（延迟初始化）"""
    global _registry
    if _registry is None:
        from backend.regions.loader import load_default_regions

        _registry = load_default_regions()
    return _registry
