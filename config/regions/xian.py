"""
西安地区配置
"""

from config.regions.template import RegionConfig


class XianConfig(RegionConfig):
    """西安配置"""

    name = "西安"
    code = "610100"
    province = "陕西省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "新城区", "碑林区", "莲湖区", "灞桥区", "未央区",
            "雁塔区", "阎良区", "临潼区", "长安区", "高陵区",
            "鄠邑区", "蓝田县", "周至县",
        ],
        "development_zones": [
            "西安高新技术产业开发区", "西安经济技术开发区",
            "西安曲江新区", "西安浐灞生态区", "西安国际港务区",
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
        "国家中心城市", "西部重要中心城市",
        "科研教育基地", "历史文化名城", "先进制造业基地",
    ]

    benchmark_data = {
        "gdp_per_capita": 99900.0,
        "average_wage": 8500.0,
        "industrial_efficiency": 0.76,
        "land_price": 2600.0,
        "energy_cost": 0.65,
    }

    data_sources = [
        "nbs", "shaanxi_statistics_bureau",
        "xian_statistics_bureau", "industry_association",
    ]
