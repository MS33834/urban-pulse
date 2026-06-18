"""
区域管理模块

提供多层级、可扩展的区域（国家/省/市/区县）注册与数据访问能力。
"""

from backend.regions.loader import RegionLoader, load_default_regions
from backend.regions.models import Region, RegionLevel
from backend.regions.registry import RegionRegistry, get_registry

__all__ = [
    "Region",
    "RegionLevel",
    "RegionRegistry",
    "RegionLoader",
    "get_registry",
    "load_default_regions",
]
