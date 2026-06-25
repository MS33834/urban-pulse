"""
南宁地区配置
"""

from config.regions.template import RegionConfig


class NanningConfig(RegionConfig):
    """南宁配置"""

    name = "南宁"
    code = "450100"
    province = "广西壮族自治区"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "兴宁区", "青秀区", "江南区", "西乡塘区", "良庆区",
            "邕宁区", "武鸣区",
            "隆安县", "马山县", "上林县", "宾阳县", "横州市",
        ],
        "development_zones": [
            "南宁高新技术产业开发区", "南宁经济技术开发区",
            "南宁综合保税区", "广西-东盟经济技术开发区",
            "五象新区",
        ],
    }

    indicator_weights = {
        "gdp": 0.25,
        "fiscal_revenue": 0.2,
        "industrial_output": 0.18,
        "employment": 0.17,
        "innovation": 0.2,
    }

    economic_characteristics = [
        "广西壮族自治区首府", "北部湾经济区中心城市",
        "面向东盟开放合作的前沿城市", "国家生态园林城市",
    ]

    benchmark_data = {
        "gdp_per_capita": 64800.0,
        "average_wage": 6200.0,
        "industrial_efficiency": 0.68,
        "land_price": 1500.0,
        "energy_cost": 0.53,
    }

    data_sources = [
        "nbs", "guangxi_statistics_bureau",
        "nanning_statistics_bureau", "industry_association",
    ]
