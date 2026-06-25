"""
长沙地区配置
"""

from config.regions.template import RegionConfig


class ChangshaConfig(RegionConfig):
    """长沙配置"""

    name = "长沙"
    code = "430100"
    province = "湖南省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "芙蓉区", "天心区", "岳麓区", "开福区", "雨花区",
            "望城区", "长沙县", "浏阳市", "宁乡市",
        ],
        "development_zones": [
            "长沙高新技术产业开发区", "长沙经济技术开发区",
            "宁乡经济技术开发区", "浏阳经济技术开发区",
            "湖南湘江新区",
        ],
    }

    indicator_weights = {
        "gdp": 0.25,
        "fiscal_revenue": 0.2,
        "industrial_output": 0.22,
        "employment": 0.13,
        "innovation": 0.2,
    }

    economic_characteristics = [
        "长江中游地区重要中心城市", "文化产业基地",
        "工程机械之都", "传媒娱乐中心",
    ]

    benchmark_data = {
        "gdp_per_capita": 137500.0,
        "average_wage": 9000.0,
        "industrial_efficiency": 0.78,
        "land_price": 2600.0,
        "energy_cost": 0.63,
    }

    data_sources = [
        "nbs", "hunan_statistics_bureau",
        "changsha_statistics_bureau", "industry_association",
    ]
