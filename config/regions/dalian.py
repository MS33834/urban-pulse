"""
大连地区配置
"""

from config.regions.template import RegionConfig


class DalianConfig(RegionConfig):
    """大连配置"""

    name = "大连"
    code = "210200"
    province = "辽宁省"
    country = "中国"

    statistical_caliber = "city"

    administrative_divisions = {
        "districts": [
            "中山区", "西岗区", "沙河口区", "甘井子区", "旅顺口区",
            "金州区", "普兰店区", "长海县", "瓦房店市", "庄河市",
        ],
        "development_zones": [
            "大连经济技术开发区", "大连高新技术产业园区",
            "大连保税区", "大连长兴岛经济技术开发区",
            "大连金石滩国家旅游度假区",
        ],
    }

    indicator_weights = {
        "gdp": 0.23,
        "fiscal_revenue": 0.22,
        "industrial_output": 0.2,
        "employment": 0.1,
        "innovation": 0.25,
    }

    economic_characteristics = [
        "计划单列市", "北方沿海重要中心城市",
        "港口及风景旅游城市", "东北亚国际航运中心",
    ]

    benchmark_data = {
        "gdp_per_capita": 116200.0,
        "average_wage": 7400.0,
        "industrial_efficiency": 0.76,
        "land_price": 1900.0,
        "energy_cost": 0.58,
    }

    data_sources = [
        "nbs", "liaoning_statistics_bureau",
        "dalian_statistics_bureau", "industry_association",
    ]
