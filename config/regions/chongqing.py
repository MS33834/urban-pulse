"""
重庆地区配置
"""

from config.regions.template import RegionConfig


class ChongqingConfig(RegionConfig):
    """重庆配置"""

    name = "重庆"
    code = "500000"
    province = "重庆市"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "万州区", "涪陵区", "渝中区", "大渡口区", "江北区",
            "沙坪坝区", "九龙坡区", "南岸区", "北碚区", "綦江区",
            "大足区", "渝北区", "巴南区", "黔江区", "长寿区",
            "江津区", "合川区", "永川区", "南川区", "璧山区",
            "铜梁区", "潼南区", "荣昌区", "开州区", "梁平区",
            "武隆区",
        ],
        "development_zones": [
            "重庆两江新区", "重庆高新技术产业开发区",
            "重庆经济技术开发区", "重庆两路寸滩保税港区",
            "重庆西永综合保税区",
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
        "国家中心城市", "长江上游经济中心",
        "现代制造业基地", "西南综合交通枢纽",
    ]

    benchmark_data = {
        "gdp_per_capita": 94400.0,
        "average_wage": 8800.0,
        "industrial_efficiency": 0.75,
        "land_price": 2400.0,
        "energy_cost": 0.60,
    }

    data_sources = [
        "nbs", "chongqing_statistics_bureau",
        "chongqing_bureau_of_finance", "industry_association",
    ]
