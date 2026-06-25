"""
沈阳地区配置
"""

from config.regions.template import RegionConfig


class ShenyangConfig(RegionConfig):
    """沈阳配置"""

    name = "沈阳"
    code = "210100"
    province = "辽宁省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "和平区", "沈河区", "大东区", "皇姑区", "铁西区",
            "苏家屯区", "浑南区", "沈北新区", "于洪区", "辽中区",
            "康平县", "法库县", "新民市",
        ],
        "development_zones": [
            "沈阳高新技术产业开发区", "沈阳经济技术开发区",
            "沈阳综合保税区", "沈阳金融商贸开发区",
            "沈阳中德装备园",
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
        "辽宁省省会", "东北地区重要中心城市",
        "先进装备制造业基地", "国家历史文化名城",
    ]

    benchmark_data = {
        "gdp_per_capita": 88800.0,
        "average_wage": 7000.0,
        "industrial_efficiency": 0.74,
        "land_price": 1700.0,
        "energy_cost": 0.56,
    }

    data_sources = [
        "nbs", "liaoning_statistics_bureau",
        "shenyang_statistics_bureau", "industry_association",
    ]
