"""Проверка данных и вычисления для EBIT ridgeline."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde

from .config import ChartLayout


@dataclass(frozen=True)
class YearDistribution:
    """Все вычисленные значения, необходимые для отрисовки одного года."""

    year: object
    values: pd.Series
    density: np.ndarray
    base_y: float
    mean_value: float
    median_value: float
    mean_position: float
    median_position: float
    mean_height: float
    median_height: float
    negative_share: float

    @property
    def company_count(self) -> str:
        return f"{len(self.values):,}".replace(",", " ")


def validate_ebit_data(data: pd.DataFrame) -> pd.DataFrame:
    """Проверяет обязательные столбцы и пригодность значений для графика."""
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data должен быть pandas.DataFrame")

    missing_columns = {"year", "ebit"} - set(data.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"В data отсутствуют обязательные столбцы: {missing}")

    if data.empty:
        raise ValueError("DataFrame пуст: нечего отображать")

    prepared = data.loc[:, ["year", "ebit"]].copy()
    prepared["ebit"] = pd.to_numeric(prepared["ebit"], errors="coerce")
    prepared = prepared.dropna(subset=["year", "ebit"])

    if prepared.empty:
        raise ValueError("После удаления пропусков не осталось данных year/ebit")

    return prepared


def signed_log10(values):
    """Симметричное логарифмическое преобразование с сохранением знака."""
    values = np.asarray(values)
    return np.sign(values) * np.log10(1 + np.abs(values))


def format_money(value: float) -> str:
    """Форматирует EBIT; исходные значения считаются тысячами рублей."""
    sign = "+" if value > 0 else "−" if value < 0 else ""
    absolute_value = abs(value)

    if absolute_value >= 1_000_000:
        number, unit = absolute_value / 1_000_000, "млрд ₽"
    elif absolute_value >= 1_000:
        number, unit = absolute_value / 1_000, "млн ₽"
    else:
        number, unit = absolute_value, "тыс. ₽"

    formatted_number = f"{number:.1f}".replace(".", ",")
    return f"{sign}{formatted_number} {unit}"


def get_axis_limits(data: pd.DataFrame) -> tuple[float, float]:
    """Подбирает устойчивые границы X по 99,5%-квантилю."""
    plot_values = signed_log10(data["ebit"].dropna().to_numpy())
    positive_values = plot_values[plot_values >= 0]
    negative_values = np.abs(plot_values[plot_values < 0])

    right_quantile = (
        float(np.quantile(positive_values, 0.995))
        if len(positive_values)
        else 5.9
    )
    left_quantile = (
        float(np.quantile(negative_values, 0.995))
        if len(negative_values)
        else 5.0
    )

    right_limit = min(max(6.0, right_quantile + 0.18), 6.45)
    left_limit = min(max(4.9, left_quantile + 0.08), 5.55)
    return left_limit, right_limit


def build_year_distribution(
    *,
    year: object,
    values: pd.Series,
    level: int,
    x_grid: np.ndarray,
    layout: ChartLayout,
) -> YearDistribution | None:
    """Вычисляет KDE, статистики и высоты линий для одного года."""
    values = values.dropna()
    if len(values) < 2 or values.nunique() < 2:
        return None

    transformed = signed_log10(values.to_numpy())
    kde = gaussian_kde(transformed, bw_method=layout.kde_bandwidth)
    density = kde(x_grid)
    density = density / density.max() * layout.ridge_height

    mean_value = float(values.mean())
    median_value = float(values.median())
    mean_position = float(signed_log10(mean_value))
    median_position = float(signed_log10(median_value))

    return YearDistribution(
        year=year,
        values=values,
        density=density,
        base_y=float(level),
        mean_value=mean_value,
        median_value=median_value,
        mean_position=mean_position,
        median_position=median_position,
        mean_height=float(np.interp(mean_position, x_grid, density)),
        median_height=float(np.interp(median_position, x_grid, density)),
        negative_share=float(values.lt(0).mean() * 100),
    )


def money_ticks_and_labels() -> tuple[np.ndarray, list[str]]:
    """Фиксированная шкала исходных денежных значений."""
    values = np.array(
        [
            -1_000_000,
            -100_000,
            -10_000,
            -1_000,
            0,
            1_000,
            10_000,
            100_000,
            1_000_000,
        ],
        dtype=float,
    )
    labels = [
        "−1 млрд",
        "−100 млн",
        "−10 млн",
        "−1 млн",
        "0",
        "+1 млн",
        "+10 млн",
        "+100 млн",
        "+1 млрд",
    ]
    return values, labels
