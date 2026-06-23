"""区域数据加载器：从 YAML/JSON 等配置加载区域"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, cast

import yaml

from backend.regions.models import Region, RegionLevel
from backend.regions.registry import RegionRegistry

logger = logging.getLogger(__name__)


class RegionLoader:
    """从 YAML/JSON 文件加载区域配置"""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> list[Region]:
        """加载并返回区域列表"""
        if not self.path.exists():
            logger.warning(f"区域配置文件不存在: {self.path}")
            return []

        raw = self._load_raw()
        regions: list[Region] = []
        seen_codes: set[str] = set()

        # 支持多级结构: countries / provinces / cities / districts
        _plural_map = {
            RegionLevel.COUNTRY: "countries",
            RegionLevel.PROVINCE: "provinces",
            RegionLevel.CITY: "cities",
            RegionLevel.DISTRICT: "districts",
        }
        for level in RegionLevel:
            for item in raw.get(_plural_map[level], []):
                if level == RegionLevel.CITY:
                    region = self._parse_city(item)
                else:
                    region = self._parse_region(item, level)
                regions.append(region)
                seen_codes.add(region.code)

        # 兼容旧格式：顶层 cities 列表（跳过已在多级结构中处理的条目）
        for item in raw.get("cities", []):
            if str(item.get("code", "")) not in seen_codes:
                regions.append(self._parse_city(item))

        # 兼容旧格式：嵌套 provinces -> cities
        for province in raw.get("provinces", []):
            province_region = self._parse_province(province)
            if province_region.code not in seen_codes:
                regions.append(province_region)
                seen_codes.add(province_region.code)
            for city in province.get("cities", []):
                city_code = str(city.get("code", ""))
                if city_code in seen_codes:
                    continue
                city["parent_code"] = province_region.code
                city["province_code"] = province_region.code
                parsed_city = self._parse_city(city)
                regions.append(parsed_city)
                seen_codes.add(parsed_city.code)

        return regions

    def load_into(self, registry: RegionRegistry) -> int:
        """加载到注册表，返回成功注册数量"""
        return registry.register_many(self.load())

    def _load_raw(self) -> dict[str, Any]:
        suffix = self.path.suffix.lower()
        with self.path.open(encoding="utf-8") as f:
            if suffix in (".yaml", ".yml"):
                return yaml.safe_load(f) or {}
            if suffix == ".json":
                import json

                return cast(dict[str, Any], json.load(f))
            raise ValueError(f"不支持的区域配置文件格式: {suffix}")

    def _parse_region(self, item: dict[str, Any], level: RegionLevel) -> Region:
        """通用区域解析"""
        return Region(
            code=str(item["code"]),
            name=str(item["name"]),
            level=level,
            parent_code=item.get("parent_code"),
            region=item.get("region"),
            country=item.get("country", "中国"),
            indicators=item.get("indicators", {}),
            historical_data=item.get("historical_data", []),
            metadata=item.get("metadata", {}),
        )

    def _parse_city(self, item: dict[str, Any]) -> Region:
        """解析城市条目（兼容 data/cities/cities.yaml 格式）"""
        name = str(item["name"])
        code = str(item.get("code", self._name_to_code(name)))
        historical = item.get("historical_data", [])

        # 如果没有显式历史数据，但 indicators 里包含多个年份，可以扩展
        if not historical and "year" in item:
            historical = [
                {
                    "year": item["year"],
                    **{k: v for k, v in item.items() if k not in ("name", "code", "province", "region", "year")},
                }
            ]

        indicators = dict(item)
        for key in ("name", "code", "province", "region", "historical_data", "metadata", "parent_code", "country"):
            indicators.pop(key, None)

        return Region(
            code=code,
            name=name,
            level=RegionLevel.CITY,
            parent_code=item.get("parent_code") or item.get("province_code"),
            region=item.get("region"),
            country=item.get("country", "中国"),
            indicators=indicators,
            historical_data=historical,
            metadata=item.get("metadata", {}),
        )

    def _parse_province(self, item: dict[str, Any]) -> Region:
        """解析省份条目"""
        return Region(
            code=str(item["code"]),
            name=str(item["name"]),
            level=RegionLevel.PROVINCE,
            region=item.get("region"),
            country=item.get("country", "中国"),
            indicators=item.get("indicators", {}),
            historical_data=item.get("historical_data", []),
            metadata=item.get("metadata", {}),
        )

    @staticmethod
    def _name_to_code(name: str) -> str:
        """简单的城市名称到拼音代码映射（fallback）"""
        mapping = {
            "深圳": "shenzhen",
            "上海": "shanghai",
            "北京": "beijing",
            "广州": "guangzhou",
            "杭州": "hangzhou",
            "成都": "chengdu",
            "武汉": "wuhan",
            "南京": "nanjing",
            "苏州": "suzhou",
            "西安": "xian",
            "重庆": "chongqing",
            "天津": "tianjin",
            "青岛": "qingdao",
            "宁波": "ningbo",
            "无锡": "wuxi",
            "长沙": "changsha",
            "郑州": "zhengzhou",
            "佛山": "foshan",
            "济南": "jinan",
            "合肥": "hefei",
            "福州": "fuzhou",
            "厦门": "xiamen",
            "东莞": "dongguan",
            "昆明": "kunming",
            "沈阳": "shenyang",
            "大连": "dalian",
            "哈尔滨": "haerbin",
            "长春": "changchun",
            "石家庄": "shijiazhuang",
            "太原": "taiyuan",
            "南昌": "nanchang",
            "贵阳": "guiyang",
            "南宁": "nanning",
            "乌鲁木齐": "wulumuqi",
            "兰州": "lanzhou",
            "银川": "yinchuan",
            "西宁": "xining",
            "拉萨": "lasa",
            "海口": "haikou",
        }
        return mapping.get(name, name)


def load_default_regions() -> RegionRegistry:
    """加载默认区域注册表（data/cities/cities.yaml + 中国省份）"""
    registry = RegionRegistry()

    # 加载城市数据
    city_yaml = Path(__file__).parents[2] / "data" / "cities" / "cities.yaml"
    if city_yaml.exists():
        registry.load_from_yaml(city_yaml)

    # 加载中国省份骨架（后续可补充指标）
    _load_china_provinces(registry)

    # 加载国家层
    registry.register(
        Region(
            code="CN",
            name="中国",
            level=RegionLevel.COUNTRY,
            indicators={"country_code": "CN"},
            metadata={"data_source": "国家统计局"},
        )
    )

    return registry


def _load_china_provinces(registry: RegionRegistry) -> None:
    """注册中国省级行政单位骨架"""
    provinces = [
        ("CN-BJ", "北京", "华北"),
        ("CN-TJ", "天津", "华北"),
        ("CN-HE", "河北", "华北"),
        ("CN-SX", "山西", "华北"),
        ("CN-NM", "内蒙古", "华北"),
        ("CN-LN", "辽宁", "东北"),
        ("CN-JL", "吉林", "东北"),
        ("CN-HL", "黑龙江", "东北"),
        ("CN-SH", "上海", "华东"),
        ("CN-JS", "江苏", "华东"),
        ("CN-ZJ", "浙江", "华东"),
        ("CN-AH", "安徽", "华东"),
        ("CN-FJ", "福建", "华东"),
        ("CN-JX", "江西", "华东"),
        ("CN-SD", "山东", "华东"),
        ("CN-HA", "河南", "华中"),
        ("CN-HB", "湖北", "华中"),
        ("CN-HN", "湖南", "华中"),
        ("CN-GD", "广东", "华南"),
        ("CN-GX", "广西", "华南"),
        ("CN-HI", "海南", "华南"),
        ("CN-CQ", "重庆", "西南"),
        ("CN-SC", "四川", "西南"),
        ("CN-GZ", "贵州", "西南"),
        ("CN-YN", "云南", "西南"),
        ("CN-XZ", "西藏", "西南"),
        ("CN-SN", "陕西", "西北"),
        ("CN-GS", "甘肃", "西北"),
        ("CN-QH", "青海", "西北"),
        ("CN-NX", "宁夏", "西北"),
        ("CN-XJ", "新疆", "西北"),
        ("CN-TW", "台湾", "华东"),
        ("CN-HK", "香港", "华南"),
        ("CN-MO", "澳门", "华南"),
    ]
    for code, name, region in provinces:
        registry.register(
            Region(
                code=code,
                name=name,
                level=RegionLevel.PROVINCE,
                parent_code="CN",
                region=region,
                metadata={"data_source": "国家统计局行政区划"},
            )
        )
