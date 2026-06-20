"""倪鹏飞弓弦箭模型 — 城市竞争力指标体系定义

硬竞争力（8 分力）：
  人才力、资本力、科技力、结构力、区位力、设施力、环境力、聚集力
软竞争力（5 分力）：
  秩序力、文化力、制度力、管理力、开放力

根据现有数据覆盖情况，映射 19 个指标到有数据的维度。
缺失维度标记为 data_missing=True，供前端展示。
"""

from __future__ import annotations

from typing import Any

Indicator = dict[str, Any]
DimensionDef = dict[str, Any]


class IndicatorFramework:
    """指标体系定义 — 倪鹏飞弓弦箭模型"""

    # ── 硬竞争力（8 分力）──
    HARD_DIMENSIONS: list[DimensionDef] = [
        {
            "name": "资本力",
            "type": "hard",
            "label": "Capital Power",
            "description": "城市经济规模与财政实力",
            "data_missing": False,
            "indicators": ["gdp", "fiscal_revenue", "gdp_growth"],
        },
        {
            "name": "科技力",
            "type": "hard",
            "label": "Technology Power",
            "description": "研发投入与创新产出水平",
            "data_missing": False,
            "indicators": ["rd_intensity", "industry_high_tech_ratio", "rd_subsidy"],
        },
        {
            "name": "聚集力",
            "type": "hard",
            "label": "Agglomeration Power",
            "description": "人口规模与产业供应链集聚程度",
            "data_missing": False,
            "indicators": ["population", "supplier_count"],
        },
        {
            "name": "区位力",
            "type": "hard",
            "label": "Location Power",
            "description": "城市地理区位价值",
            "data_missing": False,
            "indicators": ["land_price"],
        },
        {
            "name": "人才力",
            "type": "hard",
            "label": "Talent Power",
            "description": "人才吸引力与劳动力质量",
            "data_missing": False,
            "indicators": ["salary_level"],
        },
        {
            "name": "设施力",
            "type": "hard",
            "label": "Infrastructure Power",
            "description": "基础设施与运营成本水平",
            "data_missing": False,
            "indicators": ["energy_cost"],
        },
        # 以下分力无数据覆盖
        {
            "name": "结构力",
            "type": "hard",
            "label": "Structural Power",
            "description": "产业结构优化升级水平",
            "data_missing": True,
            "indicators": [],
        },
        {
            "name": "环境力",
            "type": "hard",
            "label": "Environmental Power",
            "description": "城市生态环境质量",
            "data_missing": True,
            "indicators": [],
        },
    ]

    # ── 软竞争力（5 分力）──
    SOFT_DIMENSIONS: list[DimensionDef] = [
        {
            "name": "制度力",
            "type": "soft",
            "label": "Institutional Power",
            "description": "政策支持与制度环境",
            "data_missing": False,
            "indicators": ["local_support_rate", "policy_coverage", "tax_coverage"],
        },
        {
            "name": "管理力",
            "type": "soft",
            "label": "Management Power",
            "description": "政府管理效率与服务能力",
            "data_missing": False,
            "indicators": ["avg_approval_time", "tax_reduction"],
        },
        # 以下分力无数据覆盖
        {
            "name": "秩序力",
            "type": "soft",
            "label": "Order Power",
            "description": "社会治理与法治水平",
            "data_missing": True,
            "indicators": [],
        },
        {
            "name": "文化力",
            "type": "soft",
            "label": "Cultural Power",
            "description": "城市文化影响力",
            "data_missing": True,
            "indicators": [],
        },
        {
            "name": "开放力",
            "type": "soft",
            "label": "Openness Power",
            "description": "对外经济开放程度",
            "data_missing": True,
            "indicators": [],
        },
    ]

    # ── 指标定义 ──
    # name: 中文名, key: 数据键名, direction: 正向（越大越好）/ 逆向（越小越好）/ 双向（适中最好）
    # weight: 默认权重（等权，后续被熵权法覆盖）
    ALL_INDICATORS: dict[str, Indicator] = {
        # === 资本力 ===
        "gdp": {
            "name": "GDP",
            "key": "gdp",
            "direction": "positive",
            "weight": 1.0 / 19,
            "unit": "亿元",
            "description": "地区生产总值",
        },
        "fiscal_revenue": {
            "name": "财政收入",
            "key": "fiscal_revenue",
            "direction": "positive",
            "weight": 1.0 / 19,
            "unit": "亿元",
            "description": "地方一般公共预算收入",
        },
        "gdp_growth": {
            "name": "GDP增速",
            "key": "gdp_growth",
            "direction": "positive",
            "weight": 1.0 / 19,
            "unit": "%",
            "description": "地区生产总值实际增长率",
        },
        # === 科技力 ===
        "rd_intensity": {
            "name": "研发投入强度",
            "key": "rd_intensity",
            "direction": "positive",
            "weight": 1.0 / 19,
            "unit": "%",
            "description": "R&D 经费占 GDP 比重",
        },
        "industry_high_tech_ratio": {
            "name": "高新技术产业占比",
            "key": "industry_high_tech_ratio",
            "direction": "positive",
            "weight": 1.0 / 19,
            "unit": "%",
            "description": "高新技术产业产值占工业总产值比重",
        },
        "rd_subsidy": {
            "name": "研发补贴力度",
            "key": "rd_subsidy",
            "direction": "positive",
            "weight": 1.0 / 19,
            "unit": "亿元",
            "description": "政府对研发的直接补贴金额",
        },
        # === 聚集力 ===
        "population": {
            "name": "人口规模",
            "key": "population",
            "direction": "positive",
            "weight": 1.0 / 19,
            "unit": "万人",
            "description": "常住人口",
        },
        "supplier_count": {
            "name": "供应商数量",
            "key": "supplier_count",
            "direction": "positive",
            "weight": 1.0 / 19,
            "unit": "家",
            "description": "产业链上游供应商数量",
        },
        # === 区位力 ===
        "land_price": {
            "name": "土地价格",
            "key": "land_price",
            "direction": "bidirectional",
            "weight": 1.0 / 19,
            "unit": "元/㎡",
            "description": "工业用地均价。城市竞争力语境下高说明区位值钱，企业选址语境下是成本。",
        },
        # === 人才力 ===
        "salary_level": {
            "name": "薪资水平",
            "key": "salary_level",
            "direction": "bidirectional",
            "weight": 1.0 / 19,
            "unit": "元/月",
            "description": "平均薪资。城市竞争力语境下高说明人才吸引力强，企业成本语境下是负担。",
        },
        # === 设施力 ===
        "energy_cost": {
            "name": "能源成本",
            "key": "energy_cost",
            "direction": "negative",
            "weight": 1.0 / 19,
            "unit": "元/千瓦时",
            "description": "工业用电价格，越低竞争力越强",
        },
        # === 制度力 ===
        "local_support_rate": {
            "name": "地方支持率",
            "key": "local_support_rate",
            "direction": "positive",
            "weight": 1.0 / 19,
            "unit": "%",
            "description": "地方政府对产业的支持力度评分",
        },
        "policy_coverage": {
            "name": "政策覆盖面",
            "key": "policy_coverage",
            "direction": "positive",
            "weight": 1.0 / 19,
            "unit": "%",
            "description": "产业扶持政策的覆盖范围",
        },
        "tax_coverage": {
            "name": "税收优惠覆盖面",
            "key": "tax_coverage",
            "direction": "positive",
            "weight": 1.0 / 19,
            "unit": "%",
            "description": "税收优惠政策覆盖企业比例",
        },
        # === 管理力 ===
        "avg_approval_time": {
            "name": "平均审批时间",
            "key": "avg_approval_time",
            "direction": "negative",
            "weight": 1.0 / 19,
            "unit": "天",
            "description": "企业开办/项目审批平均用时，越短竞争力越强",
        },
        "tax_reduction": {
            "name": "减税力度",
            "key": "tax_reduction",
            "direction": "positive",
            "weight": 1.0 / 19,
            "unit": "%",
            "description": "实际减税降费力度评分",
        },
    }

    # ── 已有数据的指标键列表 ──
    COVERED_INDICATOR_KEYS: list[str] = [
        "gdp",
        "fiscal_revenue",
        "gdp_growth",
        "rd_intensity",
        "industry_high_tech_ratio",
        "rd_subsidy",
        "population",
        "supplier_count",
        "land_price",
        "salary_level",
        "energy_cost",
        "local_support_rate",
        "policy_coverage",
        "tax_coverage",
        "avg_approval_time",
        "tax_reduction",
    ]

    @classmethod
    def get_all_indicators(cls) -> dict[str, Indicator]:
        """返回所有指标定义（含 name / key / direction / weight / unit / description）"""
        return dict(cls.ALL_INDICATORS)

    @classmethod
    def get_covered_indicators(cls) -> dict[str, Indicator]:
        """返回有数据覆盖的指标定义"""
        return {k: v for k, v in cls.ALL_INDICATORS.items() if k in cls.COVERED_INDICATOR_KEYS}

    @classmethod
    def get_dimension_mapping(cls) -> list[DimensionDef]:
        """返回维度→指标的映射

        Returns:
            list[dict]: 每个元素包含 name, type, label, description, data_missing, indicators
        """
        return cls.HARD_DIMENSIONS + cls.SOFT_DIMENSIONS

    @classmethod
    def get_direction(cls, key: str) -> str:
        """返回指标方向: positive / negative / bidirectional

        Args:
            key: 指标键名

        Returns:
            方向字符串，未知指标默认返回 "positive"
        """
        indicator = cls.ALL_INDICATORS.get(key)
        if indicator is None:
            return "positive"
        return str(indicator["direction"])

    @classmethod
    def get_missing_dimensions(cls) -> list[DimensionDef]:
        """返回无数据覆盖的维度列表"""
        all_dims = cls.HARD_DIMENSIONS + cls.SOFT_DIMENSIONS
        return [d for d in all_dims if d.get("data_missing", False)]

    @classmethod
    def get_data_dimensions(cls) -> list[DimensionDef]:
        """返回有数据覆盖的维度列表"""
        all_dims = cls.HARD_DIMENSIONS + cls.SOFT_DIMENSIONS
        return [d for d in all_dims if not d.get("data_missing", False)]
