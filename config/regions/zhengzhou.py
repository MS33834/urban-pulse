"""
郑州地区配置
"""

from config.regions.template import RegionConfig


class ZhengzhouConfig(RegionConfig):
    """郑州配置"""

    name = "郑州"
    code = "410100"
    province = "河南省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "中原区", "二七区", "管城回族区", "金水区", "上街区",
            "惠济区", "中牟县", "巩义市", "荥阳市", "新密市",
            "新郑市", "登封市",
        ],
        "development_zones": [
            "郑州航空港经济综合实验区", "郑州经济技术开发区",
            "郑州高新技术产业开发区", "郑东新区",
            "郑州综合保税区",
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
        "国家中心城市", "中部地区重要中心城市",
        "国家重要综合交通枢纽", "商贸物流中心",
    ]

    benchmark_data = {
        "gdp_per_capita": 104700.0,
        "average_wage": 8200.0,
        "industrial_efficiency": 0.74,
        "land_price": 2400.0,
        "energy_cost": 0.60,
    }

    data_sources = [
        "nbs", "henan_statistics_bureau",
        "zhengzhou_statistics_bureau", "industry_association",
    ]
