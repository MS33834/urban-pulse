"""
青岛地区配置
"""

from config.regions.template import RegionConfig


class QingdaoConfig(RegionConfig):
    """青岛配置"""

    name = "青岛"
    code = "370200"
    province = "山东省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "市南区", "市北区", "黄岛区", "崂山区", "李沧区",
            "城阳区", "即墨区", "胶州市", "平度市", "莱西市",
        ],
        "development_zones": [
            "青岛西海岸新区", "青岛经济技术开发区",
            "青岛高新技术产业开发区", "青岛前湾保税港区",
            "青岛蓝谷",
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
        "沿海重要中心城市", "滨海度假旅游城市",
        "国家历史文化名城", "海洋经济发展示范区",
        "先进制造业基地",
    ]

    benchmark_data = {
        "gdp_per_capita": 161200.0,
        "average_wage": 10000.0,
        "industrial_efficiency": 0.80,
        "land_price": 3400.0,
        "energy_cost": 0.70,
    }

    data_sources = [
        "nbs", "shandong_statistics_bureau",
        "qingdao_statistics_bureau", "industry_association",
    ]
