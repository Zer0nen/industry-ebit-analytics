"""Низкоуровневая отрисовка ridgeline и оформление Figure/Axes."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from .annotations import draw_company_card, draw_stat_annotations
from .config import ChartLayout, ChartTheme
from .data import YearDistribution, money_ticks_and_labels, signed_log10


def create_figure(
    *,
    year_count: int,
    theme: ChartTheme,
    layout: ChartLayout,
) -> tuple[Figure, Axes]:
    """Создаёт Figure с адаптивной высотой."""
    figure, axes = plt.subplots(
        figsize=(
            layout.figure_width,
            layout.figure_height(year_count),
        ),
        dpi=layout.screen_dpi,
    )
    figure.patch.set_facecolor(theme.background)
    axes.set_facecolor(theme.background)
    return figure, axes


def configure_geometry(
    *,
    figure: Figure,
    axes: Axes,
    left_limit: float,
    right_limit: float,
    year_count: int,
    theme: ChartTheme,
    layout: ChartLayout,
) -> None:
    """Фиксирует геометрию до пиксельных расчётов подписей."""
    figure.subplots_adjust(
        left=layout.left_margin,
        right=layout.right_margin,
        top=layout.top_margin,
        bottom=layout.bottom_margin,
    )
    axes.set_xlim(
        -left_limit,
        right_limit + layout.right_annotation_space,
    )
    axes.set_ylim(
        -0.12,
        year_count - 1 + layout.ridge_height + 0.48,
    )
    figure.canvas.draw()


def draw_year(
    *,
    axes: Axes,
    x_grid: np.ndarray,
    distribution: YearDistribution,
    color_index: int,
    right_limit: float,
    left_limit: float,
    theme: ChartTheme,
    layout: ChartLayout,
) -> None:
    """Рисует одну ridgeline-полосу со статистиками и карточкой."""
    fill_color = theme.ridge_fills[
        min(color_index, len(theme.ridge_fills) - 1)
    ]
    edge_color = theme.ridge_edges[
        min(color_index, len(theme.ridge_edges) - 1)
    ]
    base_y = distribution.base_y

    axes.hlines(
        base_y,
        -left_limit,
        right_limit,
        color=theme.baseline,
        linewidth=0.82,
        zorder=1,
    )
    axes.fill_between(
        x_grid,
        base_y,
        base_y + distribution.density,
        color=fill_color,
        alpha=0.92,
        linewidth=0,
        zorder=2,
    )
    axes.plot(
        x_grid,
        base_y + distribution.density,
        color=edge_color,
        linewidth=1.42,
        solid_capstyle="round",
        zorder=3,
    )

    axes.vlines(
        distribution.mean_position,
        base_y,
        base_y + distribution.mean_height,
        color=theme.mean,
        linewidth=2.35,
        zorder=5,
    )
    axes.vlines(
        distribution.median_position,
        base_y,
        base_y + distribution.median_height,
        color=theme.median,
        linewidth=2.35,
        linestyles=(0, (4, 2.4)),
        zorder=5,
    )

    draw_stat_annotations(
        axes=axes,
        distribution=distribution,
        theme=theme,
        layout=layout,
    )
    draw_company_card(
        axes=axes,
        distribution=distribution,
        x_position=right_limit + 0.18,
        theme=theme,
        layout=layout,
    )


def style_axes(
    *,
    axes: Axes,
    years: list[object],
    left_limit: float,
    right_limit: float,
    theme: ChartTheme,
    layout: ChartLayout,
) -> None:
    """Настраивает шкалы, сетку, тики и легенду."""
    axes.axvline(
        0,
        color=theme.zero_line,
        linestyle=(0, (1.2, 2.4)),
        linewidth=1.05,
        zorder=1,
    )

    axes.set_yticks(range(len(years)))
    axes.set_yticklabels(
        years,
        fontsize=12.0,
        fontfamily=theme.font_family,
        fontweight=theme.emphasis_weight,
        color=theme.text,
    )

    money_values, money_labels = money_ticks_and_labels()
    positions = signed_log10(money_values)
    visible_ticks = [
        (position, label)
        for position, label in zip(positions, money_labels)
        if -left_limit <= position <= right_limit
    ]
    axes.set_xticks([position for position, _ in visible_ticks])
    axes.set_xticklabels(
        [label for _, label in visible_ticks],
        fontsize=9.9,
        color=theme.muted_text,
        fontfamily=theme.font_family,
    )

    axes.set_xlabel(
        "EBIT компании",
        fontsize=11.1,
        labelpad=14,
        color=theme.text,
        fontfamily=theme.font_family,
    )
    axes.set_ylabel("")
    axes.grid(
        axis="x",
        color=theme.grid,
        linewidth=0.76,
        alpha=0.68,
    )
    axes.set_axisbelow(True)

    for spine in axes.spines.values():
        spine.set_visible(False)

    axes.tick_params(axis="y", length=0, pad=12)
    axes.tick_params(axis="x", length=0, pad=8)

    legend_elements = [
        Line2D(
            [0],
            [0],
            color=theme.mean,
            linewidth=2.35,
            label="Среднее",
        ),
        Line2D(
            [0],
            [0],
            color=theme.median,
            linewidth=2.35,
            linestyle=(0, (4, 2.4)),
            label="Медиана",
        ),
    ]
    legend = axes.legend(
        handles=legend_elements,
        loc="upper left",
        bbox_to_anchor=(0, 1.03),
        frameon=True,
        fancybox=True,
        framealpha=0.97,
        facecolor=theme.surface,
        edgecolor=theme.card_border,
        borderpad=0.5,
        ncols=2,
        fontsize=9.7,
        handlelength=2.8,
        columnspacing=1.7,
    )
    legend.get_frame().set_linewidth(0.65)
    for text_item in legend.get_texts():
        text_item.set_fontfamily(theme.font_family)


def add_figure_text(
    *,
    figure: Figure,
    theme: ChartTheme,
    layout: ChartLayout,
) -> None:
    """Добавляет заголовок, подзаголовок, акцент и примечание."""
    figure.text(
        layout.title_x,
        layout.title_y,
        "Распределение EBIT по годам",
        ha="left",
        va="top",
        fontsize=22.5,
        fontfamily=theme.font_family,
        fontweight=theme.emphasis_weight,
        color=theme.text,
    )
    figure.text(
        layout.title_x,
        layout.subtitle_y,
        "Распределение компаний; линии показывают среднее и медиану",
        ha="left",
        va="top",
        fontsize=10.35,
        fontfamily=theme.font_family,
        color=theme.muted_text,
    )
    figure.text(
        layout.title_x,
        layout.footnote_y,
        (
            "Примечание: ось X использует симметричное логарифмическое "
            "преобразование EBIT. Исходные данные — тыс. рублей."
        ),
        ha="left",
        va="bottom",
        fontsize=8.35,
        fontfamily=theme.font_family,
        color=theme.muted_text,
    )
    figure.add_artist(
        Line2D(
            [layout.title_x, layout.title_x + 0.067],
            [layout.accent_y, layout.accent_y],
            transform=figure.transFigure,
            color=theme.median,
            linewidth=2.8,
            solid_capstyle="round",
        )
    )


def save_figure(
    *,
    figure: Figure,
    output_path: str | None,
    layout: ChartLayout,
) -> None:
    """Сохраняет график и при необходимости создаёт родительскую папку."""
    if output_path is None:
        return

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(
        path,
        dpi=layout.save_dpi,
        bbox_inches="tight",
        facecolor=figure.get_facecolor(),
    )
