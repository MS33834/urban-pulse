"""
合肥地区配置
"""

from config.regions.template import RegionConfig


class HefeiConfig(RegionConfig):
    """合肥配置"""

    name = "合肥"
    code = "340100"
    province = "安徽省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "瑶海区", "庐阳区", "蜀山区", "包河区", "长丰县",
            "肥东县", "肥西县", "庐江县", "巢湖市",
        ],
        "development_zones": [
            "合肥高新技术产业开发区", "合肥经济技术开发区",
            "合肥新站高新技术产业开发区", "安徽巢湖经济开发区",
            "合肥滨湖科学城",
        ],
    }

    indicator_weights = {
        "gdp": 0.23,
        "fiscal_revenue": 0.18,
        "industrial_output": 0.22,
        "employment": 0.12,
        "innovation": 0.25,
    }

    economic_characteristics = [
        "安徽省省会", "长三角城市群副中心",
        "综合性国家科学中心", "家电产业基地",
        "新能源汽车之都",
    ]

    benchmark_data = {
        "gdp_per_capita": 128600.0,
        "average_wage": 9300.0,
        "industrial_efficiency": 0.82,
        "land_price": 2900.0,
        "energy_cost": 0.65,
    }

    data_sources = [
        "nbs", "anhui_statistics_bureau",
        "hefei_statistics_bureau", "industry_association",
    ]
