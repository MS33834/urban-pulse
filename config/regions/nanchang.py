"""
南昌地区配置
"""

from config.regions.template import RegionConfig


class NanchangConfig(RegionConfig):
    """南昌配置"""

    name = "南昌"
    code = "360100"
    province = "江西省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "东湖区", "西湖区", "青云谱区", "青山湖区", "新建区",
            "红谷滩区",
            "南昌县", "安义县", "进贤县",
        ],
        "development_zones": [
            "南昌高新技术产业开发区", "南昌经济技术开发区",
            "南昌综合保税区", "南昌小蓝经济技术开发区",
            "赣江新区",
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
        "江西省省会", "长江中游地区重要中心城市",
        "航空工业基地", "国家历史文化名城",
    ]

    benchmark_data = {
        "gdp_per_capita": 110000.0,
        "average_wage": 7000.0,
        "industrial_efficiency": 0.75,
        "land_price": 1750.0,
        "energy_cost": 0.57,
    }

    data_sources = [
        "nbs", "jiangxi_statistics_bureau",
        "nanchang_statistics_bureau", "industry_association",
    ]
