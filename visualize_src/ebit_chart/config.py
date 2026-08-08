"""Визуальные настройки ridgeline-графика EBIT."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChartTheme:
    """Палитра и типографика графика."""

    background: str = "#F6F7F3"
    surface: str = "#FFFEFC"
    grid: str = "#DCE5E0"
    baseline: str = "#C9D6D0"
    zero_line: str = "#87938D"
    text: str = "#242327"
    muted_text: str = "#676D69"
    card_border: str = "#DDE5E1"

    # Используем только гарантированно доступные веса DejaVu Sans.
    # Это убирает предупреждения Matplotlib на Windows о medium/semibold.
    font_family: str = "DejaVu Sans"
    regular_weight: str = "normal"
    emphasis_weight: str = "bold"

    mean: str = "#3A2230"       # Plum Noir
    median: str = "#F15A3A"     # Persimmon

    ridge_fills: tuple[str, ...] = (
        "#DCEFFE",
        "#C9E8E5",
        "#B7D9CF",
        "#AEBDA7",
        "#84A596",
    )
    ridge_edges: tuple[str, ...] = (
        "#B9DBF2",
        "#9FD2CE",
        "#8FC5B8",
        "#8FA187",
        "#678A7B",
    )


@dataclass(frozen=True)
class ChartLayout:
    """Размеры, интервалы и параметры плотности."""

    figure_width: float = 16.0
    minimum_figure_height: float = 7.2
    height_per_year: float = 1.35
    fixed_vertical_space: float = 2.2
    screen_dpi: int = 120
    save_dpi: int = 300

    ridge_height: float = 0.68
    kde_bandwidth: float = 0.18
    x_grid_points: int = 900

    label_font_size: float = 8.8
    label_box_pad: float = 0.29
    label_height_ratio: float = 0.72
    label_edge_gap_pixels: float = 20.0

    left_margin: float = 0.08
    right_margin: float = 0.86
    top_margin: float = 0.85
    bottom_margin: float = 0.12
    right_annotation_space: float = 1.34

    title_x: float = 0.075
    title_y: float = 0.962
    subtitle_y: float = 0.925
    accent_y: float = 0.902
    footnote_y: float = 0.025

    @property
    def label_padding_points(self) -> float:
        """Внешний padding бокса в points при текущем размере шрифта."""
        return self.label_box_pad * self.label_font_size

    def figure_height(self, year_count: int) -> float:
        """Адаптивная высота: сохраняет воздух при любом числе лет."""
        return max(
            self.minimum_figure_height,
            year_count * self.height_per_year + self.fixed_vertical_space,
        )


THEME = ChartTheme()
LAYOUT = ChartLayout()
