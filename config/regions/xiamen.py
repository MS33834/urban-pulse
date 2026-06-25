"""
厦门地区配置
"""

from config.regions.template import RegionConfig


class XiamenConfig(RegionConfig):
    """厦门配置"""

    name = "厦门"
    code = "350200"
    province = "福建省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "思明区", "海沧区", "湖里区", "集美区", "同安区",
            "翔安区",
        ],
        "development_zones": [
            "厦门经济特区", "厦门火炬高技术产业开发区",
            "厦门保税区", "厦门海沧保税港区",
            "两岸区域性金融服务中心",
        ],
    }

    indicator_weights = {
        "gdp": 0.2,
        "fiscal_revenue": 0.22,
        "industrial_output": 0.18,
        "employment": 0.1,
        "innovation": 0.3,
    }

    economic_characteristics = [
        "经济特区", "计划单列市",
        "东南沿海重要中心城市", "港口及风景旅游城市",
        "海峡西岸经济区重要中心城市",
    ]

    benchmark_data = {
        "gdp_per_capita": 161600.0,
        "average_wage": 10200.0,
        "industrial_efficiency": 0.82,
        "land_price": 4500.0,
        "energy_cost": 0.72,
    }

    data_sources = [
        "nbs", "fujian_statistics_bureau",
        "xiamen_statistics_bureau", "industry_association",
    ]
