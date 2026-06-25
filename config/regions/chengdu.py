"""
成都地区配置
"""

from config.regions.template import RegionConfig


class ChengduConfig(RegionConfig):
    """成都配置"""

    name = "成都"
    code = "510100"
    province = "四川省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "锦江区", "青羊区", "金牛区", "武侯区", "成华区",
            "龙泉驿区", "青白江区", "新都区", "温江区", "双流区",
            "郫都区", "新津区", "都江堰市", "彭州市", "邛崃市",
            "崇州市", "简阳市", "金堂县", "大邑县", "蒲江县",
        ],
        "development_zones": [
            "成都高新区", "天府新区", "成都经济技术开发区",
            "成都临空经济示范区", "成都国际生物城",
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
        "国家中心城市", "西部经济中心", "科技中心",
        "文创中心", "对外交往中心",
    ]

    benchmark_data = {
        "gdp_per_capita": 108600.0,
        "average_wage": 9200.0,
        "industrial_efficiency": 0.78,
        "land_price": 2800.0,
        "energy_cost": 0.62,
    }

    data_sources = [
        "nbs", "sichuan_statistics_bureau",
        "chengdu_statistics_bureau", "industry_association",
    ]
