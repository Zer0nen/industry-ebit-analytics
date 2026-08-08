import pandas as pd


INPUT_FILE = "data/construction_companies.parquet"
RESULT_FILE = "data/construction_ebit.parquet"
ERROR_FILE = "data/construction_ebit_errors.csv"


def load_companies():
    companies = pd.read_parquet(
        INPUT_FILE
    )

    all_companies = (
        companies
        .dropna(subset=["ИНН"])
        .drop_duplicates(subset=["ИНН"])
        .copy()
    )

    all_companies["ИНН"] = (
        all_companies["ИНН"]
        .astype("string")
    )

    return all_companies


def build_result_table(companies, results):
    results_df = pd.DataFrame(
        results,
        columns=[
            "inn",
            "year",
            "ebit",
            "address_raw",
            "revenue",
        ],
    )

    company_info = companies[
        [
            "ИНН",
            "Наименование / ФИО",
            "Категория",
        ]
    ].copy()

    company_info = company_info.rename(
        columns={
            "ИНН": "inn",
            "Наименование / ФИО": "company_name",
            "Категория": "category",
        }
    )

    company_info["inn"] = (
        company_info["inn"]
        .astype("string")
    )

    results_df["inn"] = (
        results_df["inn"]
        .astype("string")
    )

    return company_info.merge(
        results_df,
        on="inn",
        how="inner",
    )


def save_results(
    result_table,
    errors,
    result_file=RESULT_FILE,
    error_file=ERROR_FILE,
):
    result_table.to_parquet(
        result_file,
        index=False,
    )

    errors_df = pd.DataFrame(
        errors,
        columns=[
            "inn",
            "year",
            "error",
        ],
    )

    errors_df.to_csv(
        error_file,
        index=False,
        encoding="utf-8-sig",
    )
