from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import pandas as pd

from visualize_src.geocode_companies import (
    DEFAULT_USER_AGENT,
    _address_queries,
    geocode_companies,
)
from visualize_src.plot_geo import plot_company_map
from visualize_src.prepare_geo import prepare_top_companies


class FakeLocation:
    latitude = 55.75
    longitude = 37.62


class GeoPipelineTests(unittest.TestCase):
    def test_prepare_top_companies_selects_unique_inns_by_revenue(self):
        source = pd.DataFrame(
            {
                "inn": ["1", "1", "2", "3"],
                "year": [2023, 2023, 2023, 2022],
                "revenue": [100, 120, 110, 1_000],
                "address_raw": ["A", "B", "C", "D"],
            }
        )

        result = prepare_top_companies(source, year=2023, top_n=2)

        self.assertEqual(result["inn"].tolist(), ["1", "2"])
        self.assertEqual(result["revenue"].tolist(), [120, 110])

    def test_geocoder_uses_fallback_and_persistent_cache(self):
        source = pd.DataFrame(
            {
                "inn": ["1", "2"],
                "year": [2023, 2023],
                "revenue": [200, 100],
                "ebit": [20, 10],
                "address_raw": [
                    "Москва, ул Тверская, д. 1, офис 2",
                    "Москва, ул Тверская, д. 1, офис 2",
                ],
            }
        )
        calls: list[str] = []
        queries = _address_queries(source.loc[0, "address_raw"])

        def fake_geocode(query, **_kwargs):
            calls.append(query)
            return None if query == queries[0].value else FakeLocation()

        with tempfile.TemporaryDirectory() as temporary_directory:
            cache_path = Path(temporary_directory) / "cache.json"
            first = geocode_companies(
                source,
                cache_path=cache_path,
                min_delay_seconds=0,
                geocode=fake_geocode,
                show_progress=lambda _message: None,
            )

            self.assertIsInstance(first, gpd.GeoDataFrame)
            self.assertEqual(first.crs.to_epsg(), 4326)
            self.assertEqual(len(calls), 2)
            self.assertTrue(first.geometry.notna().all())

            calls.clear()
            second = geocode_companies(
                source,
                cache_path=cache_path,
                min_delay_seconds=0,
                geocode=fake_geocode,
                show_progress=lambda _message: None,
            )

            self.assertEqual(calls, [])
            self.assertTrue(second.geometry.notna().all())

    def test_postcode_is_used_as_structured_query(self):
        queries = _address_queries(
            "101000, Москва, ул Тверская, д. 1, офис 2"
        )

        self.assertEqual(len(queries), 1)
        self.assertEqual(queries[0].cache_key, "postcode:101000")
        self.assertEqual(
            queries[0].value,
            {"postalcode": "101000", "country": "Россия"},
        )
        self.assertEqual(queries[0].precision, "postcode")

    def test_placeholder_user_agent_falls_back_to_app_identifier(self):
        source = pd.DataFrame(
            {
                "address_raw": ["101000, Москва"],
            }
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch(
                "visualize_src.geocode_companies.Nominatim"
            ) as nominatim:
                nominatim.return_value.geocode.return_value = FakeLocation()

                result = geocode_companies(
                    source,
                    user_agent=(
                        "business_analysis_project "
                        "(contact: your_email@example.com)"
                    ),
                    cache_path=Path(temporary_directory) / "cache.json",
                    show_progress=lambda _message: None,
                )

        nominatim.assert_called_once_with(
            user_agent=DEFAULT_USER_AGENT,
            timeout=20,
        )
        self.assertTrue(result.geometry.notna().all())

    def test_plot_company_map_creates_html(self):
        frame = gpd.GeoDataFrame(
            {
                "inn": ["1"],
                "company_name": ["Компания"],
                "year": [2023],
                "revenue": [1_000],
                "ebit": [100],
                "address_raw": ["Москва"],
            },
            geometry=gpd.points_from_xy([37.62], [55.75]),
            crs="EPSG:4326",
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "map.html"
            result_path = plot_company_map(frame, output_path)

            self.assertEqual(result_path, output_path)
            self.assertTrue(output_path.exists())
            html = output_path.read_text(encoding="utf-8")
            self.assertIn("company_name", html)
            self.assertIn("OpenStreetMap", html)
            self.assertNotRegex(
                html,
                r"\.foliumtooltip\s*\{\s*\}",
            )


if __name__ == "__main__":
    unittest.main()
