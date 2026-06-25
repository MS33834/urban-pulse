"""
福州地区配置
"""

from config.regions.template import RegionConfig


class FuzhouConfig(RegionConfig):
    """福州配置"""

    name = "福州"
    code = "350100"
    province = "福建省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "鼓楼区", "台江区", "仓山区", "马尾区", "晋安区",
            "长乐区", "闽侯县", "连江县", "罗源县", "闽清县",
            "永泰县", "平潭县", "福清市",
        ],
        "development_zones": [
            "福州经济技术开发区", "福州高新技术产业开发区",
            "福州保税区", "福州台商投资区",
            "福州新区",
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
        "福建省省会", "海峡西岸经济区中心城市",
        "滨江滨海生态园林城市", "数字经济产业基地",
    ]

    benchmark_data = {
        "gdp_per_capita": 158200.0,
        "average_wage": 9600.0,
        "industrial_efficiency": 0.78,
        "land_price": 3200.0,
        "energy_cost": 0.68,
    }

    data_sources = [
        "nbs", "fujian_statistics_bureau",
        "fuzhou_statistics_bureau", "industry_association",
    ]
