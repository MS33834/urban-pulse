"""
石家庄地区配置
"""

from config.regions.template import RegionConfig


class ShijiazhuangConfig(RegionConfig):
    """石家庄配置"""

    name = "石家庄"
    code = "130100"
    province = "河北省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "长安区", "桥西区", "新华区", "井陉矿区", "裕华区",
            "藁城区", "鹿泉区", "栾城区",
            "井陉县", "正定县", "行唐县", "灵寿县", "高邑县",
            "深泽县", "赞皇县", "无极县", "平山县", "元氏县",
            "赵县", "晋州市", "新乐市",
        ],
        "development_zones": [
            "石家庄高新技术产业开发区", "石家庄经济技术开发区",
            "石家庄综合保税区", "正定新区",
            "石家庄循环化工园区",
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
        "河北省省会", "京津冀地区重要中心城市",
        "全国重要的医药工业基地", "交通枢纽城市",
    ]

    benchmark_data = {
        "gdp_per_capita": 67100.0,
        "average_wage": 6500.0,
        "industrial_efficiency": 0.72,
        "land_price": 1500.0,
        "energy_cost": 0.54,
    }

    data_sources = [
        "nbs", "hebei_statistics_bureau",
        "shijiazhuang_statistics_bureau", "industry_association",
    ]
