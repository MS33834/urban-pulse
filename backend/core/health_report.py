"""CEHI PDF 诊断报告生成器。

使用 reportlab 构建 PDF，使用 matplotlib 绘制雷达图。
中文字体优先使用系统自带 CJK 字体，不存在时降级为默认字体并对中文做 ASCII 占位。
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from backend.core.health_index import CEHIResult

logger = logging.getLogger(__name__)

matplotlib.use("Agg")


# 常见系统自带中文字体候选路径
_CJK_FONT_CANDIDATES = [
    Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
    Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
    Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttf"),
    Path("/usr/share/fonts/truetype/arphic/uming.ttc"),
    Path("/usr/share/fonts/truetype/arphic/ukai.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansSC-Regular.otf"),
    Path("/usr/share/fonts/truetype/liberation/simhei.ttf"),
    Path("/System/Library/Fonts/PingFang.ttc"),
    Path("/System/Library/Fonts/STHeiti Light.ttc"),
    Path("/Windows/Fonts/simhei.ttf"),
    Path("/Windows/Fonts/msyh.ttc"),
    Path("/Windows/Fonts/simsun.ttc"),
]


class _FontHelper:
    """中文字体辅助类：自动发现并注册系统 CJK 字体，不存在时降级为默认字体。"""

    def __init__(self) -> None:
        self.cjk_path: Path | None = self._find_cjk_font()
        self.has_cjk: bool = self.cjk_path is not None
        self.font_name: str = "Helvetica"
        self.bold_font_name: str = "Helvetica-Bold"
        self._register()

    def _find_cjk_font(self) -> Path | None:
        for candidate in _CJK_FONT_CANDIDATES:
            if candidate.exists():
                return candidate
        return None

    def _register(self) -> None:
        if not self.cjk_path:
            logger.warning("未找到系统中文字体，PDF 中的中文将使用 ASCII 占位符")
            return
        try:
            font_name = "CEHIFont"
            pdfmetrics.registerFont(TTFont(font_name, str(self.cjk_path)))
            self.font_name = font_name
            self.bold_font_name = font_name
        except Exception:
            logger.exception("注册中文字体失败，将使用默认字体")
            self.cjk_path = None
            self.has_cjk = False

    def text(self, s: str | None) -> str:
        """返回可在当前字体下安全渲染的文本。

        存在 CJK 字体时原样返回；否则将 CJK 字符替换为 ``[?]`` 占位符。
        """
        if s is None:
            return ""
        if self.has_cjk:
            return s
        # 基础 ASCII 占位：连续 CJK 字符替换为 [?]
        return re.sub(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+", "[?]", s)

    def paragraph_style(
        self, name: str, *, size: int, bold: bool = False, color: colors.Color = colors.black
    ) -> ParagraphStyle:
        return ParagraphStyle(
            name,
            fontName=self.bold_font_name if bold else self.font_name,
            fontSize=size,
            leading=size * 1.3,
            textColor=color,
        )


FONT = _FontHelper()


def _radar_chart_bytes(result: CEHIResult, width: float = 14 * cm, height: float = 10 * cm) -> bytes:
    """使用 matplotlib 生成六大维度雷达图 PNG 字节流。"""
    dimensions = result.dimension_scores
    labels = [FONT.text(ds.dimension.name) for ds in dimensions]
    values = [ds.score for ds in dimensions]

    # 闭合雷达图数据
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    values_closed = values + values[:1]
    angles_closed = angles + angles[:1]

    fig, ax = plt.subplots(figsize=(width / cm * 1.5, height / cm * 1.5), subplot_kw=dict(polar=True))
    ax.plot(angles_closed, values_closed, color="#D08560", linewidth=2)
    ax.fill(angles_closed, values_closed, color="#D08560", alpha=0.25)
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.set_title(FONT.text(f"{result.city_name} · {result.year} CEHI 雷达图"), fontsize=14, pad=20)

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _make_table(data: list[list[Any]], col_widths: list[float], style: TableStyle | None = None) -> Table:
    """创建 reportlab 表格，并应用默认样式。"""
    table = Table(data, colWidths=col_widths)
    default_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0E1F3F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, 0), FONT.bold_font_name),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FAF8F3")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CDD6E0")),
        ("FONTNAME", (0, 1), (-1, -1), FONT.font_name),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
    ]
    table.setStyle(TableStyle(default_style + (style.getCommands() if style else [])))  # type: ignore[arg-type]
    return table


def _indicator_rows(items: list[Any], *, with_contribution: bool = True) -> list[list[str]]:
    """将指标评分列表转换为表格行数据。"""
    rows: list[list[str]] = []
    for it in items:
        indicator = asdict(it.indicator)
        name = FONT.text(indicator.get("name", ""))
        dimension = FONT.text(indicator.get("dimension_id", ""))
        unit = FONT.text(indicator.get("unit", ""))
        raw_value = it.raw_value
        value_str = f"{raw_value}{unit}" if raw_value is not None else "N/A"
        score = f"{it.score:.1f}"
        status = FONT.text(it.status_name)
        row = [name, dimension, value_str, score, status]
        if with_contribution:
            row.append(f"{it.contribution:+.2f}")
        rows.append(row)
    return rows


def generate_cehi_pdf(result: CEHIResult) -> bytes:
    """根据 CEHI 计算结果生成 PDF 诊断报告，返回文件二进制内容。"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    title_style = FONT.paragraph_style("Title", size=24, bold=True, color=colors.HexColor("#0E1F3F"))
    subtitle_style = FONT.paragraph_style("Subtitle", size=14, color=colors.HexColor("#4B6B8C"))
    section_style = FONT.paragraph_style("Section", size=16, bold=True, color=colors.HexColor("#0E1F3F"))
    body_style = FONT.paragraph_style("Body", size=10, color=colors.HexColor("#1A1A1A"))
    score_style = FONT.paragraph_style("Score", size=48, bold=True, color=colors.HexColor("#D08560"))

    story: list[Any] = []

    # ------------------------------------------------------------------ #
    # 第一页：标题页
    # ------------------------------------------------------------------ #
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph(FONT.text("城市经济发展健康水平指数"), title_style))
    story.append(Paragraph(FONT.text("CEHI 诊断报告"), title_style))
    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph(FONT.text(f"{result.city_name} · {result.year}"), subtitle_style))
    story.append(Spacer(1, 2 * cm))

    score_text = f"{result.total_score:.1f}"
    story.append(Paragraph(score_text, score_style))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            FONT.text(f"健康等级：{result.status_name} {result.level.emoji}"),
            FONT.paragraph_style("Level", size=14, bold=True, color=colors.HexColor(result.level.color or "#0E1F3F")),
        )
    )
    story.append(Spacer(1, 2 * cm))
    story.append(
        Paragraph(
            FONT.text(result.level.description),
            body_style,
        )
    )
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(FONT.text(f"报告生成时间：{result.year}"), body_style))

    story.append(Spacer(1, 1.5 * cm))

    # 摘要指标
    summary_data = [
        [FONT.text("维度数"), FONT.text("指标数"), FONT.text("主要短板数"), FONT.text("主要优势数")],
        [
            str(len(result.dimension_scores)),
            str(sum(len(ds.indicator_scores) for ds in result.dimension_scores)),
            str(len(result.top_weaknesses)),
            str(len(result.top_strengths)),
        ],
    ]
    story.append(_make_table(summary_data, [3.5 * cm, 3.5 * cm, 3.5 * cm, 3.5 * cm]))

    story.append(Spacer(1, 1.5 * cm))
    story.append(PageBreak())

    # ------------------------------------------------------------------ #
    # 第二页：雷达图 + 维度得分表
    # ------------------------------------------------------------------ #
    story.append(Paragraph(FONT.text("一、六大维度雷达图"), section_style))
    story.append(Spacer(1, 0.5 * cm))

    radar_bytes = _radar_chart_bytes(result)
    radar_img = Image(io.BytesIO(radar_bytes), width=14 * cm, height=10 * cm)
    story.append(radar_img)

    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph(FONT.text("二、维度得分明细"), section_style))
    story.append(Spacer(1, 0.4 * cm))

    dim_data = [[FONT.text("维度"), FONT.text("得分"), FONT.text("状态"), FONT.text("权重")]]
    for ds in result.dimension_scores:
        dim_data.append(
            [
                FONT.text(ds.dimension.name),
                f"{ds.score:.1f}",
                FONT.text(ds.status_name),
                f"{ds.weight:.2f}",
            ]
        )
    story.append(_make_table(dim_data, [7 * cm, 3 * cm, 3 * cm, 2.5 * cm]))

    story.append(PageBreak())

    # ------------------------------------------------------------------ #
    # 第三页：短板指标 + 优势指标
    # ------------------------------------------------------------------ #
    story.append(Paragraph(FONT.text("三、主要短板指标"), section_style))
    story.append(Spacer(1, 0.4 * cm))
    if result.top_weaknesses:
        weak_header = [
            FONT.text("指标"),
            FONT.text("维度"),
            FONT.text("原始值"),
            FONT.text("得分"),
            FONT.text("状态"),
            FONT.text("贡献度"),
        ]
        weak_data = [weak_header] + _indicator_rows(result.top_weaknesses)
        story.append(_make_table(weak_data, [4 * cm, 2.5 * cm, 2.5 * cm, 1.8 * cm, 2 * cm, 2.2 * cm]))
    else:
        story.append(Paragraph(FONT.text("暂无显著短板指标。"), body_style))

    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph(FONT.text("四、主要优势指标"), section_style))
    story.append(Spacer(1, 0.4 * cm))
    if result.top_strengths:
        strong_header = [
            FONT.text("指标"),
            FONT.text("维度"),
            FONT.text("原始值"),
            FONT.text("得分"),
            FONT.text("状态"),
            FONT.text("贡献度"),
        ]
        strong_data = [strong_header] + _indicator_rows(result.top_strengths)
        story.append(_make_table(strong_data, [4 * cm, 2.5 * cm, 2.5 * cm, 1.8 * cm, 2 * cm, 2.2 * cm]))
    else:
        story.append(Paragraph(FONT.text("暂无显著优势指标。"), body_style))

    story.append(PageBreak())

    # ------------------------------------------------------------------ #
    # 第四页：改进建议
    # ------------------------------------------------------------------ #
    story.append(Paragraph(FONT.text("五、改进建议"), section_style))
    story.append(Spacer(1, 0.4 * cm))
    if result.recommendations:
        for i, rec in enumerate(result.recommendations, 1):
            story.append(Paragraph(f"{i}. {FONT.text(rec)}", body_style))
            story.append(Spacer(1, 0.2 * cm))
    else:
        story.append(Paragraph(FONT.text("暂无建议。"), body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
