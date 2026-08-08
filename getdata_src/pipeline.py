from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import local

from requests import RequestException

from getdata_src.api import create_session
from getdata_src.collector import get_company_ebit
from getdata_src.storage import (
    build_result_table,
    load_companies,
    save_results,
)


MAX_WORKERS = 5
thread_local = local()


def get_thread_session():
    if not hasattr(thread_local, "session"):
        thread_local.session = create_session()

    return thread_local.session


def process_company(
    inn,
    year_from,
    year_to,
    organization_id=None,
):
    session = get_thread_session()

    try:
        return get_company_ebit(
            inn,
            session,
            year_from,
            year_to,
            organization_id,
        )

    except RequestException:
        return [], [{
            "inn": str(inn),
            "year": None,
            "error": "request_error",
        }]

    except (
        KeyError,
        TypeError,
        ValueError,
        IndexError,
    ):
        return [], [{
            "inn": str(inn),
            "year": None,
            "error": "processing_error",
        }]


def run_pipeline(
    year_from,
    year_to,
    show_progress,
    companies=None,
    result_file="data/construction_ebit.parquet",
    error_file="data/construction_ebit_errors.csv",
):
    if companies is None:
        companies = load_companies()

    inns = companies["ИНН"].tolist()
    organization_ids = (
        companies["organization_id"].tolist()
        if "organization_id" in companies.columns
        else [None] * len(companies)
    )

    results = []
    errors = []

    successful_companies = 0
    failed_companies = 0
    total = len(inns)

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:
        futures = [
            executor.submit(
                process_company,
                inn,
                year_from,
                year_to,
                organization_id,
            )
            for inn, organization_id in zip(
                inns,
                organization_ids,
            )
        ]

        for number, future in enumerate(
            as_completed(futures),
            start=1,
        ):
            company_results, company_errors = future.result()

            if company_results:
                results.extend(company_results)
                successful_companies += 1
            else:
                failed_companies += 1

            errors.extend(company_errors)

            progress_step = max(1, total // 10)
            if number % progress_step == 0 or number == total:
                show_progress(
                    number,
                    total,
                    len(results),
                )

    result_table = build_result_table(
        companies,
        results,
    )

    save_results(
        result_table,
        errors,
        result_file,
        error_file,
    )

    return {
        "successful_companies": successful_companies,
        "failed_companies": failed_companies,
        "result_rows": len(result_table),
        "data": result_table,
        "result_file": result_file,
        "error_file": error_file,
    }
