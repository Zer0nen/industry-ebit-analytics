
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .ebit_chart.config import LAYOUT, THEME
from .ebit_chart.data import (
    build_year_distribution,
    get_axis_limits,
    validate_ebit_data,
)
from .ebit_chart.drawing import (
    add_figure_text,
    configure_geometry,
    create_figure,
    draw_year,
    save_figure,
    style_axes,
)


def plot_ebit_ridgeline(
    data: pd.DataFrame,
    output_path: str | None = None,
) -> None:
   
    prepared_data = validate_ebit_data(data)
    years = sorted(prepared_data["year"].unique())
    left_limit, right_limit = get_axis_limits(prepared_data)
    x_grid = np.linspace(
        -left_limit,
        right_limit,
        LAYOUT.x_grid_points,
    )

    figure, axes = create_figure(
        year_count=len(years),
        theme=THEME,
        layout=LAYOUT,
    )
    configure_geometry(
        figure=figure,
        axes=axes,
        left_limit=left_limit,
        right_limit=right_limit,
        year_count=len(years),
        theme=THEME,
        layout=LAYOUT,
    )

    for level, year in enumerate(years):
        year_values = prepared_data.loc[
            prepared_data["year"] == year,
            "ebit",
        ]
        distribution = build_year_distribution(
            year=year,
            values=year_values,
            level=level,
            x_grid=x_grid,
            layout=LAYOUT,
        )
        if distribution is None:
            continue

        draw_year(
            axes=axes,
            x_grid=x_grid,
            distribution=distribution,
            color_index=level,
            right_limit=right_limit,
            left_limit=left_limit,
            theme=THEME,
            layout=LAYOUT,
        )

    style_axes(
        axes=axes,
        years=years,
        left_limit=left_limit,
        right_limit=right_limit,
        theme=THEME,
        layout=LAYOUT,
    )
    add_figure_text(
        figure=figure,
        theme=THEME,
        layout=LAYOUT,
    )
    save_figure(
        figure=figure,
        output_path=output_path,
        layout=LAYOUT,
    )
    if "agg" not in plt.get_backend().lower():
        plt.show()
