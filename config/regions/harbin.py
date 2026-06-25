"""
哈尔滨地区配置
"""

from config.regions.template import RegionConfig


class HarbinConfig(RegionConfig):
    """哈尔滨配置"""

    name = "哈尔滨"
    code = "230100"
    province = "黑龙江省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "道里区", "南岗区", "道外区", "平房区", "松北区",
            "香坊区", "呼兰区", "阿城区", "双城区",
            "依兰县", "方正县", "宾县", "巴彦县", "木兰县",
            "通河县", "延寿县", "尚志市", "五常市",
        ],
        "development_zones": [
            "哈尔滨高新技术产业开发区", "哈尔滨经济技术开发区",
            "哈尔滨综合保税区", "哈尔滨利民经济技术开发区",
            "哈尔滨新区",
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
        "黑龙江省省会", "东北地区重要中心城市",
        "国家重要制造业基地", "冰雪文化名城",
    ]

    benchmark_data = {
        "gdp_per_capita": 56800.0,
        "average_wage": 6000.0,
        "industrial_efficiency": 0.68,
        "land_price": 1300.0,
        "energy_cost": 0.52,
    }

    data_sources = [
        "nbs", "heilongjiang_statistics_bureau",
        "harbin_statistics_bureau", "industry_association",
    ]
