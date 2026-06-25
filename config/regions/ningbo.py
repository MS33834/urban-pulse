"""
宁波地区配置
"""

from config.regions.template import RegionConfig


class NingboConfig(RegionConfig):
    """宁波配置"""

    name = "宁波"
    code = "330200"
    province = "浙江省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "海曙区", "江北区", "北仑区", "镇海区", "鄞州区",
            "奉化区", "余姚市", "慈溪市", "象山县", "宁海县",
        ],
        "development_zones": [
            "宁波舟山港", "宁波经济技术开发区",
            "宁波保税区", "宁波高新技术产业开发区",
            "宁波前湾新区",
        ],
    }

    indicator_weights = {
        "gdp": 0.25,
        "fiscal_revenue": 0.22,
        "industrial_output": 0.25,
        "employment": 0.1,
        "innovation": 0.18,
    }

    economic_characteristics = [
        "计划单列市", "港口城市", "制造业基地",
        "外贸口岸", "海洋经济强市",
    ]

    benchmark_data = {
        "gdp_per_capita": 169600.0,
        "average_wage": 10800.0,
        "industrial_efficiency": 0.86,
        "land_price": 3800.0,
        "energy_cost": 0.74,
    }

    data_sources = [
        "nbs", "zhejiang_statistics_bureau",
        "ningbo_statistics_bureau", "industry_association",
    ]
