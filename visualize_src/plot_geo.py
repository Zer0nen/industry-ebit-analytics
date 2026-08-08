"""Interactive map for geocoded companies."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd


def plot_company_map(
    companies: gpd.GeoDataFrame,
    output_path: str | Path,
) -> Path:
    """Save an interactive HTML map and return its path."""
    if not isinstance(companies, gpd.GeoDataFrame):
        raise TypeError("companies должен быть geopandas.GeoDataFrame")
    if companies.crs is None:
        raise ValueError("Для GeoDataFrame не задана система координат")

    mapped = companies.dropna(subset=[companies.geometry.name]).copy()
    if mapped.empty:
        raise ValueError("Не найдено ни одной координаты для построения карты")

    mapped = mapped.to_crs("EPSG:4326")
    mapped["revenue_mln_rub"] = (
        pd.to_numeric(mapped["revenue"], errors="coerce") / 1_000
    ).round(1)
    mapped["ebit_mln_rub"] = (
        pd.to_numeric(mapped["ebit"], errors="coerce") / 1_000
    ).round(1)

    tooltip_columns = [
        column
        for column in [
            "company_name",
            "inn",
            "year",
            "revenue_mln_rub",
            "ebit_mln_rub",
            "geocode_precision",
            "address_raw",
        ]
        if column in mapped.columns
    ]
    tooltip_aliases = {
        "company_name": "Компания",
        "inn": "ИНН",
        "year": "Год",
        "revenue_mln_rub": "Выручка, млн ₽",
        "ebit_mln_rub": "EBIT, млн ₽",
        "geocode_precision": "Точность геокодирования",
        "address_raw": "Адрес регистрации",
    }

    map_object = mapped.explore(
        column="revenue",
        cmap="YlOrRd",
        tiles="OpenStreetMap",
        tooltip=tooltip_columns,
        tooltip_kwds={
            "aliases": [tooltip_aliases[column] for column in tooltip_columns],
            "localize": True,
            "sticky": False,
            "style": (
                "background-color: white; "
                "color: #292522; "
                "font-family: Arial, sans-serif; "
                "font-size: 12px; "
                "padding: 6px;"
            ),
        },
        marker_type="circle_marker",
        marker_kwds={
            "radius": 5,
        },
        style_kwds={
            "fillOpacity": 0.78,
            "weight": 0.7,
        },
        legend=True,
        name="Компании",
    )

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    map_object.save(path)
    return path
