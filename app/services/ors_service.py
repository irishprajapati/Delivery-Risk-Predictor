"""
OpenRouteService integration for geocoding and driving directions.
District validation is driven by geocoding API responses, not hardcoded keywords.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

ORS_API_KEY = os.getenv("ORS_API_KEY")
GEOCODE_URL = "https://api.openrouteservice.org/geocode/search"
DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"

# Service area — business constraint, not input keyword matching
ALLOWED_DISTRICTS = frozenset({"kathmandu", "lalitpur", "bhaktapur"})

VALLEY_ONLY_MESSAGE = "Service limited to Kathmandu Valley only (Kathmandu, Lalitpur, Bhaktapur districts)"


class LocationValidationError(Exception):
    """Raised when an address cannot be geocoded or is outside the service area."""


class ORSServiceError(Exception):
    """Raised when the OpenRouteService API fails unexpectedly."""


def _require_api_key() -> str:
    if not ORS_API_KEY:
        raise ORSServiceError("ORS_API_KEY is not configured in .env")
    return ORS_API_KEY


def _is_in_nepal_bounds(lng: float, lat: float) -> bool:
    return 80.0 < lng < 88.5 and 26.0 < lat < 30.5


def _normalize_district(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip().lower()


def _extract_district(properties: dict) -> str | None:
    """Extract district from ORS geocoding properties (county is primary for Nepal)."""
    for field in ("county", "locality", "region", "name"):
        normalized = _normalize_district(properties.get(field))
        if normalized in ALLOWED_DISTRICTS:
            return normalized
    county = _normalize_district(properties.get("county"))
    return county


def _is_allowed_district(district: str | None) -> bool:
    return district is not None and district in ALLOWED_DISTRICTS


def geocode_address(address: str) -> dict:
    """
    Geocode an address via OpenRouteService.
    Returns lat, lng, district, label, and matched area name.
    """
    api_key = _require_api_key()
    address = address.strip()
    if not address:
        raise LocationValidationError("Address cannot be empty")

    params = {
        "api_key": api_key,
        "text": address,
        "size": 5,
        "boundary.country": "NP",
    }

    try:
        response = requests.get(GEOCODE_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        logger.error("ORS geocoding request failed for %r: %s", address, exc)
        raise ORSServiceError(f"Geocoding service unavailable: {exc}") from exc

    features = data.get("features") or []
    if not features:
        raise LocationValidationError(f"Could not find location: {address}")

    # Prefer highest-confidence results within Nepal that belong to allowed districts
    ranked: list[tuple[float, dict]] = []
    for feature in features:
        props = feature.get("properties") or {}
        coords = feature.get("geometry", {}).get("coordinates")
        if not coords or len(coords) < 2:
            continue

        lng, lat = float(coords[0]), float(coords[1])
        if not _is_in_nepal_bounds(lng, lat):
            continue

        district = _extract_district(props)
        confidence = float(props.get("confidence") or 0)
        in_service_area = 1 if _is_allowed_district(district) else 0
        ranked.append((in_service_area * 10 + confidence, {
            "lat": lat,
            "lng": lng,
            "district": district,
            "label": props.get("label") or props.get("name") or address,
            "matched_area": props.get("name") or props.get("locality") or address,
        }))

    if not ranked:
        raise LocationValidationError(f"Could not find a valid location in Nepal: {address}")

    ranked.sort(key=lambda item: item[0], reverse=True)
    best = ranked[0][1]

    if not _is_allowed_district(best["district"]):
        district_name = best["district"] or "unknown"
        raise LocationValidationError(
            f"Location '{address}' is in {district_name.title()} district. {VALLEY_ONLY_MESSAGE}"
        )

    return best


def get_driving_route(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
) -> dict:
    """
    Fetch a real driving route from OpenRouteService.
    Returns distance_km, duration_min, and polyline as [{lat, lng}, ...].
    """
    api_key = _require_api_key()
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }
    body = {
        "coordinates": [[origin_lng, origin_lat], [dest_lng, dest_lat]],
    }

    try:
        response = requests.post(DIRECTIONS_URL, json=body, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        logger.error("ORS directions request failed: %s", exc)
        raise ORSServiceError(f"Routing service unavailable: {exc}") from exc

    try:
        feature = data["features"][0]
        summary = feature["properties"]["summary"]
        coordinates = feature["geometry"]["coordinates"]
    except (KeyError, IndexError) as exc:
        raise ORSServiceError("Failed to parse driving route from OpenRouteService") from exc

    polyline = [{"lat": lat, "lng": lng} for lng, lat in coordinates]

    return {
        "distance_km": round(summary["distance"] / 1000, 2),
        "duration_min": round(summary["duration"] / 60, 1),
        "polyline": polyline,
    }


def build_route_info(pickup_address: str, delivery_address: str) -> dict:
    """
    Geocode both addresses, validate districts, and fetch a real driving route.
    """
    pickup = geocode_address(pickup_address)
    delivery = geocode_address(delivery_address)

    driving = get_driving_route(
        pickup["lat"], pickup["lng"],
        delivery["lat"], delivery["lng"],
    )

    return {
        "pickup_district": pickup["district"],
        "delivery_district": delivery["district"],
        "pickup_area": pickup["matched_area"],
        "delivery_area": delivery["matched_area"],
        "pickup_coordinates": {"lat": pickup["lat"], "lng": pickup["lng"]},
        "delivery_coordinates": {"lat": delivery["lat"], "lng": delivery["lng"]},
        "estimated_distance_km": driving["distance_km"],
        "estimated_duration_min": driving["duration_min"],
        "route_polyline": driving["polyline"],
        "route_source": "openrouteservice",
    }
