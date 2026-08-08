from __future__ import annotations

import unittest
from unittest.mock import patch

from getdata_src.api import search_companies_by_okved


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "content": [
                {
                    "id": 10,
                    "inn": "1234567890",
                    "shortName": "ООО Тест",
                    "bfo": {
                        "period": "2025",
                        "knd": "0710099",
                    },
                },
                {
                    "id": 11,
                    "inn": "123456789012",
                    "shortName": "Не юрлицо",
                    "bfo": {"period": "2025"},
                },
                {
                    "id": 12,
                    "inn": "0987654321",
                    "shortName": "Без отчётности",
                    "bfo": None,
                },
                {
                    "id": 13,
                    "inn": "1111111111",
                    "shortName": "Упрощённая форма",
                    "bfo": {
                        "period": "2025",
                        "knd": "0710096",
                    },
                },
            ],
            "last": True,
        }


class FakeSession:
    def __init__(self):
        self.params = None

    def get(self, _url, *, params, timeout):
        self.params = params
        self.timeout = timeout
        return FakeResponse()


class PaginatedFakeResponse(FakeResponse):
    def __init__(self, page):
        self.page = page

    def json(self):
        return {
            "content": [{
                "id": self.page + 1,
                "inn": f"{self.page + 1:010d}",
                "shortName": f"Компания {self.page + 1}",
                "bfo": {"period": "2025", "knd": "0710099"},
            }],
            "last": self.page == 1,
        }


class PaginatedFakeSession:
    def get(self, _url, *, params, timeout):
        return PaginatedFakeResponse(params["page"])


class CompanySearchTests(unittest.TestCase):
    def test_search_keeps_only_legal_entities_with_bfo(self):
        session = FakeSession()

        companies = search_companies_by_okved(
            "62.01",
            limit=5,
            session=session,
        )

        self.assertEqual(len(companies), 1)
        self.assertEqual(companies[0]["ИНН"], "1234567890")
        self.assertEqual(companies[0]["organization_id"], 10)
        self.assertEqual(session.params["okved"], "62.01")
        self.assertNotIn("period", session.params)
        self.assertEqual(session.params["sort"], "inn,asc")

    def test_search_all_reads_every_page(self):
        companies = search_companies_by_okved(
            "62.01",
            limit=None,
            session=PaginatedFakeSession(),
        )

        self.assertEqual(len(companies), 2)
        self.assertEqual(companies[1]["organization_id"], 2)

    def test_large_search_uses_inn_parts_and_removes_highlight(self):
        class LargeFakeResponse(FakeResponse):
            def __init__(self, params):
                self.params = params

            def json(self):
                inn_part = self.params.get("inn")
                direction = self.params["sort"].split(",")[1]

                if inn_part == "000":
                    return {
                        "content": [{
                            "id": 2,
                            "inn": "0000<strong>000</strong>002",
                            "shortName": "ООО Два",
                            "bfo": {"knd": "0710099"},
                        }],
                        "totalElements": 1,
                        "last": True,
                    }

                organization_id = 1 if direction == "asc" else 3
                return {
                    "content": [{
                        "id": organization_id,
                        "inn": f"{organization_id:010d}",
                        "shortName": f"ООО {organization_id}",
                        "bfo": {"knd": "0710099"},
                    }],
                    "totalElements": 3,
                    "last": False,
                }

        class LargeFakeSession:
            def get(self, _url, *, params, timeout):
                return LargeFakeResponse(params)

        with (
            patch("getdata_src.api.SEARCH_PAGE_SIZE", 1),
            patch("getdata_src.api.SEARCH_RESULT_WINDOW", 1),
        ):
            companies = search_companies_by_okved(
                "62.01",
                limit=None,
                session=LargeFakeSession(),
            )

        self.assertEqual(len(companies), 3)
        self.assertIn("0000000002", {row["ИНН"] for row in companies})


if __name__ == "__main__":
    unittest.main()
