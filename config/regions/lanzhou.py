"""
兰州地区配置
"""

from config.regions.template import RegionConfig


class LanzhouConfig(RegionConfig):
    """兰州配置"""

    name = "兰州"
    code = "620100"
    province = "甘肃省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "城关区", "七里河区", "西固区", "安宁区", "红古区",
            "永登县", "皋兰县", "榆中县",
        ],
        "development_zones": [
            "兰州高新技术产业开发区", "兰州经济技术开发区",
            "兰州新区", "兰州综合保税区",
            "兰州白银国家自主创新示范区",
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
        "甘肃省省会", "西北地区重要中心城市",
        "丝绸之路经济带重要节点城市", "黄河上游经济区中心城市",
    ]

    benchmark_data = {
        "gdp_per_capita": 69000.0,
        "average_wage": 5800.0,
        "industrial_efficiency": 0.66,
        "land_price": 1200.0,
        "energy_cost": 0.48,
    }

    data_sources = [
        "nbs", "gansu_statistics_bureau",
        "lanzhou_statistics_bureau", "industry_association",
    ]
