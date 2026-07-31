"""
OpenWeatherMap integration for route-aware weather fetching.
All API keys stay server-side; the frontend never calls weather APIs directly.
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

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

RAIN_CATEGORIES = frozenset({"rain", "drizzle", "thunderstorm"})


class WeatherServiceError(Exception):
    """Raised when the OpenWeatherMap API fails unexpectedly."""


def _require_api_key() -> str:
    if not OPENWEATHER_API_KEY:
        raise WeatherServiceError("OPENWEATHER_API_KEY is not configured in .env")
    return OPENWEATHER_API_KEY


def normalize_weather(main_category: str) -> str:
    """
    Convert OpenWeatherMap `weather[].main` into RAIN, CLOUDY, or CLEAR.
    """
    category = (main_category or "").strip().lower()

    if category in RAIN_CATEGORIES:
        return "RAIN"
    if category == "clouds":
        return "CLOUDY"
    if category == "clear":
        return "CLEAR"

    # Non-rain adverse conditions (fog, mist, snow, etc.) map to CLOUDY for risk logic.
    return "CLOUDY"


def get_weather(lat: float, lon: float) -> str:
    """
    Fetch current weather for a coordinate and return a normalized category.
    """
    api_key = _require_api_key()
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric",
    }

    try:
        response = requests.get(OPENWEATHER_URL, params=params, timeout=15)
        if response.status_code == 401:
            raise WeatherServiceError(
                "Invalid OPENWEATHER_API_KEY — verify the key in .env at openweathermap.org"
            )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        logger.error("OpenWeatherMap request failed for (%s, %s): %s", lat, lon, exc)
        raise WeatherServiceError(f"Weather service unavailable: {exc}") from exc

    weather_items = data.get("weather") or []
    if not weather_items:
        raise WeatherServiceError("OpenWeatherMap returned no weather data")

    main_category = weather_items[0].get("main", "")
    normalized = normalize_weather(main_category)
    logger.info("Weather at (%s, %s): %s -> %s", lat, lon, main_category, normalized)
    return normalized


def extract_midpoint(route_geometry: list[dict]) -> dict:
    """
    Return the middle point of a route polyline as {lat, lng}.
    """
    if not route_geometry:
        raise WeatherServiceError("Route geometry is empty; cannot sample midpoint")

    midpoint_index = len(route_geometry) // 2
    point = route_geometry[midpoint_index]

    if "lat" not in point or "lng" not in point:
        raise WeatherServiceError("Invalid route geometry point format")

    return {"lat": float(point["lat"]), "lng": float(point["lng"])}


def compute_weather_risk(
    pickup_weather: str,
    midpoint_weather: str,
    delivery_weather: str,
) -> str:
    """
    Deterministic route weather risk:
    - Rain at midpoint -> HIGH
    - Rain at both pickup and delivery -> HIGH
    - Rain at either pickup or delivery -> MEDIUM
    - No rain anywhere -> LOW
    """
    pickup_rain = pickup_weather == "RAIN"
    midpoint_rain = midpoint_weather == "RAIN"
    delivery_rain = delivery_weather == "RAIN"

    if midpoint_rain:
        return "HIGH"
    if pickup_rain and delivery_rain:
        return "HIGH"
    if pickup_rain or delivery_rain:
        return "MEDIUM"
    return "LOW"


def build_weather_risk_message(
    weather_risk: str,
    pickup_weather: str,
    midpoint_weather: str,
    delivery_weather: str,
) -> str:
    if weather_risk == "HIGH":
        if midpoint_weather == "RAIN":
            return "Route Risk: HIGH due to rain in transit"
        return "Route Risk: HIGH due to rain at pickup and delivery"
    if weather_risk == "MEDIUM":
        location = "pickup" if pickup_weather == "RAIN" else "delivery"
        return f"Route Risk: MEDIUM due to rain at {location}"
    return "Route Risk: LOW — no rain detected along route"


def route_weather_to_model_category(
    pickup_weather: str,
    midpoint_weather: str,
    delivery_weather: str,
) -> str:
    """Map sampled route weather to the ML model's weather_condition values."""
    if "RAIN" in {pickup_weather, midpoint_weather, delivery_weather}:
        return "rain"
    return "normal"


def fetch_route_weather(route_info: dict) -> dict:
    """
    Sample pickup, midpoint, and delivery coordinates from route_info and fetch weather.
    """
    polyline = route_info.get("route_polyline") or []
    pickup_coords = route_info["pickup_coordinates"]
    delivery_coords = route_info["delivery_coordinates"]
    midpoint_coords = extract_midpoint(polyline)

    pickup_weather = get_weather(pickup_coords["lat"], pickup_coords["lng"])
    midpoint_weather = get_weather(midpoint_coords["lat"], midpoint_coords["lng"])
    delivery_weather = get_weather(delivery_coords["lat"], delivery_coords["lng"])

    weather_risk = compute_weather_risk(
        pickup_weather,
        midpoint_weather,
        delivery_weather,
    )

    return {
        "pickup_weather": pickup_weather,
        "midpoint_weather": midpoint_weather,
        "delivery_weather": delivery_weather,
        "weather_risk": weather_risk,
        "weather_risk_message": build_weather_risk_message(
            weather_risk,
            pickup_weather,
            midpoint_weather,
            delivery_weather,
        ),
        "model_weather_condition": route_weather_to_model_category(
            pickup_weather,
            midpoint_weather,
            delivery_weather,
        ),
        "midpoint_coordinates": midpoint_coords,
    }
