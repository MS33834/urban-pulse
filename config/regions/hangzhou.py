"""
杭州地区配置
"""

from config.regions.template import RegionConfig


class HangzhouConfig(RegionConfig):
    """杭州配置"""

    name = "杭州"
    code = "330100"
    province = "浙江省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "上城区", "拱墅区", "西湖区", "滨江区", "萧山区",
            "余杭区", "临平区", "钱塘区", "富阳区", "临安区",
            "桐庐县", "淳安县", "建德市",
        ],
        "development_zones": [
            "杭州高新区（滨江）", "杭州经济技术开发区",
            "杭州临空经济示范区", "杭州未来科技城",
            "钱塘新区",
        ],
    }

    indicator_weights = {
        "gdp": 0.22,
        "fiscal_revenue": 0.18,
        "industrial_output": 0.15,
        "employment": 0.15,
        "innovation": 0.3,
    }

    economic_characteristics = [
        "数字经济第一城", "电子商务中心", "创新活力之城",
        "先进制造业基地", "文化旅游名城",
    ]

    benchmark_data = {
        "gdp_per_capita": 168800.0,
        "average_wage": 12500.0,
        "industrial_efficiency": 0.84,
        "land_price": 5500.0,
        "energy_cost": 0.80,
    }

    data_sources = [
        "nbs", "zhejiang_statistics_bureau",
        "hangzhou_statistics_bureau", "industry_association",
    ]
