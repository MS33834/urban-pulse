"""
南京地区配置
"""

from config.regions.template import RegionConfig


class NanjingConfig(RegionConfig):
    """南京配置"""

    name = "南京"
    code = "320100"
    province = "江苏省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "玄武区", "秦淮区", "建邺区", "鼓楼区", "浦口区",
            "栖霞区", "雨花台区", "江宁区", "六合区", "溧水区",
            "高淳区",
        ],
        "development_zones": [
            "南京江北新区", "南京经济技术开发区",
            "江宁经济技术开发区", "南京高新技术产业开发区",
            "南京麒麟科技创新园",
        ],
    }

    indicator_weights = {
        "gdp": 0.22,
        "fiscal_revenue": 0.2,
        "industrial_output": 0.18,
        "employment": 0.15,
        "innovation": 0.25,
    }

    economic_characteristics = [
        "东部地区重要中心城市", "全国重要科研教育基地",
        "综合交通枢纽", "软件产业基地", "先进制造业基地",
    ]

    benchmark_data = {
        "gdp_per_capita": 184800.0,
        "average_wage": 12000.0,
        "industrial_efficiency": 0.85,
        "land_price": 5800.0,
        "energy_cost": 0.76,
    }

    data_sources = [
        "nbs", "jiangsu_statistics_bureau",
        "nanjing_statistics_bureau", "industry_association",
    ]
