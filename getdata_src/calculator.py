def get_number(financial_result, field):
    return float(financial_result.get(field) or 0)


def calculate_ebit(financial_result):
    interest_income_raw = financial_result.get("current2320")
    interest_expense_raw = financial_result.get("current2330")

    interest_income = get_number(
        financial_result,
        "current2320",
    )
    interest_expense = get_number(
        financial_result,
        "current2330",
    )

    profit_before_tax_raw = financial_result.get("current2300")

    calculated_profit_before_tax = (
        get_number(financial_result, "current2200")
        + get_number(financial_result, "current2310")
        + interest_income
        - interest_expense
        + get_number(financial_result, "current2340")
        - get_number(financial_result, "current2350")
    )

    if profit_before_tax_raw is None:
        fields_for_calculation = [
            "current2200",
            "current2310",
            "current2320",
            "current2330",
            "current2340",
            "current2350",
        ]

        has_nonzero_value = any(
            get_number(financial_result, field) != 0
            for field in fields_for_calculation
        )

        if not has_nonzero_value:
            return None

        profit_before_tax = calculated_profit_before_tax

    else:
        profit_before_tax = float(profit_before_tax_raw)

        interest_is_missing = (
            interest_income_raw is None
            or interest_expense_raw is None
        )

        if (
            interest_is_missing
            and calculated_profit_before_tax != profit_before_tax
        ):
            return None

    return (
        profit_before_tax
        + interest_expense
        - interest_income
    )
