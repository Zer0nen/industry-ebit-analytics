import argparse
from pathlib import Path

import pandas as pd

from visualize_src.geocode_companies import (
    GeocodingError,
    geocode_companies,
)

from visualize_src.plot_ebit import (
    plot_ebit_ridgeline,
)
from visualize_src.prepare_growth import (
    prepare_ebit_growth,
)
from visualize_src.plot_growth import (
    plot_growth_curve,
)
from visualize_src.prepare_geo import (
    prepare_top_companies,
)
from visualize_src.plot_geo import (
    plot_company_map,
)


def choose_geo_year(
    data: pd.DataFrame,
) -> int:
    available_years = sorted(
        data["year"]
        .dropna()
        .astype(int)
        .unique()
    )

    while True:
        try:
            year = int(
                input(
                    "Год для геоанализа "
                    f"({available_years[0]}–"
                    f"{available_years[-1]}): "
                )
            )

            if year in available_years:
                return year

            print(
                "Нет данных за этот год."
            )

        except ValueError:
            print(
                "Год нужно ввести числом."
            )


def run_geo_analysis(
    data: pd.DataFrame,
    *,
    year: int | None = None,
    top_n: int = 500,
    output_path: str | Path | None = None,
) -> Path:
    geo_year = year if year is not None else choose_geo_year(data)

    available_years = set(
        data["year"].dropna().astype(int).unique()
    )
    if geo_year not in available_years:
        raise ValueError(f"Нет данных за {geo_year} год")

    top_companies = prepare_top_companies(
        data,
        year=geo_year,
        top_n=top_n,
    )

    print(
        f"Для карты выбрано "
        f"{len(top_companies)} компаний "
        f"за {geo_year} год."
    )

    company_geodata = geocode_companies(
        top_companies
    )

    found = company_geodata.geometry.notna().sum()
    if found == 0:
        raise ValueError(
            "Геокодер не нашёл ни одного адреса. Карта не создана."
        )

    map_path = Path(output_path or f"data/top{top_n}_companies_{geo_year}.html")
    plot_company_map(
        company_geodata,
        output_path=map_path,
    )

    print(
        f"Координаты найдены: "
        f"{found}/{len(company_geodata)}"
    )
    print(f"Интерактивная карта сохранена: {map_path}")
    return map_path


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Построение графиков EBIT и карты крупнейших компаний",
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Год карты; если не указан, программа запросит его интерактивно",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=500,
        help="Количество крупнейших по выручке компаний (по умолчанию: 500)",
    )
    parser.add_argument(
        "--map-output",
        type=Path,
        help="Путь к HTML-карте",
    )
    return parser


def main() -> None:
    arguments = build_argument_parser().parse_args()
    data = pd.read_parquet(
        "data/construction_ebit.parquet"
    )

    plot_ebit_ridgeline(
        data,
        output_path=(
            "data/ebit_distribution.png"
        ),
    )

    growth_data = prepare_ebit_growth(
        data
    )

    plot_growth_curve(
        growth_data,
        output_path=(
            "data/ebit_growth_2022_2025.png"
        ),
    )

    try:
        run_geo_analysis(
            data,
            year=arguments.year,
            top_n=arguments.top_n,
            output_path=arguments.map_output,
        )
    except (GeocodingError, ValueError) as error:
        raise SystemExit(f"Карта не создана: {error}") from error


if __name__ == "__main__":
    main()
