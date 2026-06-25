"""
太原地区配置
"""

from config.regions.template import RegionConfig


class TaiyuanConfig(RegionConfig):
    """太原配置"""

    name = "太原"
    code = "140100"
    province = "山西省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "小店区", "迎泽区", "杏花岭区", "尖草坪区", "万柏林区",
            "晋源区",
            "清徐县", "阳曲县", "娄烦县", "古交市",
        ],
        "development_zones": [
            "太原高新技术产业开发区", "太原经济技术开发区",
            "太原武宿综合保税区", "山西转型综合改革示范区",
            "太原不锈钢产业园区",
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
        "山西省省会", "中部地区重要中心城市",
        "能源重工业基地", "国家历史文化名城",
    ]

    benchmark_data = {
        "gdp_per_capita": 99500.0,
        "average_wage": 6800.0,
        "industrial_efficiency": 0.73,
        "land_price": 1600.0,
        "energy_cost": 0.56,
    }

    data_sources = [
        "nbs", "shanxi_statistics_bureau",
        "taiyuan_statistics_bureau", "industry_association",
    ]
