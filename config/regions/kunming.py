"""
昆明地区配置
"""

from config.regions.template import RegionConfig


class KunmingConfig(RegionConfig):
    """昆明配置"""

    name = "昆明"
    code = "530100"
    province = "云南省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "五华区", "盘龙区", "官渡区", "西山区", "东川区",
            "呈贡区", "晋宁区", "富民县", "宜良县", "嵩明县",
            "石林彝族自治县", "禄劝彝族苗族自治县",
            "寻甸回族彝族自治县", "安宁市",
        ],
        "development_zones": [
            "昆明高新技术产业开发区", "昆明经济技术开发区",
            "昆明综合保税区", "滇池旅游度假区",
            "昆明阳宗海风景名胜区",
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
        "云南省省会", "西部地区重要中心城市",
        "国家历史文化名城", "面向东南亚南亚开放的区域性国际中心城市",
    ]

    benchmark_data = {
        "gdp_per_capita": 91200.0,
        "average_wage": 7200.0,
        "industrial_efficiency": 0.72,
        "land_price": 1800.0,
        "energy_cost": 0.55,
    }

    data_sources = [
        "nbs", "yunnan_statistics_bureau",
        "kunming_statistics_bureau", "industry_association",
    ]
