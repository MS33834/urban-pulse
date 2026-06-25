"""
乌鲁木齐地区配置
"""

from config.regions.template import RegionConfig


class UrumqiConfig(RegionConfig):
    """乌鲁木齐配置"""

    name = "乌鲁木齐"
    code = "650100"
    province = "新疆维吾尔自治区"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "天山区", "沙依巴克区", "新市区", "水磨沟区",
            "头屯河区", "达坂城区", "米东区",
            "乌鲁木齐县",
        ],
        "development_zones": [
            "乌鲁木齐高新技术产业开发区", "乌鲁木齐经济技术开发区",
            "乌鲁木齐综合保税区", "甘泉堡经济技术开发区",
            "新疆国际陆港区",
        ],
    }

    indicator_weights = {
        "gdp": 0.25,
        "fiscal_revenue": 0.2,
        "industrial_output": 0.2,
        "employment": 0.15,
        "innovation": 0.2,
    }

    economic_characteristics = [
        "新疆维吾尔自治区首府", "西北地区重要中心城市",
        "丝绸之路经济带核心区节点城市", "向西开放的门户城市",
    ]

    benchmark_data = {
        "gdp_per_capita": 79500.0,
        "average_wage": 6000.0,
        "industrial_efficiency": 0.66,
        "land_price": 1300.0,
        "energy_cost": 0.42,
    }

    data_sources = [
        "nbs", "xinjiang_statistics_bureau",
        "urumqi_statistics_bureau", "industry_association",
    ]
