import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BACKGROUND_COLOR = "#F6F1E7"
TEXT_COLOR = "#292522"
GRID_COLOR = "#DDD4C5"
ZERO_COLOR = "#8A8178"

LINE_COLORS = [
    "#236192",
    "#C35A2C",
]


def plot_growth_curve(
    growth_data: pd.DataFrame,
    output_path: str | None = None,
) -> None:
    if growth_data.empty:
        print(
            "Нет данных для графика "
            "трёхлетнего изменения EBIT"
        )
        return

    distribution = (
        growth_data
        .groupby(
            [
                "start_year",
                "end_year",
                "growth_percent",
            ]
        )
        .size()
        .reset_index(
            name="companies_count"
        )
    )

    # Экстремальные проценты могут растянуть
    # ось на десятки тысяч процентов.
    # Показываем центральные 98% наблюдений.
    lower_limit = int(
        np.floor(
            growth_data[
                "growth_percent"
            ].quantile(0.01)
        )
    )

    upper_limit = int(
        np.ceil(
            growth_data[
                "growth_percent"
            ].quantile(0.99)
        )
    )

    # Ноль обязательно должен быть виден.
    lower_limit = min(lower_limit, 0)
    upper_limit = max(upper_limit, 0)

    x_values = np.arange(
        lower_limit,
        upper_limit + 1,
    )

    figure, axes = plt.subplots(
        figsize=(13.5, 7.5),
        dpi=120,
    )

    figure.patch.set_facecolor(
        BACKGROUND_COLOR
    )
    axes.set_facecolor(
        BACKGROUND_COLOR
    )

    comparisons = (
        growth_data[
            [
                "start_year",
                "end_year",
            ]
        ]
        .drop_duplicates()
        .sort_values(
            [
                "start_year",
                "end_year",
            ]
        )
    )

    for index, comparison in enumerate(
        comparisons.itertuples(
            index=False
        )
    ):
        start_year = comparison.start_year
        end_year = comparison.end_year

        curve = distribution[
            (
                distribution["start_year"]
                == start_year
            )
            & (
                distribution["end_year"]
                == end_year
            )
        ].set_index(
            "growth_percent"
        )["companies_count"]

        # Добавляем отсутствующие целые проценты
        # с количеством компаний 0.
        curve = curve.reindex(
            x_values,
            fill_value=0,
        )

        color = LINE_COLORS[
            index % len(LINE_COLORS)
        ]

        companies_count = len(
            growth_data[
                (
                    growth_data["start_year"]
                    == start_year
                )
                & (
                    growth_data["end_year"]
                    == end_year
                )
            ]
        )

        label = (
            f"{start_year} → {end_year} "
            f"(n={companies_count:,})"
        ).replace(",", " ")

        axes.plot(
            x_values,
            curve.values,
            color=color,
            linewidth=2.2,
            label=label,
        )

        axes.fill_between(
            x_values,
            curve.values,
            color=color,
            alpha=0.10,
        )
    axes.set_xscale(
        "symlog",
        linthresh=100,
        linscale=1.2,
    )

    custom_ticks = [
        -5000, -2000, -1000, -500, -200, -100, -50, -20, -10,
        0,
        10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000
    ]

    visible_ticks = [
        tick for tick in custom_ticks
        if lower_limit <= tick <= upper_limit
    ]

    axes.set_xticks(visible_ticks)

    axes.set_xticklabels(
        [str(tick) for tick in visible_ticks]
    )
    
    axes.axvline(
        0,
        color=ZERO_COLOR,
        linestyle="--",
        linewidth=1.2,
    )

    axes.set_xlabel(
        "Изменение EBIT с 2022 по 2025 год, %",
        fontsize=11,
        labelpad=10,
    )
    axes.set_ylabel(
        "Количество компаний",
        fontsize=11,
        labelpad=10,
    )

    axes.set_title(
    "Распределение изменения EBIT: 2022–2025",
        loc="left",
        fontsize=19,
        fontweight="bold",
        color=TEXT_COLOR,
        pad=26,
    )

    axes.text(
        0,
        1.025,
        (
            "Каждой целой величине изменения "
            "соответствует количество компаний"
        ),
        transform=axes.transAxes,
        fontsize=10,
        color="#746D65",
    )

    axes.grid(
        axis="y",
        color=GRID_COLOR,
        linewidth=0.8,
        alpha=0.8,
    )

    axes.set_axisbelow(True)

    for side in [
        "top",
        "right",
        "left",
    ]:
        axes.spines[side].set_visible(
            False
        )

    axes.spines["bottom"].set_color(
        GRID_COLOR
    )

    axes.tick_params(
        axis="both",
        length=0,
        colors=TEXT_COLOR,
    )

    axes.legend(
        frameon=False,
        fontsize=10,
    )

    figure.text(
        0.075,
        0.025,
        (
            "Показан диапазон от 1-го до "
            "99-го процентиля. Компании с EBIT = 0 "
            "в начальном году исключены."
        ),
        fontsize=8.5,
        color="#746D65",
    )

    figure.subplots_adjust(
        left=0.09,
        right=0.97,
        top=0.86,
        bottom=0.14,
    )

    if output_path is not None:
        figure.savefig(
            output_path,
            dpi=300,
            bbox_inches="tight",
            facecolor=figure.get_facecolor(),
        )

    if "agg" not in plt.get_backend().lower():
        plt.show()
