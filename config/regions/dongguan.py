"""
东莞地区配置
"""

from config.regions.template import RegionConfig


class DongguanConfig(RegionConfig):
    """东莞配置"""

    name = "东莞"
    code = "441900"
    province = "广东省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "东城街道", "南城街道", "万江街道", "莞城街道",
            "石碣镇", "石龙镇", "茶山镇", "石排镇", "企石镇",
            "横沥镇", "桥头镇", "谢岗镇", "东坑镇", "常平镇",
            "寮步镇", "樟木头镇", "大朗镇", "黄江镇", "清溪镇",
            "塘厦镇", "凤岗镇", "大岭山镇", "长安镇", "虎门镇",
            "厚街镇", "沙田镇", "道滘镇", "洪梅镇", "麻涌镇",
            "望牛墩镇", "中堂镇", "高埗镇", "松山湖管委会",
        ],
        "development_zones": [
            "东莞松山湖高新技术产业开发区", "东莞港保税区",
            "东莞滨海湾新区", "东莞生态园",
            "东莞水乡特色发展经济区",
        ],
    }

    indicator_weights = {
        "gdp": 0.28,
        "fiscal_revenue": 0.18,
        "industrial_output": 0.3,
        "employment": 0.1,
        "innovation": 0.14,
    }

    economic_characteristics = [
        "世界工厂", "制造业基地", "珠三角重要城市",
        "电子信息产业基地", "外贸出口大市",
    ]

    benchmark_data = {
        "gdp_per_capita": 109100.0,
        "average_wage": 9000.0,
        "industrial_efficiency": 0.84,
        "land_price": 2800.0,
        "energy_cost": 0.64,
    }

    data_sources = [
        "nbs", "guangdong_statistics_bureau",
        "dongguan_statistics_bureau", "industry_association",
    ]
