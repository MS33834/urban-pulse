"""
济南地区配置
"""

from config.regions.template import RegionConfig


class JinanConfig(RegionConfig):
    """济南配置"""

    name = "济南"
    code = "370100"
    province = "山东省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "历下区", "市中区", "槐荫区", "天桥区", "历城区",
            "长清区", "章丘区", "济阳区", "莱芜区", "钢城区",
            "平阴县", "商河县",
        ],
        "development_zones": [
            "济南高新技术产业开发区", "济南经济技术开发区",
            "济南综合保税区", "济南新旧动能转换起步区",
            "济南国际医学科学中心",
        ],
    }

    indicator_weights = {
        "gdp": 0.25,
        "fiscal_revenue": 0.2,
        "industrial_output": 0.18,
        "employment": 0.15,
        "innovation": 0.22,
    }

    economic_characteristics = [
        "山东省省会", "环渤海地区南翼中心城市",
        "泉城文化名城", "高端装备制造业基地",
    ]

    benchmark_data = {
        "gdp_per_capita": 135200.0,
        "average_wage": 9400.0,
        "industrial_efficiency": 0.78,
        "land_price": 3100.0,
        "energy_cost": 0.67,
    }

    data_sources = [
        "nbs", "shandong_statistics_bureau",
        "jinan_statistics_bureau", "industry_association",
    ]
