"""
苏州地区配置
"""

from config.regions.template import RegionConfig


class SuzhouConfig(RegionConfig):
    """苏州配置"""

    name = "苏州"
    code = "320500"
    province = "江苏省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "姑苏区", "虎丘区", "吴中区", "相城区", "吴江区",
            "常熟市", "张家港市", "昆山市", "太仓市",
        ],
        "development_zones": [
            "苏州工业园区", "苏州高新区", "昆山经济技术开发区",
            "苏州太湖国家旅游度假区", "汾湖高新技术产业开发区",
        ],
    }

    indicator_weights = {
        "gdp": 0.28,
        "fiscal_revenue": 0.22,
        "industrial_output": 0.25,
        "employment": 0.1,
        "innovation": 0.15,
    }

    economic_characteristics = [
        "最强地级市", "制造业基地", "外向型经济发达",
        "生物医药产业", "纳米技术产业",
    ]

    benchmark_data = {
        "gdp_per_capita": 190200.0,
        "average_wage": 11200.0,
        "industrial_efficiency": 0.90,
        "land_price": 4200.0,
        "energy_cost": 0.76,
    }

    data_sources = [
        "nbs", "jiangsu_statistics_bureau",
        "suzhou_statistics_bureau", "industry_association",
    ]
