"""
广州地区配置
"""

from config.regions.template import RegionConfig


class GuangzhouConfig(RegionConfig):
    """广州配置"""

    name = "广州"
    code = "440100"
    province = "广东省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "越秀区", "海珠区", "荔湾区", "天河区", "白云区",
            "黄埔区", "番禺区", "花都区", "南沙区", "从化区",
            "增城区",
        ],
        "development_zones": [
            "广州开发区", "南沙自贸区", "中新广州知识城",
            "琶洲人工智能与数字经济试验区", "广州科学城",
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
        "国家中心城市", "国际商贸中心", "综合交通枢纽",
        "先进制造业基地", "科技创新枢纽",
    ]

    benchmark_data = {
        "gdp_per_capita": 165000.0,
        "average_wage": 11800.0,
        "industrial_efficiency": 0.82,
        "land_price": 4800.0,
        "energy_cost": 0.75,
    }

    data_sources = [
        "nbs", "guangdong_statistics_bureau",
        "guangzhou_statistics_bureau", "industry_association",
    ]
