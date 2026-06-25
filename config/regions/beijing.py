"""
北京地区配置
"""

from config.regions.template import RegionConfig


class BeijingConfig(RegionConfig):
    """北京配置"""

    name = "北京"
    code = "110000"
    province = "北京市"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "东城区", "西城区", "朝阳区", "丰台区", "石景山区",
            "海淀区", "门头沟区", "房山区", "通州区", "顺义区",
            "昌平区", "大兴区", "怀柔区", "平谷区", "密云区",
            "延庆区",
        ],
        "development_zones": [
            "中关村国家自主创新示范区", "北京经济技术开发区",
            "通州副中心", "临空经济区", "怀柔科学城",
        ],
    }

    indicator_weights = {
        "gdp": 0.2,
        "fiscal_revenue": 0.2,
        "industrial_output": 0.1,
        "employment": 0.15,
        "innovation": 0.35,
    }

    economic_characteristics = [
        "全国政治中心", "文化中心", "国际交往中心",
        "科技创新中心", "总部经济集聚",
    ]

    benchmark_data = {
        "gdp_per_capita": 199800.0,
        "average_wage": 14200.0,
        "industrial_efficiency": 0.86,
        "land_price": 7500.0,
        "energy_cost": 0.85,
    }

    data_sources = [
        "nbs", "beijing_statistics_bureau",
        "beijing_bureau_of_finance", "industry_association",
    ]
