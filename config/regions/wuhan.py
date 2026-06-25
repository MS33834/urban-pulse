"""
武汉地区配置
"""

from config.regions.template import RegionConfig


class WuhanConfig(RegionConfig):
    """武汉配置"""

    name = "武汉"
    code = "420100"
    province = "湖北省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "江岸区", "江汉区", "硚口区", "汉阳区", "武昌区",
            "青山区", "洪山区", "东西湖区", "汉南区", "蔡甸区",
            "江夏区", "黄陂区", "新洲区",
        ],
        "development_zones": [
            "武汉东湖新技术开发区", "武汉经济技术开发区",
            "武汉临空港经济技术开发区", "武汉长江新区",
            "光谷科技创新大走廊",
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
        "国家中心城市", "中部地区龙头", "光电子信息产业基地",
        "汽车产业基地", "科教资源集聚",
    ]

    benchmark_data = {
        "gdp_per_capita": 153800.0,
        "average_wage": 9800.0,
        "industrial_efficiency": 0.80,
        "land_price": 3200.0,
        "energy_cost": 0.68,
    }

    data_sources = [
        "nbs", "hubei_statistics_bureau",
        "wuhan_statistics_bureau", "industry_association",
    ]
