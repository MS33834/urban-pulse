"""生成扩展后的 data/cities/cities.yaml

数据说明：
- 2024 年核心宏观经济指标基于各城市统计公报、国家统计局公开数据整理。
- 商业成本类指标（地价、薪资、能耗、融资、政策等）为基于城市等级和产业结构的
  合理估算，用于演示城市对比与评分模型。
- 2020-2024 年历史时序用于演示预测能力，GDP/人口/财政收入基于公开趋势推算，
  其他字段为模型估算。
- 来源字段统一标注为"各城市统计局 2020-2024 统计公报 + Urban Pulse 模型估算"，
  实际生产环境应接入官方 API。
"""

from __future__ import annotations

from pathlib import Path

import yaml


def build_city(
    code: str,
    name: str,
    province: str,
    parent_code: str,
    region: str,
    base: dict,
    history: list[dict],
) -> dict:
    return {
        "code": code,
        "name": name,
        "province": province,
        "parent_code": parent_code,
        "region": region,
        **base,
        "historical_data": history,
        "metadata": {
            "data_source": "各城市统计局 2020-2024 统计公报 + Urban Pulse 模型估算",
            "data_quality": base.get("data_quality", 85.0),
            "update_frequency": "annual",
        },
    }


# 2024 年宏观经济指标（gdp/增速/人口/财政收入/研发强度/高技术占比/数据质量）
CITY_SPECS = [
    # 一线城市
    ("CN-GD-SZ", "深圳", "广东", "CN-GD", "华南", 34606.4, 6.7, 1779.0, 4012.0, 5.49, 62.5, 95.0),
    ("CN-SH-SH", "上海", "上海", "CN-SH", "华东", 47218.7, 5.0, 2487.4, 7800.0, 4.4, 55.0, 96.0),
    ("CN-BJ-BJ", "北京", "北京", "CN-BJ", "华北", 43761.0, 5.2, 2185.8, 5800.0, 6.49, 58.0, 96.0),
    ("CN-GD-GZ", "广州", "广东", "CN-GD", "华南", 31045.0, 4.6, 1881.0, 1920.0, 3.5, 48.0, 94.0),
    # 新一线 / 强二线
    ("CN-JS-SZ", "苏州", "江苏", "CN-JS", "华东", 24653.0, 4.5, 1295.8, 2400.0, 3.8, 52.0, 93.0),
    ("CN-SC-CD", "成都", "四川", "CN-SC", "西南", 23311.0, 6.2, 2147.4, 1600.0, 3.2, 42.0, 91.0),
    ("CN-ZJ-HZ", "杭州", "浙江", "CN-ZJ", "华东", 21140.0, 5.6, 1252.2, 2400.0, 4.0, 55.0, 93.0),
    ("CN-HB-WH", "武汉", "湖北", "CN-HB", "华中", 21180.0, 5.2, 1377.0, 1500.0, 3.5, 42.0, 91.0),
    ("CN-JS-NJ", "南京", "江苏", "CN-JS", "华东", 17421.0, 4.6, 942.3, 1600.0, 3.8, 48.0, 92.0),
    ("CN-SN-XA", "西安", "陕西", "CN-SN", "西北", 13168.0, 5.2, 1316.3, 850.0, 3.5, 40.0, 89.0),
    ("CN-CQ-CQ", "重庆", "重庆", "CN-CQ", "西南", 30145.8, 6.0, 3191.4, 2100.0, 2.5, 35.0, 91.0),
    ("CN-TJ-TJ", "天津", "天津", "CN-TJ", "华北", 16737.3, 5.1, 1363.0, 1750.0, 3.5, 45.0, 91.0),
    ("CN-SD-QD", "青岛", "山东", "CN-SD", "华东", 16719.5, 5.7, 1037.2, 1300.0, 2.8, 38.0, 90.0),
    ("CN-ZJ-NB", "宁波", "浙江", "CN-ZJ", "华东", 16452.8, 5.4, 969.7, 1650.0, 3.0, 40.0, 91.0),
    ("CN-JS-WX", "无锡", "江苏", "CN-JS", "华东", 14850.8, 5.8, 749.5, 1200.0, 3.3, 48.0, 90.0),
    ("CN-HN-CS", "长沙", "湖南", "CN-HN", "华中", 14331.0, 5.0, 1042.0, 1220.0, 3.0, 36.0, 90.0),
    ("CN-HA-ZZ", "郑州", "河南", "CN-HA", "华中", 13617.8, 5.3, 1300.8, 1160.0, 2.6, 32.0, 88.0),
    ("CN-GD-FS", "佛山", "广东", "CN-GD", "华南", 12698.0, 4.5, 961.5, 800.0, 2.8, 35.0, 89.0),
    ("CN-SD-JN", "济南", "山东", "CN-SD", "华东", 12757.4, 5.4, 943.7, 1000.0, 2.7, 34.0, 89.0),
    ("CN-AH-HF", "合肥", "安徽", "CN-AH", "华东", 12673.8, 5.8, 985.3, 920.0, 3.6, 42.0, 89.0),
    ("CN-FJ-FZ", "福州", "福建", "CN-FJ", "华东", 13400.0, 5.5, 846.9, 750.0, 2.4, 30.0, 89.0),
    ("CN-FJ-XM", "厦门", "福建", "CN-FJ", "华东", 8589.0, 5.5, 531.5, 830.0, 3.2, 42.0, 90.0),
    ("CN-GD-DG", "东莞", "广东", "CN-GD", "华南", 11438.1, 4.0, 1048.5, 750.0, 3.0, 38.0, 88.0),
    # 二线 / 省会
    ("CN-YN-KM", "昆明", "云南", "CN-YN", "西南", 7864.8, 4.0, 862.0, 540.0, 1.8, 22.0, 86.0),
    ("CN-LN-SY", "沈阳", "辽宁", "CN-LN", "东北", 8122.1, 5.0, 915.0, 610.0, 2.3, 25.0, 87.0),
    ("CN-LN-DL", "大连", "辽宁", "CN-LN", "东北", 8752.9, 5.0, 753.1, 760.0, 2.5, 28.0, 88.0),
    ("CN-HL-HRB", "哈尔滨", "黑龙江", "CN-HL", "东北", 5576.3, 3.1, 982.0, 320.0, 1.9, 20.0, 84.0),
    ("CN-JL-CC", "长春", "吉林", "CN-JL", "东北", 6001.9, 5.0, 907.0, 310.0, 2.0, 22.0, 85.0),
    ("CN-HE-SJZ", "石家庄", "河北", "CN-HE", "华北", 7534.2, 5.0, 1122.0, 620.0, 2.1, 24.0, 86.0),
    ("CN-SX-TY", "太原", "山西", "CN-SX", "华北", 5418.9, 3.0, 544.4, 450.0, 2.0, 23.0, 85.0),
    ("CN-JX-NC", "南昌", "江西", "CN-JX", "华东", 7203.5, 4.8, 654.7, 540.0, 1.8, 25.0, 87.0),
    ("CN-GZ-GY", "贵阳", "贵州", "CN-GZ", "西南", 5154.8, 4.5, 640.3, 410.0, 1.5, 18.0, 85.0),
    ("CN-GX-NN", "南宁", "广西", "CN-GX", "华南", 5491.1, 3.0, 894.1, 380.0, 1.6, 19.0, 84.0),
    ("CN-XJ-WLMQ", "乌鲁木齐", "新疆", "CN-XJ", "西北", 4163.0, 5.0, 408.5, 370.0, 1.4, 18.0, 83.0),
    ("CN-GS-LZ", "兰州", "甘肃", "CN-GS", "西北", 3487.3, 4.0, 442.5, 220.0, 1.7, 20.0, 83.0),
]


# 基于城市等级的商业成本/政策/产业环境估算（用于评分模型兼容）
TIER_PARAMS = {
    # 一线城市
    "深圳": {"land_price": 5200, "salary_level": 12800, "energy_cost": 0.78, "financing_cost": 3.2, "local_support_rate": 85.5, "avg_delivery_time": 3.5, "location_quotient": 1.85, "tax_reduction": 28.5, "policy_coverage": 92.0, "tax_coverage": 92.0, "rd_subsidy": 15.0, "avg_approval_time": 18.0},
    "上海": {"land_price": 6800, "salary_level": 13500, "energy_cost": 0.82, "financing_cost": 3.0, "local_support_rate": 82.0, "avg_delivery_time": 4.0, "location_quotient": 1.75, "tax_reduction": 25.0, "policy_coverage": 88.0, "tax_coverage": 88.0, "rd_subsidy": 12.0, "avg_approval_time": 22.0},
    "北京": {"land_price": 7500, "salary_level": 14200, "energy_cost": 0.85, "financing_cost": 2.8, "local_support_rate": 78.0, "avg_delivery_time": 4.5, "location_quotient": 1.60, "tax_reduction": 22.0, "policy_coverage": 85.0, "tax_coverage": 85.0, "rd_subsidy": 18.0, "avg_approval_time": 25.0},
    "广州": {"land_price": 4800, "salary_level": 11800, "energy_cost": 0.75, "financing_cost": 3.5, "local_support_rate": 75.0, "avg_delivery_time": 4.0, "location_quotient": 1.45, "tax_reduction": 24.0, "policy_coverage": 82.0, "tax_coverage": 82.0, "rd_subsidy": 10.0, "avg_approval_time": 20.0},
    # 新一线
    "苏州": {"land_price": 4200, "salary_level": 11200, "energy_cost": 0.76, "financing_cost": 3.4, "local_support_rate": 80.0, "avg_delivery_time": 3.5, "location_quotient": 1.95, "tax_reduction": 26.0, "policy_coverage": 84.0, "tax_coverage": 84.0, "rd_subsidy": 13.0, "avg_approval_time": 16.0},
    "成都": {"land_price": 2800, "salary_level": 9200, "energy_cost": 0.62, "financing_cost": 4.2, "local_support_rate": 58.0, "avg_delivery_time": 5.5, "location_quotient": 1.05, "tax_reduction": 32.0, "policy_coverage": 90.0, "tax_coverage": 90.0, "rd_subsidy": 16.0, "avg_approval_time": 12.0},
    "杭州": {"land_price": 5500, "salary_level": 12500, "energy_cost": 0.80, "financing_cost": 3.1, "local_support_rate": 72.0, "avg_delivery_time": 4.2, "location_quotient": 1.55, "tax_reduction": 26.0, "policy_coverage": 86.0, "tax_coverage": 86.0, "rd_subsidy": 13.0, "avg_approval_time": 20.0},
    "武汉": {"land_price": 3200, "salary_level": 9800, "energy_cost": 0.68, "financing_cost": 4.0, "local_support_rate": 65.0, "avg_delivery_time": 5.0, "location_quotient": 1.20, "tax_reduction": 30.0, "policy_coverage": 88.0, "tax_coverage": 88.0, "rd_subsidy": 14.0, "avg_approval_time": 15.0},
    "南京": {"land_price": 5800, "salary_level": 12000, "energy_cost": 0.76, "financing_cost": 3.3, "local_support_rate": 70.0, "avg_delivery_time": 4.3, "location_quotient": 1.50, "tax_reduction": 27.0, "policy_coverage": 84.0, "tax_coverage": 84.0, "rd_subsidy": 12.0, "avg_approval_time": 22.0},
    "西安": {"land_price": 2600, "salary_level": 8500, "energy_cost": 0.65, "financing_cost": 4.4, "local_support_rate": 60.0, "avg_delivery_time": 6.0, "location_quotient": 1.20, "tax_reduction": 28.0, "policy_coverage": 86.0, "tax_coverage": 86.0, "rd_subsidy": 15.0, "avg_approval_time": 14.0},
    "重庆": {"land_price": 2400, "salary_level": 8800, "energy_cost": 0.60, "financing_cost": 4.3, "local_support_rate": 62.0, "avg_delivery_time": 5.8, "location_quotient": 1.10, "tax_reduction": 31.0, "policy_coverage": 85.0, "tax_coverage": 85.0, "rd_subsidy": 14.0, "avg_approval_time": 13.0},
    "天津": {"land_price": 3600, "salary_level": 10500, "energy_cost": 0.72, "financing_cost": 3.8, "local_support_rate": 68.0, "avg_delivery_time": 4.8, "location_quotient": 1.30, "tax_reduction": 25.0, "policy_coverage": 83.0, "tax_coverage": 83.0, "rd_subsidy": 11.0, "avg_approval_time": 21.0},
    "青岛": {"land_price": 3400, "salary_level": 10000, "energy_cost": 0.70, "financing_cost": 3.9, "local_support_rate": 66.0, "avg_delivery_time": 4.9, "location_quotient": 1.25, "tax_reduction": 26.0, "policy_coverage": 82.0, "tax_coverage": 82.0, "rd_subsidy": 11.0, "avg_approval_time": 19.0},
    "宁波": {"land_price": 3800, "salary_level": 10800, "energy_cost": 0.74, "financing_cost": 3.6, "local_support_rate": 72.0, "avg_delivery_time": 4.3, "location_quotient": 1.45, "tax_reduction": 24.0, "policy_coverage": 84.0, "tax_coverage": 84.0, "rd_subsidy": 12.0, "avg_approval_time": 18.0},
    "无锡": {"land_price": 4000, "salary_level": 10600, "energy_cost": 0.73, "financing_cost": 3.7, "local_support_rate": 74.0, "avg_delivery_time": 4.1, "location_quotient": 1.50, "tax_reduction": 25.0, "policy_coverage": 83.0, "tax_coverage": 83.0, "rd_subsidy": 12.0, "avg_approval_time": 17.0},
    "长沙": {"land_price": 2600, "salary_level": 9000, "energy_cost": 0.63, "financing_cost": 4.1, "local_support_rate": 64.0, "avg_delivery_time": 5.2, "location_quotient": 1.15, "tax_reduction": 29.0, "policy_coverage": 85.0, "tax_coverage": 85.0, "rd_subsidy": 13.0, "avg_approval_time": 15.0},
    "郑州": {"land_price": 2400, "salary_level": 8200, "energy_cost": 0.60, "financing_cost": 4.4, "local_support_rate": 58.0, "avg_delivery_time": 5.6, "location_quotient": 1.05, "tax_reduction": 30.0, "policy_coverage": 84.0, "tax_coverage": 84.0, "rd_subsidy": 12.0, "avg_approval_time": 14.0},
    "佛山": {"land_price": 3000, "salary_level": 9500, "energy_cost": 0.66, "financing_cost": 3.9, "local_support_rate": 68.0, "avg_delivery_time": 4.5, "location_quotient": 1.40, "tax_reduction": 24.0, "policy_coverage": 81.0, "tax_coverage": 81.0, "rd_subsidy": 10.0, "avg_approval_time": 17.0},
    "济南": {"land_price": 3100, "salary_level": 9400, "energy_cost": 0.67, "financing_cost": 4.0, "local_support_rate": 62.0, "avg_delivery_time": 5.0, "location_quotient": 1.15, "tax_reduction": 26.0, "policy_coverage": 82.0, "tax_coverage": 82.0, "rd_subsidy": 11.0, "avg_approval_time": 18.0},
    "合肥": {"land_price": 2900, "salary_level": 9300, "energy_cost": 0.65, "financing_cost": 4.0, "local_support_rate": 70.0, "avg_delivery_time": 4.8, "location_quotient": 1.35, "tax_reduction": 27.0, "policy_coverage": 85.0, "tax_coverage": 85.0, "rd_subsidy": 14.0, "avg_approval_time": 16.0},
    "福州": {"land_price": 3200, "salary_level": 9600, "energy_cost": 0.68, "financing_cost": 3.9, "local_support_rate": 65.0, "avg_delivery_time": 4.9, "location_quotient": 1.20, "tax_reduction": 23.0, "policy_coverage": 80.0, "tax_coverage": 80.0, "rd_subsidy": 10.0, "avg_approval_time": 19.0},
    "厦门": {"land_price": 4500, "salary_level": 10200, "energy_cost": 0.72, "financing_cost": 3.5, "local_support_rate": 72.0, "avg_delivery_time": 4.2, "location_quotient": 1.50, "tax_reduction": 22.0, "policy_coverage": 83.0, "tax_coverage": 83.0, "rd_subsidy": 12.0, "avg_approval_time": 18.0},
    "东莞": {"land_price": 2800, "salary_level": 9000, "energy_cost": 0.64, "financing_cost": 4.0, "local_support_rate": 70.0, "avg_delivery_time": 4.4, "location_quotient": 1.45, "tax_reduction": 23.0, "policy_coverage": 81.0, "tax_coverage": 81.0, "rd_subsidy": 11.0, "avg_approval_time": 16.0},
    # 二线 / 省会
    "昆明": {"land_price": 1800, "salary_level": 7200, "energy_cost": 0.55, "financing_cost": 4.6, "local_support_rate": 52.0, "avg_delivery_time": 6.5, "location_quotient": 0.90, "tax_reduction": 28.0, "policy_coverage": 78.0, "tax_coverage": 78.0, "rd_subsidy": 10.0, "avg_approval_time": 20.0},
    "沈阳": {"land_price": 1700, "salary_level": 7000, "energy_cost": 0.56, "financing_cost": 4.5, "local_support_rate": 50.0, "avg_delivery_time": 6.2, "location_quotient": 0.95, "tax_reduction": 27.0, "policy_coverage": 77.0, "tax_coverage": 77.0, "rd_subsidy": 9.0, "avg_approval_time": 21.0},
    "大连": {"land_price": 1900, "salary_level": 7400, "energy_cost": 0.58, "financing_cost": 4.4, "local_support_rate": 53.0, "avg_delivery_time": 6.0, "location_quotient": 1.00, "tax_reduction": 26.0, "policy_coverage": 78.0, "tax_coverage": 78.0, "rd_subsidy": 10.0, "avg_approval_time": 20.0},
    "哈尔滨": {"land_price": 1300, "salary_level": 6000, "energy_cost": 0.52, "financing_cost": 4.8, "local_support_rate": 45.0, "avg_delivery_time": 7.0, "location_quotient": 0.80, "tax_reduction": 29.0, "policy_coverage": 76.0, "tax_coverage": 76.0, "rd_subsidy": 8.0, "avg_approval_time": 23.0},
    "长春": {"land_price": 1400, "salary_level": 6200, "energy_cost": 0.53, "financing_cost": 4.7, "local_support_rate": 47.0, "avg_delivery_time": 6.8, "location_quotient": 0.85, "tax_reduction": 28.0, "policy_coverage": 77.0, "tax_coverage": 77.0, "rd_subsidy": 9.0, "avg_approval_time": 22.0},
    "石家庄": {"land_price": 1500, "salary_level": 6500, "energy_cost": 0.54, "financing_cost": 4.7, "local_support_rate": 48.0, "avg_delivery_time": 6.6, "location_quotient": 0.85, "tax_reduction": 27.0, "policy_coverage": 76.0, "tax_coverage": 76.0, "rd_subsidy": 8.0, "avg_approval_time": 22.0},
    "太原": {"land_price": 1600, "salary_level": 6800, "energy_cost": 0.56, "financing_cost": 4.5, "local_support_rate": 50.0, "avg_delivery_time": 6.2, "location_quotient": 0.90, "tax_reduction": 25.0, "policy_coverage": 75.0, "tax_coverage": 75.0, "rd_subsidy": 8.0, "avg_approval_time": 21.0},
    "南昌": {"land_price": 1750, "salary_level": 7000, "energy_cost": 0.57, "financing_cost": 4.5, "local_support_rate": 51.0, "avg_delivery_time": 6.3, "location_quotient": 0.90, "tax_reduction": 26.0, "policy_coverage": 77.0, "tax_coverage": 77.0, "rd_subsidy": 9.0, "avg_approval_time": 21.0},
    "贵阳": {"land_price": 1450, "salary_level": 6600, "energy_cost": 0.54, "financing_cost": 4.7, "local_support_rate": 49.0, "avg_delivery_time": 6.5, "location_quotient": 0.85, "tax_reduction": 28.0, "policy_coverage": 76.0, "tax_coverage": 76.0, "rd_subsidy": 9.0, "avg_approval_time": 22.0},
    "南宁": {"land_price": 1350, "salary_level": 6300, "energy_cost": 0.53, "financing_cost": 4.8, "local_support_rate": 47.0, "avg_delivery_time": 6.8, "location_quotient": 0.80, "tax_reduction": 29.0, "policy_coverage": 75.0, "tax_coverage": 75.0, "rd_subsidy": 8.0, "avg_approval_time": 23.0},
    "乌鲁木齐": {"land_price": 1200, "salary_level": 5800, "energy_cost": 0.50, "financing_cost": 4.9, "local_support_rate": 44.0, "avg_delivery_time": 7.2, "location_quotient": 0.75, "tax_reduction": 30.0, "policy_coverage": 74.0, "tax_coverage": 74.0, "rd_subsidy": 8.0, "avg_approval_time": 24.0},
    "兰州": {"land_price": 1100, "salary_level": 5600, "energy_cost": 0.49, "financing_cost": 5.0, "local_support_rate": 43.0, "avg_delivery_time": 7.3, "location_quotient": 0.75, "tax_reduction": 28.0, "policy_coverage": 74.0, "tax_coverage": 74.0, "rd_subsidy": 7.0, "avg_approval_time": 24.0},
}


def make_history(gdp_2024: float, growth_2024: float, pop_2024: float, fiscal_2024: float, rd_2024: float, hitech_2024: float, tier: dict):
    """生成 2020-2024 五年历史数据。"""
    # 假设 2020-2023 年复合增速逐步接近 2024 年增速
    gdp_2020 = round(gdp_2024 / ((1 + growth_2024 / 100) ** 4), 1)
    gdp_2021 = round(gdp_2020 * (1 + growth_2024 / 100), 1)
    gdp_2022 = round(gdp_2021 * (1 + growth_2024 / 100), 1)
    gdp_2023 = round(gdp_2022 * (1 + growth_2024 / 100), 1)

    pop_2020 = round(pop_2024 - 20, 1)
    pop_2021 = round(pop_2020 + 5, 1)
    pop_2022 = round(pop_2021 + 5, 1)
    pop_2023 = round(pop_2022 + 5, 1)

    fiscal_2020 = round(fiscal_2024 / ((1 + growth_2024 / 100) ** 4), 1)
    fiscal_2021 = round(fiscal_2020 * (1 + growth_2024 / 100), 1)
    fiscal_2022 = round(fiscal_2021 * (1 + growth_2024 / 100), 1)
    fiscal_2023 = round(fiscal_2022 * (1 + growth_2024 / 100), 1)

    base_row = {
        "land_price": tier["land_price"],
        "salary_level": tier["salary_level"],
        "energy_cost": tier["energy_cost"],
        "financing_cost": tier["financing_cost"],
        "local_support_rate": tier["local_support_rate"],
        "avg_delivery_time": tier["avg_delivery_time"],
        "location_quotient": tier["location_quotient"],
        "tax_reduction": tier["tax_reduction"],
        "policy_coverage": tier["policy_coverage"],
        "tax_coverage": tier["tax_coverage"],
        "rd_subsidy": tier["rd_subsidy"],
        "avg_approval_time": tier["avg_approval_time"],
    }

    rows = []
    for i, year in enumerate([2020, 2021, 2022, 2023, 2024]):
        gdp = [gdp_2020, gdp_2021, gdp_2022, gdp_2023, gdp_2024][i]
        pop = [pop_2020, pop_2021, pop_2022, pop_2023, pop_2024][i]
        fiscal = [fiscal_2020, fiscal_2021, fiscal_2022, fiscal_2023, fiscal_2024][i]
        rd_step = rd_2024 - (4 - i) * 0.1
        hitech_step = hitech_2024 - (4 - i) * 1.0
        rows.append(
            {
                "year": year,
                "gdp": gdp,
                "population": pop,
                "fiscal_revenue": fiscal,
                "rd_intensity": round(rd_step, 2),
                "industry_high_tech_ratio": round(hitech_step, 1),
                **base_row,
            }
        )
    return rows


def main() -> None:
    cities = []
    for spec in CITY_SPECS:
        code, name, province, parent_code, region, gdp, growth, pop, fiscal, rd, hitech, quality = spec
        tier = TIER_PARAMS[name]
        base = {
            "year": 2024,
            "gdp": gdp,
            "gdp_growth": growth,
            "population": pop,
            "fiscal_revenue": fiscal,
            "rd_intensity": rd,
            "industry_high_tech_ratio": hitech,
            "data_quality": quality,
            **tier,
        }
        history = make_history(gdp, growth, pop, fiscal, rd, hitech, tier)
        cities.append(build_city(code, name, province, parent_code, region, base, history))

    doc = {
        "_meta": {
            "version": "2025.06.1",
            "last_updated": "2025-06-17",
            "city_count": len(cities),
            "sources": [
                {"name": "国家统计局", "url": "http://www.stats.gov.cn", "coverage": "全国"},
                {"name": "各城市统计局 2020-2024 统计公报", "coverage": "城市级"},
            ],
            "update_frequency": "年度",
            "license": "CC-BY-SA-4.0 / 内部使用",
            "note": "商业成本、政策环境类字段为 Urban Pulse 模型估算，生产环境应接入官方或调研数据源。",
        },
        "score_weights": {
            "business_cost": 0.3,
            "supply_chain": 0.25,
            "policy_benefit": 0.15,
            "talent_pool": 0.15,
            "innovation": 0.1,
            "infrastructure": 0.05,
        },
        "cities": cities,
    }

    target = Path(__file__).parents[1] / "data" / "cities" / "cities.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)
    print(f"Generated {target} with {len(cities)} cities")


if __name__ == "__main__":
    main()
