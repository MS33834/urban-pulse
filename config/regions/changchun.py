"""
长春地区配置
"""

from config.regions.template import RegionConfig


class ChangchunConfig(RegionConfig):
    """长春配置"""

    name = "长春"
    code = "220100"
    province = "吉林省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "南关区", "宽城区", "朝阳区", "二道区", "绿园区",
            "双阳区", "九台区",
            "农安县", "榆树市", "德惠市", "公主岭市",
        ],
        "development_zones": [
            "长春高新技术产业开发区", "长春经济技术开发区",
            "长春净月高新技术产业开发区", "长春汽车经济技术开发区",
            "长春新区",
        ],
    }

    indicator_weights = {
        "gdp": 0.25,
        "fiscal_revenue": 0.2,
        "industrial_output": 0.25,
        "employment": 0.1,
        "innovation": 0.2,
    }

    economic_characteristics = [
        "吉林省省会", "东北地区重要中心城市",
        "中国汽车工业摇篮", "电影文化名城",
    ]

    benchmark_data = {
        "gdp_per_capita": 66200.0,
        "average_wage": 6200.0,
        "industrial_efficiency": 0.70,
        "land_price": 1400.0,
        "energy_cost": 0.53,
    }

    data_sources = [
        "nbs", "jilin_statistics_bureau",
        "changchun_statistics_bureau", "industry_association",
    ]
