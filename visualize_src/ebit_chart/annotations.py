"""Подписи среднего/медианы и информационные карточки."""

from __future__ import annotations

from typing import Literal

from matplotlib.axes import Axes

from .config import ChartLayout, ChartTheme
from .data import YearDistribution, format_money

LabelSide = Literal["left", "right"]


def pixels_to_points(axes: Axes, pixels: float) -> float:
    """Переводит экранные пиксели в типографские пункты Matplotlib."""
    return pixels * 72.0 / axes.figure.dpi


def stat_label_sides(
    mean_position: float,
    median_position: float,
) -> tuple[LabelSide, LabelSide]:
    """
    Возвращает стороны для (mean, median).

    Большая статистика получает бокс справа от своей линии,
    меньшая — слева. При равенстве медиана остаётся слева,
    среднее справа, чтобы подписи не накладывались друг на друга.
    """
    if median_position > mean_position:
        return "left", "right"
    return "right", "left"


def text_anchor_offset(
    *,
    axes: Axes,
    side: LabelSide,
    edge_gap_pixels: float,
    layout: ChartLayout,
) -> tuple[float, str]:
    """Ставит внешнюю грань бокса ровно на заданном расстоянии от линии."""
    gap_points = pixels_to_points(axes, edge_gap_pixels)
    offset = gap_points + layout.label_padding_points

    if side == "right":
        return offset, "left"
    return -offset, "right"


def draw_stat_label(
    *,
    axes: Axes,
    x_line: float,
    y_level: float,
    title: str,
    value: float,
    color: str,
    side: LabelSide,
    theme: ChartTheme,
    layout: ChartLayout,
) -> None:
    """Рисует компактную двухстрочную подпись статистики."""
    anchor_offset, horizontal_alignment = text_anchor_offset(
        axes=axes,
        side=side,
        edge_gap_pixels=layout.label_edge_gap_pixels,
        layout=layout,
    )

    axes.annotate(
        f"{title}\n{format_money(value)}",
        xy=(x_line, y_level),
        xycoords="data",
        xytext=(anchor_offset, 0),
        textcoords="offset points",
        ha=horizontal_alignment,
        va="center",
        fontsize=layout.label_font_size,
        color=color,
        fontfamily=theme.font_family,
        fontweight=theme.emphasis_weight,
        linespacing=1.02,
        bbox={
            "boxstyle": (
                f"round,pad={layout.label_box_pad},"
                "rounding_size=0.14"
            ),
            "facecolor": theme.surface,
            "edgecolor": color,
            "linewidth": 0.72,
            "alpha": 0.985,
        },
        annotation_clip=False,
        zorder=8,
    )


def draw_stat_annotations(
    *,
    axes: Axes,
    distribution: YearDistribution,
    theme: ChartTheme,
    layout: ChartLayout,
) -> None:
    """Рисует обе подписи на одной высоте с точной привязкой 20 px."""
    mean_side, median_side = stat_label_sides(
        distribution.mean_position,
        distribution.median_position,
    )
    label_y = (
        distribution.base_y
        + layout.ridge_height * layout.label_height_ratio
    )

    draw_stat_label(
        axes=axes,
        x_line=distribution.median_position,
        y_level=label_y,
        title="Медиана",
        value=distribution.median_value,
        color=theme.median,
        side=median_side,
        theme=theme,
        layout=layout,
    )
    draw_stat_label(
        axes=axes,
        x_line=distribution.mean_position,
        y_level=label_y,
        title="Среднее",
        value=distribution.mean_value,
        color=theme.mean,
        side=mean_side,
        theme=theme,
        layout=layout,
    )


def draw_company_card(
    *,
    axes: Axes,
    distribution: YearDistribution,
    x_position: float,
    theme: ChartTheme,
    layout: ChartLayout,
) -> None:
    """Рисует правую карточку с числом компаний и долей отрицательного EBIT."""
    axes.text(
        x_position,
        distribution.base_y + layout.ridge_height * 0.43,
        (
            f"{distribution.company_count} компаний\n"
            f"{distribution.negative_share:.1f}% с EBIT < 0"
        ),
        ha="left",
        va="center",
        fontsize=8.75,
        color=theme.muted_text,
        fontfamily=theme.font_family,
        fontweight=theme.regular_weight,
        linespacing=1.25,
        bbox={
            "boxstyle": "round,pad=0.43,rounding_size=0.14",
            "facecolor": theme.surface,
            "edgecolor": theme.card_border,
            "linewidth": 0.68,
            "alpha": 0.965,
        },
        clip_on=False,
        zorder=7,
    )
