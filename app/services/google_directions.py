"""
Google Maps Directions API integration for real driving routes.
Falls back gracefully when the API key is missing or the request fails.
"""

import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"


def decode_polyline(encoded: str) -> list[dict[str, float]]:
    """Decode Google's encoded polyline into [{lat, lng}, ...]."""
    points: list[dict[str, float]] = []
    index = 0
    lat = 0
    lng = 0

    while index < len(encoded):
        shift = result = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break
        delta_lat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += delta_lat

        shift = result = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break
        delta_lng = ~(result >> 1) if (result & 1) else (result >> 1)
        lng += delta_lng

        points.append({"lat": lat / 1e5, "lng": lng / 1e5})

    return points


def get_driving_route(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
) -> dict | None:
    """
    Fetch a driving route from Google Directions API.
    Returns distance_km, duration_min, and polyline points, or None on failure.
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.debug("GOOGLE_MAPS_API_KEY not set — skipping Directions API")
        return None

    params = {
        "origin": f"{origin_lat},{origin_lng}",
        "destination": f"{dest_lat},{dest_lng}",
        "key": GOOGLE_MAPS_API_KEY,
        "mode": "driving",
    }

    try:
        response = requests.get(DIRECTIONS_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        logger.warning("Google Directions request failed: %s", exc)
        return None

    if data.get("status") != "OK" or not data.get("routes"):
        logger.warning("Google Directions returned status: %s", data.get("status"))
        return None

    route = data["routes"][0]
    leg = route["legs"][0]
    encoded = route["overview_polyline"]["points"]

    return {
        "distance_km": round(leg["distance"]["value"] / 1000, 2),
        "duration_min": round(leg["duration"]["value"] / 60, 1),
        "polyline": decode_polyline(encoded),
    }


def enrich_route_info(route_info: dict) -> dict:
    """
    Add real driving distance, duration, and polyline to route_info.
    Keeps haversine estimate as fallback when Google is unavailable.
    """
    pickup = route_info["pickup_coordinates"]
    delivery = route_info["delivery_coordinates"]

    driving = get_driving_route(
        pickup["lat"], pickup["lng"],
        delivery["lat"], delivery["lng"],
    )

    if driving:
        route_info["estimated_distance_km"] = driving["distance_km"]
        route_info["estimated_duration_min"] = driving["duration_min"]
        route_info["route_polyline"] = driving["polyline"]
        route_info["route_source"] = "google"
    else:
        route_info["estimated_duration_min"] = None
        route_info["route_polyline"] = [
            {"lat": pickup["lat"], "lng": pickup["lng"]},
            {"lat": delivery["lat"], "lng": delivery["lng"]},
        ]
        route_info["route_source"] = "straight_line"

    return route_info
