"""
区位商（Location Quotient, LQ）模型

用于识别地区专业化产业与比较优势。
参考：mathmodels-book 区域经济；地理学报《中国物流集群量化甄别》
"""

from __future__ import annotations

from typing import Any

import pandas as pd


class LocationQuotientModel:
    """
    区位商模型：
        LQ_ij = (e_ij / e_i) / (E_j / E)
    其中：
        e_ij = 地区 i 产业 j 的就业/产值
        e_i = 地区 i 总就业/产值
        E_j = 全国产业 j 总就业/产值
        E = 全国总就业/产值
    """

    def __init__(self, region_col: str = "region", industry_col: str = "industry", value_col: str = "value"):
        self.region_col = region_col
        self.industry_col = industry_col
        self.value_col = value_col

    def run(self, df: pd.DataFrame) -> dict[str, Any]:
        data = df[[self.region_col, self.industry_col, self.value_col]].dropna().copy()

        # 全国产业总计
        national_industry = data.groupby(self.industry_col)[self.value_col].sum()
        national_total = data[self.value_col].sum()

        # 地区总计
        region_total = data.groupby(self.region_col)[self.value_col].sum()

        results = []
        for _, row in data.iterrows():
            region = row[self.region_col]
            industry = row[self.industry_col]
            value = row[self.value_col]

            region_share = value / region_total[region] if region_total[region] > 0 else 0
            national_share = national_industry[industry] / national_total if national_total > 0 else 0
            lq = region_share / national_share if national_share > 0 else 0

            interpretation = ""
            if lq > 1.5:
                interpretation = "高度专业化（出口型/优势产业）"
            elif lq > 1.0:
                interpretation = "专业化程度高于全国平均"
            elif lq > 0.5:
                interpretation = "专业化程度一般"
            else:
                interpretation = "非主导产业"

            results.append({
                "region": region,
                "industry": industry,
                "value": float(value),
                "location_quotient": round(lq, 4),
                "interpretation": interpretation,
            })

        # 按区位商排序
        results.sort(key=lambda x: x["location_quotient"], reverse=True)

        return {
            "model": "Location_Quotient",
            "region_col": self.region_col,
            "industry_col": self.industry_col,
            "value_col": self.value_col,
            "results": results,
            "summary": {
                "total_regions": data[self.region_col].nunique(),
                "total_industries": data[self.industry_col].nunique(),
                "advantageous_industries": len([r for r in results if r["location_quotient"] > 1.0]),
            },
        }
