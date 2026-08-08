"""Geocoding and creation of an in-memory GeoDataFrame."""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import geopandas as gpd
import pandas as pd
from geopy.adapters import AdapterHTTPError
from geopy.exc import GeocoderServiceError
from geopy.geocoders import Nominatim


MIN_REQUEST_DELAY_SECONDS = 1.05
CACHE_VERSION = 1
DEFAULT_USER_AGENT = "construction-ebit-map/1.0 (local analytics)"

_POSTCODE = re.compile(r"^\d{6}$")
_INDOOR_PART = re.compile(
    r"^(?:"
    r"оф(?:ис)?\.?|"
    r"пом(?:ещение|ещ\.)?|"
    r"кв(?:артира)?\.?|"
    r"комн(?:ата)?\.?|"
    r"этаж|"
    r"рабочее\s+место"
    r")\b",
    flags=re.IGNORECASE,
)
_HOUSE_PART = re.compile(
    r"\b(?:д(?:ом)?\.?|владение|вл\.?)\s*(?:№\s*)?\d",
    flags=re.IGNORECASE,
)
_STREET_PART = re.compile(
    r"(?:^|\s)(?:"
    r"ул(?:ица)?\.?|"
    r"проспект|пр-?кт|"
    r"переулок|пер\.?|"
    r"шоссе|ш\.?|"
    r"проезд|"
    r"набережная|наб\.?|"
    r"бульвар|б-р|"
    r"площадь|пл\."
    r")(?:\s|$)",
    flags=re.IGNORECASE,
)
_MUNICIPAL_NOISE = re.compile(
    r"^(?:вн\.\s*тер\.|внутригородская\s+территория).*"
    r"муниципальн",
    flags=re.IGNORECASE,
)


class GeocodingError(RuntimeError):
    """Raised when the external geocoder rejects or cannot serve a request."""


def _resolve_user_agent(user_agent: str | None) -> str:
    """Return an app identifier, ignoring placeholders left by old versions."""
    configured_value = user_agent or os.environ.get("GEOCODE_USER_AGENT")
    if not configured_value:
        return DEFAULT_USER_AGENT

    normalized_value = configured_value.casefold()
    placeholder_markers = (
        "your_email",
        "example.",
        "ваш_реальный_email",
        "ваш_email",
    )
    if any(marker in normalized_value for marker in placeholder_markers):
        return DEFAULT_USER_AGENT

    return configured_value


@dataclass(frozen=True)
class GeocodingQuery:
    """A provider query together with its cache key and map precision."""

    cache_key: str
    value: str | dict[str, str]
    precision: str


def _default_cache_path() -> Path:
    configured_path = os.environ.get("GEOCODE_CACHE_PATH")
    if configured_path:
        return Path(configured_path).expanduser()

    if os.name == "nt":
        cache_root = Path(
            os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        )
    else:
        cache_root = Path(
            os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")
        )

    return cache_root / "construction-ebit" / "geocode_cache.json"


def _clean_address(address: str) -> str:
    """Remove office-level details which usually hurt geocoding accuracy."""
    normalized = re.sub(r"\s+", " ", address).strip(" ,")
    raw_parts = [part.strip() for part in normalized.split(",") if part.strip()]
    parts: list[str] = []

    for part in raw_parts:
        if _INDOOR_PART.match(part):
            break
        if _MUNICIPAL_NOISE.match(part):
            continue
        parts.append(part)

    while (
        len(parts) > 1
        and re.fullmatch(r"\d{1,5}[А-ЯA-Z]?", parts[-1], flags=re.IGNORECASE)
        and any(_HOUSE_PART.search(part) for part in parts[:-1])
    ):
        parts.pop()

    if parts and _POSTCODE.fullmatch(parts[0]):
        parts[0] = parts[0]

    return ", ".join(parts)


def _address_queries(address: str) -> list[GeocodingQuery]:
    """Prefer a postal-zone point; use address/locality when no code exists."""
    cleaned = _clean_address(address)
    if not cleaned:
        return []

    parts = [part.strip() for part in cleaned.split(",") if part.strip()]
    if parts and _POSTCODE.fullmatch(parts[0]):
        postcode = parts[0]
        return [
            GeocodingQuery(
                cache_key=f"postcode:{postcode}",
                value={
                    "postalcode": postcode,
                    "country": "Россия",
                },
                precision="postcode",
            )
        ]

    queries = [
        GeocodingQuery(
            cache_key=f"address:{cleaned}",
            value=f"{cleaned}, Россия",
            precision="address",
        )
    ]

    street_index = next(
        (
            index
            for index, part in enumerate(parts)
            if _STREET_PART.search(part)
        ),
        None,
    )
    if street_index is not None and street_index > 0:
        locality = ", ".join(parts[:street_index])
        if locality and locality != cleaned:
            queries.append(
                GeocodingQuery(
                    cache_key=f"locality:{locality}",
                    value=f"{locality}, Россия",
                    precision="locality",
                )
            )

    return queries


def _load_cache(path: Path) -> dict[str, list[float] | None]:
    if not path.exists():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if payload.get("version") != CACHE_VERSION:
        return {}

    locations = payload.get("locations")
    return locations if isinstance(locations, dict) else {}


def _save_cache(path: Path, cache: dict[str, list[float] | None]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    payload = {
        "version": CACHE_VERSION,
        "locations": cache,
    }
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(path)


def _coordinates(location: object) -> list[float]:
    latitude = float(getattr(location, "latitude"))
    longitude = float(getattr(location, "longitude"))

    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("Геокодер вернул координаты вне допустимого диапазона")

    return [latitude, longitude]


def geocode_companies(
    companies: pd.DataFrame,
    *,
    user_agent: str | None = None,
    cache_path: str | Path | None = None,
    min_delay_seconds: float = MIN_REQUEST_DELAY_SECONDS,
    geocode: Callable[..., object | None] | None = None,
    show_progress: Callable[[str], None] = print,
) -> gpd.GeoDataFrame:
    """Geocode registration addresses and return an EPSG:4326 GeoDataFrame.

    Coordinates are kept in memory. The small address-response cache is stored
    in the operating-system cache directory unless ``cache_path`` is supplied.
    A custom ``geocode`` callable can be injected for tests or another provider.
    """
    if not isinstance(companies, pd.DataFrame):
        raise TypeError("companies должен быть pandas.DataFrame")
    if "address_raw" not in companies.columns:
        raise ValueError("В companies отсутствует обязательный столбец: address_raw")
    if min_delay_seconds < 0:
        raise ValueError("min_delay_seconds не может быть отрицательным")

    result = companies.copy()
    resolved_cache_path = (
        Path(cache_path).expanduser()
        if cache_path is not None
        else _default_cache_path()
    )
    cache = _load_cache(resolved_cache_path)

    if geocode is None:
        resolved_user_agent = _resolve_user_agent(user_agent)
        if min_delay_seconds < MIN_REQUEST_DELAY_SECONDS:
            raise ValueError(
                "Для публичного Nominatim min_delay_seconds должен быть не меньше "
                f"{MIN_REQUEST_DELAY_SECONDS}."
            )

        locator = Nominatim(
            user_agent=resolved_user_agent,
            timeout=20,
        )
        geocode = locator.geocode

    latitudes: list[float | None] = []
    longitudes: list[float | None] = []
    precisions: list[str | None] = []
    network_queries = 0
    cache_changed = False
    total = len(result)

    try:
        for number, raw_address in enumerate(result["address_raw"], start=1):
            coordinates: list[float] | None = None
            precision: str | None = None

            if pd.notna(raw_address):
                for query in _address_queries(str(raw_address)):
                    if query.cache_key in cache:
                        cached_coordinates = cache[query.cache_key]
                        if cached_coordinates is not None:
                            coordinates = cached_coordinates
                            precision = query.precision
                            break
                        continue

                    if network_queries:
                        time.sleep(min_delay_seconds)

                    try:
                        location = geocode(
                            query.value,
                            exactly_one=True,
                            country_codes="ru",
                            language="ru",
                            addressdetails=True,
                        )
                    except (AdapterHTTPError, GeocoderServiceError) as error:
                        raise GeocodingError(
                            "Сервис геокодирования отклонил запрос. Проверьте "
                            "GEOCODE_USER_AGENT, не запускайте несколько процессов "
                            "одновременно и повторите запуск позднее. "
                            f"Исходная ошибка: {error}"
                        ) from error

                    network_queries += 1
                    if location is None:
                        cache[query.cache_key] = None
                        cache_changed = True
                        continue

                    coordinates = _coordinates(location)
                    precision = query.precision
                    cache[query.cache_key] = coordinates
                    cache_changed = True
                    break

            if coordinates is None:
                latitudes.append(None)
                longitudes.append(None)
                precisions.append(None)
            else:
                latitudes.append(coordinates[0])
                longitudes.append(coordinates[1])
                precisions.append(precision)

            if number % 25 == 0 or number == total:
                found = sum(latitude is not None for latitude in latitudes)
                show_progress(
                    f"Геокодирование: {number}/{total} | найдено: {found}"
                )
                if cache_changed:
                    _save_cache(resolved_cache_path, cache)
                    cache_changed = False
    finally:
        if cache_changed:
            _save_cache(resolved_cache_path, cache)

    result["latitude"] = latitudes
    result["longitude"] = longitudes
    result["geocode_precision"] = precisions
    geometry = gpd.GeoSeries(
        gpd.points_from_xy(
            result["longitude"],
            result["latitude"],
        ),
        index=result.index,
        crs="EPSG:4326",
    )
    geometry = geometry.where(
        result["latitude"].notna() & result["longitude"].notna()
    )

    return gpd.GeoDataFrame(
        result,
        geometry=geometry,
        crs="EPSG:4326",
    )
