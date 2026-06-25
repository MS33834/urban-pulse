"""
贵阳地区配置
"""

from config.regions.template import RegionConfig


class GuiyangConfig(RegionConfig):
    """贵阳配置"""

    name = "贵阳"
    code = "520100"
    province = "贵州省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "南明区", "云岩区", "花溪区", "乌当区", "白云区",
            "观山湖区",
            "开阳县", "息烽县", "修文县", "清镇市",
        ],
        "development_zones": [
            "贵阳国家高新技术产业开发区", "贵阳经济技术开发区",
            "贵阳综合保税区", "贵州双龙航空港经济区",
            "贵安新区",
        ],
    }

    indicator_weights = {
        "gdp": 0.23,
        "fiscal_revenue": 0.18,
        "industrial_output": 0.2,
        "employment": 0.15,
        "innovation": 0.24,
    }

    economic_characteristics = [
        "贵州省省会", "西南地区重要中心城市",
        "大数据产业之都", "国家大数据综合试验区核心区",
    ]

    benchmark_data = {
        "gdp_per_capita": 77500.0,
        "average_wage": 6500.0,
        "industrial_efficiency": 0.70,
        "land_price": 1600.0,
        "energy_cost": 0.54,
    }

    data_sources = [
        "nbs", "guizhou_statistics_bureau",
        "guiyang_statistics_bureau", "industry_association",
    ]
