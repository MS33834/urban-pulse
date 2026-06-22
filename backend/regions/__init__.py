"""
全球城市与区域管理模块
"""

from backend.regions.city_registry import (
    GlobalCityRegistry,
    get_global_city_registry,
    load_default_global_cities,
)
from backend.regions.models import Region, RegionLevel
from backend.regions.registry import RegionRegistry, get_registry

__all__ = [
    "Region",
    "RegionLevel",
    "RegionRegistry",
    "get_registry",
    "GlobalCityRegistry",
    "get_global_city_registry",
    "load_default_global_cities",
]
