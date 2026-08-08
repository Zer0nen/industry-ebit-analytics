from pathlib import Path

import pandas as pd

from getdata_src.api import (
    create_session,
    search_companies_by_okved,
)
from getdata_src.pipeline import run_pipeline
from Read_thetable import build_educational_companies
from visualize import run_geo_analysis
from visualize_src.geocode_companies import GeocodingError
from visualize_src.plot_ebit import plot_ebit_ridgeline
from visualize_src.plot_growth import plot_growth_curve
from visualize_src.prepare_growth import prepare_ebit_growth


DEFAULT_YEAR_FROM = 2021
DEFAULT_YEAR_TO = 2025
EDUCATIONAL_RESULT = Path("data/construction_ebit.parquet")
EDUCATIONAL_COMPANIES = Path("data/construction_companies.parquet")


def show_progress(processed, total, result_rows):
    print(
        f"{processed}/{total} | "
        f"строк компания-год: {result_rows}"
    )


def print_summary(summary):
    print("\nАнализ завершён")
    print("Компаний с результатом:", summary["successful_companies"])
    print("Компаний без результата:", summary["failed_companies"])
    print("Строк компания-год:", summary["result_rows"])
    print("Данные:", summary["result_file"])
    print("Пропуски:", summary["error_file"])


def run_analytical_mode():
    okved = input("Введите код ОКВЭД: ").strip().replace(",", ".")
    count_input = input(
        "Сколько компаний проанализировать (число или 'все'): "
    ).strip().lower()
    company_limit = None if count_input == "все" else int(count_input)

    print("\nИщу компании с БФО...")
    session = create_session()
    company_rows = search_companies_by_okved(
        okved,
        company_limit,
        session,
    )

    if not company_rows:
        raise SystemExit("Подходящие юридические лица с БФО не найдены.")

    companies = pd.DataFrame(company_rows)
    print(f"Найдено компаний: {len(companies)}")

    file_code = okved.replace(".", "_")
    result_file = f"data/okved_{file_code}_ebit.parquet"
    error_file = f"data/okved_{file_code}_ebit_errors.csv"

    summary = run_pipeline(
        DEFAULT_YEAR_FROM,
        DEFAULT_YEAR_TO,
        show_progress,
        companies=companies,
        result_file=result_file,
        error_file=error_file,
    )
    print_summary(summary)

    return summary["data"], f"okved_{file_code}", len(companies)


def run_educational_mode():
    if EDUCATIONAL_RESULT.exists():
        print("\nИспользую готовые учебные данные из таблицы.")
        data = pd.read_parquet(EDUCATIONAL_RESULT)
        return data, "construction", 500

    if not EDUCATIONAL_COMPANIES.exists():
        print("\nГотовлю учебную выборку из реестра...")
        build_educational_companies()

    summary = run_pipeline(
        DEFAULT_YEAR_FROM,
        DEFAULT_YEAR_TO,
        show_progress,
    )
    print_summary(summary)
    return summary["data"], "construction", 500


def show_visualizations(data, output_name, company_count):
    if data.empty:
        print("Нет рассчитанных данных для визуализации.")
        return

    print(
        "\nЧто показать?\n"
        "1 — распределение EBIT\n"
        "2 — изменение EBIT\n"
        "3 — карту\n"
        "4 — всё вместе"
    )
    choice = input("Ваш выбор: ").strip()

    if choice in {"1", "4"}:
        plot_ebit_ridgeline(
            data,
            output_path=f"data/{output_name}_ebit_distribution.png",
        )

    if choice in {"2", "4"}:
        growth_data = prepare_ebit_growth(data)
        plot_growth_curve(
            growth_data,
            output_path=f"data/{output_name}_ebit_growth.png",
        )

    if choice in {"3", "4"}:
        latest_year = int(data["year"].max())
        try:
            run_geo_analysis(
                data,
                year=latest_year,
                top_n=company_count,
                output_path=(
                    f"data/{output_name}_companies_{latest_year}.html"
                ),
            )
        except (GeocodingError, ValueError) as error:
            print(f"Карта не создана: {error}")

    if choice not in {"1", "2", "3", "4"}:
        print("Неизвестный вариант визуализации.")


def main():
    print(
        "Выберите режим:\n"
        "1 — аналитический по коду ОКВЭД\n"
        "2 — учебный на готовой таблице"
    )
    mode = input("Ваш выбор: ").strip()

    if mode == "1":
        data, output_name, company_count = run_analytical_mode()
    elif mode == "2":
        data, output_name, company_count = run_educational_mode()
    else:
        raise SystemExit("Нужно выбрать режим 1 или 2.")

    show_visualizations(
        data,
        output_name,
        company_count,
    )


if __name__ == "__main__":
    main()
