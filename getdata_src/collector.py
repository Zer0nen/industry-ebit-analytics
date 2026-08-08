from getdata_src.api import get_organization_id, get_reports
from getdata_src.parser import parse_report


def get_company_ebit(
    inn,
    session,
    year_from,
    year_to,
    organization_id=None,
):
    if organization_id is None:
        organization_id = get_organization_id(
            inn,
            session,
        )

    if organization_id is None:
        return [], [{
            "inn": str(inn),
            "year": None,
            "error": "organization_not_found",
        }]

    reports = get_reports(
        organization_id,
        session,
    )

    if not reports:
        return [], [{
            "inn": str(inn),
            "year": None,
            "error": "reports_not_found",
        }]

    results = []
    errors = []

    for report in reports:
        result, error = parse_report(
            inn,
            report,
            year_from,
            year_to,
        )

        if result is not None:
            results.append(result)

        if error is not None:
            errors.append(error)

    return results, errors
