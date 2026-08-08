import pandas as pd


def prepare_ebit_growth(
    data: pd.DataFrame,
) -> pd.DataFrame:
    start_year = 2022
    end_year = 2025

    ebit_by_year = data.pivot(
        index="inn",
        columns="year",
        values="ebit",
    )

    if (
        start_year not in ebit_by_year.columns
        or end_year not in ebit_by_year.columns
    ):
        return pd.DataFrame(
            columns=[
                "inn",
                "start_year",
                "end_year",
                "growth_percent",
            ]
        )

    companies = ebit_by_year[
        [
            start_year,
            end_year,
        ]
    ].dropna().copy()

    # Если EBIT в 2022 году равен нулю,
    # процентное изменение посчитать нельзя.
    companies = companies[
        companies[start_year] != 0
    ].copy()

    companies["growth_percent"] = (
        (
            companies[end_year]
            - companies[start_year]
        )
        / companies[start_year].abs()
        * 100
    ).round().astype(int)

    result = pd.DataFrame({
        "inn": companies.index,
        "start_year": start_year,
        "end_year": end_year,
        "growth_percent": (
            companies["growth_percent"].values
        ),
    })

    return result
