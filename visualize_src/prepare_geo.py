import pandas as pd


def prepare_top_companies(
    data: pd.DataFrame,
    year: int,
    top_n: int = 500,
) -> pd.DataFrame:
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data должен быть pandas.DataFrame")
    if top_n <= 0:
        raise ValueError("top_n должен быть положительным числом")

    required_columns = {"inn", "year", "revenue", "address_raw"}
    missing_columns = required_columns - set(data.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"В data отсутствуют обязательные столбцы: {missing}")

    years = pd.to_numeric(data["year"], errors="coerce")
    year_data = data.loc[years.eq(year)].copy()
    year_data["revenue"] = pd.to_numeric(
        year_data["revenue"],
        errors="coerce",
    )
    year_data = year_data.dropna(subset=["revenue"])

    return (
        year_data
        .sort_values("revenue", ascending=False, kind="stable")
        .drop_duplicates(subset=["inn"], keep="first")
        .head(top_n)
        .copy()
    )
