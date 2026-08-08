from getdata_src.calculator import calculate_ebit


SIMPLIFIED_KND = "0710096"


def get_financial_result(report):
    type_corrections = report.get("typeCorrections") or []

    corrections = [
        item.get("correction")
        for item in type_corrections
        if item.get("correction")
    ]

    if not corrections:
        return None

    correction = max(
        corrections,
        key=lambda item: int(
            item.get("correctionVersion") or 0
        ),
    )

    return correction.get("financialResult")


def parse_report(inn, report, year_from, year_to):
    year = int(report["period"])

    if not year_from <= year <= year_to:
        return None, None

    if report.get("knd") == SIMPLIFIED_KND:
        return None, {
            "inn": str(inn),
            "year": year,
            "error": "simplified_form",
        }

    financial_result = get_financial_result(report)

    if not financial_result:
        return None, {
            "inn": str(inn),
            "year": year,
            "error": "financial_result_not_found",
        }

    ebit = calculate_ebit(financial_result)

    if ebit is None:
        return None, {
            "inn": str(inn),
            "year": year,
            "error": "financial_data_not_enough",
        }

    organization_info = report.get("organizationInfo") or {}

    return {
        "inn": str(inn),
        "year": year,
        "ebit": ebit,
        "address_raw": organization_info.get("address"),
        "revenue": report.get("gainSum"),
    }, None
