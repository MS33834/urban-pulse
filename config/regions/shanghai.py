"""
上海地区配置
"""

from config.regions.template import RegionConfig


class ShanghaiConfig(RegionConfig):
    """上海配置"""

    name = "上海"
    code = "310000"
    province = "上海市"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "黄浦区", "徐汇区", "长宁区", "静安区", "普陀区",
            "虹口区", "杨浦区", "闵行区", "宝山区", "嘉定区",
            "浦东新区", "金山区", "松江区", "青浦区", "奉贤区",
            "崇明区",
        ],
        "development_zones": [
            "上海自贸区", "张江高科技园区", "临港新片区",
            "虹桥国际中央商务区", "陆家嘴金融贸易区",
        ],
    }

    indicator_weights = {
        "gdp": 0.25,
        "fiscal_revenue": 0.2,
        "industrial_output": 0.15,
        "employment": 0.15,
        "innovation": 0.25,
    }

    economic_characteristics = [
        "国际经济中心", "国际金融中心", "国际贸易中心",
        "国际航运中心", "科技创新中心",
    ]

    benchmark_data = {
        "gdp_per_capita": 189600.0,
        "average_wage": 13500.0,
        "industrial_efficiency": 0.88,
        "land_price": 6800.0,
        "energy_cost": 0.82,
    }

    data_sources = [
        "nbs", "shanghai_statistics_bureau",
        "shanghai_bureau_of_finance", "industry_association",
    ]
