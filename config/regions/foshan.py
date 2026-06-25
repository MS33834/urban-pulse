"""
佛山地区配置
"""

from config.regions.template import RegionConfig


class FoshanConfig(RegionConfig):
    """佛山配置"""

    name = "佛山"
    code = "440600"
    province = "广东省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "禅城区", "南海区", "顺德区", "三水区", "高明区",
        ],
        "development_zones": [
            "佛山高新技术产业开发区", "佛山经济技术开发区",
            "顺德高新技术产业开发区", "南海经济开发区",
            "广东金融高新技术服务区",
        ],
    }

    indicator_weights = {
        "gdp": 0.28,
        "fiscal_revenue": 0.18,
        "industrial_output": 0.3,
        "employment": 0.1,
        "innovation": 0.14,
    }

    economic_characteristics = [
        "制造业基地", "民营经济发达", "陶瓷产业之都",
        "家电产业基地", "广佛都市圈核心城市",
    ]

    benchmark_data = {
        "gdp_per_capita": 132000.0,
        "average_wage": 9500.0,
        "industrial_efficiency": 0.83,
        "land_price": 3000.0,
        "energy_cost": 0.66,
    }

    data_sources = [
        "nbs", "guangdong_statistics_bureau",
        "foshan_statistics_bureau", "industry_association",
    ]
