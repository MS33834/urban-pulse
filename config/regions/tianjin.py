"""
天津地区配置
"""

from config.regions.template import RegionConfig


class TianjinConfig(RegionConfig):
    """天津配置"""

    name = "天津"
    code = "120000"
    province = "天津市"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "和平区", "河东区", "河西区", "南开区", "河北区",
            "红桥区", "东丽区", "西青区", "津南区", "北辰区",
            "武清区", "宝坻区", "滨海新区", "宁河区", "静海区",
            "蓟州区",
        ],
        "development_zones": [
            "天津滨海新区", "天津经济技术开发区",
            "天津港保税区", "天津滨海高新技术产业开发区",
            "天津东疆保税港区",
        ],
    }

    indicator_weights = {
        "gdp": 0.25,
        "fiscal_revenue": 0.22,
        "industrial_output": 0.2,
        "employment": 0.13,
        "innovation": 0.2,
    }

    economic_characteristics = [
        "北方经济中心", "国际港口城市",
        "北方国际航运核心区", "金融创新运营示范区",
        "改革开放先行区",
    ]

    benchmark_data = {
        "gdp_per_capita": 122800.0,
        "average_wage": 10500.0,
        "industrial_efficiency": 0.80,
        "land_price": 3600.0,
        "energy_cost": 0.72,
    }

    data_sources = [
        "nbs", "tianjin_statistics_bureau",
        "tianjin_bureau_of_finance", "industry_association",
    ]
