import re

import requests


SIMPLE_SEARCH_URL = (
    "https://bo.nalog.gov.ru/"
    "advanced-search/organizations/search"
)
ADVANCED_SEARCH_URL = (
    "https://bo.nalog.gov.ru/"
    "advanced-search/organizations"
)
REPORTS_URL = "https://bo.nalog.gov.ru/nbo/organizations/{}/bfo/"
TIMEOUT = (5, 20)
SEARCH_PAGE_SIZE = 2000
SEARCH_RESULT_WINDOW = 10000


def create_session():
    session = requests.Session()

    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://bo.nalog.gov.ru/",
    })

    return session


def get_organization_id(inn, session):
    response = session.get(
        SIMPLE_SEARCH_URL,
        params={
            "query": inn,
            "page": 0,
        },
        timeout=TIMEOUT,
    )

    response.raise_for_status()

    organizations = response.json()["content"]

    if not organizations:
        return None

    return organizations[0]["id"]


def search_companies_by_okved(okved, limit, session):
    companies = {}
    seen_organizations = set()

    def collect(inn_part=None, direction="asc"):
        page = 0
        total = None
        complete = False

        while page * SEARCH_PAGE_SIZE < SEARCH_RESULT_WINDOW:
            params = {
                "okved": okved,
                "page": page,
                "size": SEARCH_PAGE_SIZE,
                "sort": f"inn,{direction}",
            }
            if inn_part is not None:
                params["inn"] = inn_part

            response = session.get(
                ADVANCED_SEARCH_URL,
                params=params,
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            search_result = response.json()

            if total is None:
                total = search_result.get("totalElements")

            content = search_result.get("content", [])
            for organization in content:
                organization_id = organization.get("id")
                inn = re.sub(
                    r"<[^>]+>",
                    "",
                    str(organization.get("inn") or ""),
                )
                seen_organizations.add(organization_id or inn)

                # ИНН юридического лица состоит из 10 цифр.
                if len(inn) != 10 or not inn.isdigit():
                    continue

                bfo = organization.get("bfo")
                if not bfo:
                    continue

                # Только упрощённая форма не содержит данных для точного EBIT.
                # Смешанный КНД включает обычную форму и поэтому подходит.
                if bfo.get("knd") == "0710096":
                    continue

                companies.setdefault(inn, {
                    "ИНН": inn,
                    "Наименование / ФИО": (
                        organization.get("shortName") or inn
                    ),
                    "Категория": f"ОКВЭД {okved}",
                    "organization_id": organization_id,
                })

                if limit is not None and len(companies) >= limit:
                    return total, True

            if search_result.get("last", False) or not content:
                complete = True
                break

            page += 1

        return total, complete

    total, complete = collect()
    if limit is not None and len(companies) >= limit:
        return list(companies.values())[:limit]

    if total is None:
        total = len(seen_organizations)

    # ГИР БО не отдаёт страницы глубже 10 000. Сначала читаем конец
    # стабильной сортировки, затем разбиваем остаток по фрагментам ИНН.
    if not complete and len(seen_organizations) < total:
        collect(direction="desc")

    needs_more = (
        limit is None and len(seen_organizations) < total
    ) or (
        limit is not None
        and len(companies) < limit
        and len(seen_organizations) < total
    )

    if needs_more:
        for number in range(1000):
            inn_part = f"{number:03d}"
            part_total, part_complete = collect(inn_part=inn_part)

            if (
                not part_complete
                and part_total
                and part_total > SEARCH_RESULT_WINDOW
            ):
                collect(inn_part=inn_part, direction="desc")

            if limit is not None and len(companies) >= limit:
                break
            if limit is None and len(seen_organizations) >= total:
                break

    if limit is None and len(seen_organizations) < total:
        raise RuntimeError(
            "ГИР БО не позволил получить полную выдачу: "
            f"получено {len(seen_organizations)} из {total} организаций."
        )

    return list(companies.values())[:limit]


def get_reports(organization_id, session):
    response = session.get(
        REPORTS_URL.format(organization_id),
        timeout=TIMEOUT,
    )

    response.raise_for_status()

    return response.json()
