from pathlib import Path

import pandas as pd


FILE_PATH = Path("data/Реестр (1).xlsx")
OUTPUT_PATH = Path("data/construction_companies.parquet")


def build_educational_companies(
    input_path=FILE_PATH,
    output_path=OUTPUT_PATH,
):
    selected_columns = [
        "Наименование / ФИО",
        "Тип субъекта",
        "Категория",
        "ИНН",
        "Основной вид деятельности",
        "Регион",
        "Район",
        "Город",
        "Населенный пункт",
        "Дата включения в реестр",
        "Дата исключения из реестра",
    ]

    registry = pd.read_excel(
        input_path,
        header=2,
        usecols=selected_columns,
        dtype={
            "ИНН": "string",
        },
        parse_dates=[
            "Дата включения в реестр",
            "Дата исключения из реестра",
        ],
        engine="openpyxl",
    )

    registry["is_active"] = registry[
        "Дата исключения из реестра"
    ].isna()

    filter_columns = [
        "Тип субъекта",
        "Категория",
        "Основной вид деятельности",
    ]

    for column in filter_columns:
        registry[column] = registry[column].str.strip()

    is_legal_entity = registry["Тип субъекта"].eq(
        "Юридическое лицо"
    )
    is_required_size = registry["Категория"].isin(
        [
            "Малое предприятие",
            "Среднее предприятие",
        ]
    )
    is_construction = registry[
        "Основной вид деятельности"
    ].str.contains(
        "Строительство жилых и нежилых зданий",
        na=False,
    )

    construction = registry.loc[
        is_legal_entity
        & is_required_size
        & is_construction
    ].copy()

    construction.to_parquet(
        output_path,
        index=False,
    )
    return construction


if __name__ == "__main__":
    build_educational_companies()
