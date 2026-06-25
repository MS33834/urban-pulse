"""
无锡地区配置
"""

from config.regions.template import RegionConfig


class WuxiConfig(RegionConfig):
    """无锡配置"""

    name = "无锡"
    code = "320200"
    province = "江苏省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "锡山区", "惠山区", "滨湖区", "梁溪区", "新吴区",
            "江阴市", "宜兴市",
        ],
        "development_zones": [
            "无锡高新技术产业开发区", "无锡经济开发区",
            "江阴经济技术开发区", "宜兴经济技术开发区",
            "无锡太湖国家旅游度假区",
        ],
    }

    indicator_weights = {
        "gdp": 0.27,
        "fiscal_revenue": 0.2,
        "industrial_output": 0.25,
        "employment": 0.1,
        "innovation": 0.18,
    }

    economic_characteristics = [
        "长三角中心城市", "制造业强市", "物联网产业基地",
        "新能源产业", "集成电路产业",
    ]

    benchmark_data = {
        "gdp_per_capita": 198100.0,
        "average_wage": 10600.0,
        "industrial_efficiency": 0.91,
        "land_price": 4000.0,
        "energy_cost": 0.73,
    }

    data_sources = [
        "nbs", "jiangsu_statistics_bureau",
        "wuxi_statistics_bureau", "industry_association",
    ]
