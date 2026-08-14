"""
Weather service for pre-dispatch delivery prediction.

Responsibilities:

1. Fetch current weather from OpenWeatherMap.
2. Normalize weather categories to the ML contract.
3. Sample weather at:
       - pickup
       - route midpoint
       - delivery
4. Aggregate route-level weather conditions.
5. Calculate environmental severity.
6. Return weather-risk metadata for API/explainability layers.

This module does NOT:
- calculate final delivery failure probability
- calculate traffic
- access the database
- call the ML model

Traffic belongs to:
    app/services/traffic_service.py
"""

from __future__ import annotations

import logging
import math
import os
from pathlib import Path

import requests
from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

_PROJECT_ROOT = (
    Path(__file__).resolve()
    .parent.parent.parent
)

load_dotenv(
    _PROJECT_ROOT / ".env"
)

logger = logging.getLogger(__name__)

OPENWEATHER_API_KEY = os.getenv(
    "OPENWEATHER_API_KEY"
)

OPENWEATHER_URL = (
    "https://api.openweathermap.org/data/2.5/weather"
)


# ============================================================
# EXCEPTION
# ============================================================

class WeatherServiceError(Exception):
    """Raised when the weather service fails."""


# ============================================================
# SAFE HELPERS
# ============================================================

def _safe_float(
    value,
    default: float = 0.0,
) -> float:
    """Convert to a finite float safely."""

    if value is None:
        return default

    try:
        result = float(value)

        if not math.isfinite(result):
            return default

        return result

    except (
        TypeError,
        ValueError,
    ):
        return default


# ============================================================
# WEATHER NORMALIZATION
# ============================================================

def normalize_weather(
    main_category: str,
) -> str:
    """
    Normalize OpenWeatherMap categories into the ML contract.

    Allowed values:

        CLEAR
        CLOUDY
        RAIN
        STORM
        SNOW
        FOG
    """

    category = str(
        main_category or ""
    ).strip().lower()

    if category == "clear":
        return "CLEAR"

    if category == "clouds":
        return "CLOUDY"

    if category in {
        "rain",
        "drizzle",
    }:
        return "RAIN"

    if category == "thunderstorm":
        return "STORM"

    if category == "snow":
        return "SNOW"

    if category in {
        "mist",
        "smoke",
        "haze",
        "dust",
        "fog",
        "sand",
        "ash",
        "squall",
        "tornado",
    }:
        return "FOG"

    return "CLOUDY"


# ============================================================
# API KEY
# ============================================================

def _require_api_key() -> str:
    if not OPENWEATHER_API_KEY:
        raise WeatherServiceError(
            "OPENWEATHER_API_KEY is not configured in .env"
        )

    return OPENWEATHER_API_KEY


# ============================================================
# COORDINATE VALIDATION
# ============================================================

def _validate_coordinates(
    lat: float,
    lon: float,
) -> None:
    """Validate a weather coordinate pair."""

    lat = _safe_float(lat)
    lon = _safe_float(lon)

    if not (
        -90 <= lat <= 90
    ):
        raise WeatherServiceError(
            "Invalid weather latitude."
        )

    if not (
        -180 <= lon <= 180
    ):
        raise WeatherServiceError(
            "Invalid weather longitude."
        )


# ============================================================
# CURRENT WEATHER
# ============================================================

def get_weather(
    lat: float,
    lon: float,
) -> dict:
    """
    Fetch current weather for one coordinate.

    Returns:

        {
            "weather": "RAIN",
            "temperature": 24.5,
            "rainfall": 2.4,
            "humidity": 82,
            "wind_speed": 3.2
        }

    Rainfall is normalized to an approximate mm/hour value.
    """

    _validate_coordinates(
        lat,
        lon,
    )

    api_key = _require_api_key()

    params = {
        "lat": float(lat),
        "lon": float(lon),
        "appid": api_key,
        "units": "metric",
    }

    try:
        response = requests.get(
            OPENWEATHER_URL,
            params=params,
            timeout=15,
        )

    except requests.RequestException as exc:

        logger.error(
            "OpenWeatherMap request failed "
            "for (%s, %s): %s",
            lat,
            lon,
            exc,
        )

        raise WeatherServiceError(
            "Weather service unavailable."
        ) from exc

    if response.status_code == 401:
        raise WeatherServiceError(
            "Invalid OPENWEATHER_API_KEY."
        )

    try:
        response.raise_for_status()
        data = response.json()

    except (
        requests.RequestException,
        ValueError,
    ) as exc:

        logger.error(
            "Invalid OpenWeatherMap response "
            "for (%s, %s): %s",
            lat,
            lon,
            exc,
        )

        raise WeatherServiceError(
            "Invalid weather service response."
        ) from exc

    weather_items = (
        data.get("weather")
        or []
    )

    if not weather_items:
        raise WeatherServiceError(
            "OpenWeatherMap returned no weather information."
        )

    raw_weather = weather_items[0].get(
        "main",
        "",
    )

    weather = normalize_weather(
        raw_weather
    )

    main = (
        data.get("main")
        or {}
    )

    temperature = _safe_float(
        main.get("temp")
    )

    humidity = max(
        0.0,
        min(
            _safe_float(
                main.get("humidity")
            ),
            100.0,
        ),
    )

    wind = (
        data.get("wind")
        or {}
    )

    wind_speed = max(
        0.0,
        _safe_float(
            wind.get("speed")
        ),
    )

    rain = (
        data.get("rain")
        or {}
    )

    rainfall = 0.0

    if "1h" in rain:

        rainfall = max(
            0.0,
            _safe_float(
                rain.get("1h")
            ),
        )

    elif "3h" in rain:

        rainfall = max(
            0.0,
            _safe_float(
                rain.get("3h")
            ) / 3.0,
        )

    logger.info(
        "Weather (%s, %s): %s | "
        "temp=%.2f°C | rainfall=%.2f mm | "
        "humidity=%.1f%% | wind=%.2f m/s",
        lat,
        lon,
        weather,
        temperature,
        rainfall,
        humidity,
        wind_speed,
    )

    return {
        "weather": weather,
        "temperature": round(
            temperature,
            2,
        ),
        "rainfall": round(
            rainfall,
            2,
        ),
        "humidity": round(
            humidity,
            2,
        ),
        "wind_speed": round(
            wind_speed,
            2,
        ),
    }


# ============================================================
# ROUTE MIDPOINT
# ============================================================

def extract_midpoint(
    route_geometry: list[dict],
) -> dict:
    """
    Extract the midpoint coordinate from an ORS route polyline.
    """

    if not route_geometry:
        raise WeatherServiceError(
            "Route geometry is empty; "
            "cannot determine midpoint."
        )

    midpoint_index = (
        len(route_geometry) // 2
    )

    point = route_geometry[
        midpoint_index
    ]

    if (
        "lat" not in point
        or "lng" not in point
    ):
        raise WeatherServiceError(
            "Invalid route geometry point format."
        )

    lat = _safe_float(
        point["lat"]
    )

    lng = _safe_float(
        point["lng"]
    )

    _validate_coordinates(
        lat,
        lng,
    )

    return {
        "lat": lat,
        "lng": lng,
    }


# ============================================================
# WEATHER SEVERITY
# ============================================================

def calculate_weather_severity(
    weather: str,
    rainfall: float,
    temperature: float,
    wind_speed: float,
) -> float:
    """
    Calculate environmental severity from 0 to 1.

    This is NOT final delivery failure probability.
    """

    weather = normalize_weather(
        weather
    )

    rainfall = max(
        0.0,
        _safe_float(
            rainfall
        ),
    )

    temperature = _safe_float(
        temperature
    )

    wind_speed = max(
        0.0,
        _safe_float(
            wind_speed
        ),
    )

    severity = 0.0

    if weather == "CLEAR":
        severity += 0.0

    elif weather == "CLOUDY":
        severity += 0.05

    elif weather == "FOG":
        severity += 0.15

    elif weather == "RAIN":
        severity += 0.25

    elif weather in {
        "STORM",
        "SNOW",
    }:
        severity += 0.50

    if rainfall >= 20:
        severity += 0.35

    elif rainfall >= 10:
        severity += 0.25

    elif rainfall >= 5:
        severity += 0.15

    elif rainfall > 0:
        severity += 0.05

    if (
        temperature >= 35
        or temperature <= 5
    ):
        severity += 0.10

    if wind_speed >= 15:
        severity += 0.15

    elif wind_speed >= 10:
        severity += 0.10

    return round(
        min(
            max(
                severity,
                0.0,
            ),
            1.0,
        ),
        2,
    )


# ============================================================
# WEATHER RISK MAPPING
# ============================================================

def classify_weather_risk(
    severity: float,
) -> str:
    """
    Map environmental severity to an operational weather risk.
    """

    severity = max(
        0.0,
        min(
            _safe_float(
                severity
            ),
            1.0,
        ),
    )

    if severity >= 0.70:
        return "SEVERE"

    if severity >= 0.40:
        return "HIGH"

    if severity >= 0.15:
        return "MEDIUM"

    return "LOW"


def build_weather_risk_message(
    weather_risk: str,
    route_weather: str,
) -> str | None:
    """
    Build a human-readable operational weather message.
    """

    if weather_risk == "SEVERE":
        return (
            f"Severe route weather detected "
            f"({route_weather}). Consider delaying "
            "or manually reviewing dispatch."
        )

    if weather_risk == "HIGH":
        return (
            f"High route weather risk detected "
            f"({route_weather}). Consider additional "
            "delivery precautions."
        )

    if weather_risk == "MEDIUM":
        return (
            f"Moderate route weather risk detected "
            f"({route_weather})."
        )

    return None


# ============================================================
# ROUTE WEATHER
# ============================================================

def fetch_route_weather(
    route_info: dict,
) -> dict:
    """
    Fetch weather at:

        1. pickup
        2. route midpoint
        3. delivery

    Then aggregate the results into route-level environmental
    information.
    """

    if not isinstance(
        route_info,
        dict,
    ):
        raise WeatherServiceError(
            "route_info must be a dictionary."
        )

    polyline = (
        route_info.get(
            "route_polyline"
        )
        or []
    )

    pickup_coords = route_info.get(
        "pickup_coordinates"
    )

    delivery_coords = route_info.get(
        "delivery_coordinates"
    )

    if not pickup_coords:
        raise WeatherServiceError(
            "Pickup coordinates are missing."
        )

    if not delivery_coords:
        raise WeatherServiceError(
            "Delivery coordinates are missing."
        )

    pickup_lat = pickup_coords.get(
        "lat"
    )

    pickup_lng = pickup_coords.get(
        "lng"
    )

    delivery_lat = delivery_coords.get(
        "lat"
    )

    delivery_lng = delivery_coords.get(
        "lng"
    )

    _validate_coordinates(
        pickup_lat,
        pickup_lng,
    )

    _validate_coordinates(
        delivery_lat,
        delivery_lng,
    )

    midpoint_coords = extract_midpoint(
        polyline
    )

    pickup = get_weather(
        pickup_lat,
        pickup_lng,
    )

    midpoint = get_weather(
        midpoint_coords["lat"],
        midpoint_coords["lng"],
    )

    delivery = get_weather(
        delivery_lat,
        delivery_lng,
    )

    weather_points = [
        pickup,
        midpoint,
        delivery,
    ]

    rainfall_values = [
        point["rainfall"]
        for point in weather_points
    ]

    temperature_values = [
        point["temperature"]
        for point in weather_points
    ]

    severity_values = [
        calculate_weather_severity(
            weather=point["weather"],
            rainfall=point["rainfall"],
            temperature=point["temperature"],
            wind_speed=point["wind_speed"],
        )
        for point in weather_points
    ]

    maximum_rainfall = max(
        rainfall_values
    )

    average_temperature = (
        sum(
            temperature_values
        )
        / len(
            temperature_values
        )
    )

    maximum_weather_severity = max(
        severity_values
    )

    adverse_points = sum(
        1
        for point in weather_points
        if point["weather"]
        in {
            "RAIN",
            "STORM",
            "SNOW",
            "FOG",
        }
    )

    # Route weather is based on the maximum observed
    # environmental severity across the sampled points.

    if maximum_weather_severity >= 0.70:
        route_weather = "SEVERE"

    elif maximum_weather_severity >= 0.40:
        route_weather = "HIGH"

    elif maximum_weather_severity >= 0.15:
        route_weather = "MODERATE"

    else:
        route_weather = "LOW"

    weather_risk = classify_weather_risk(
        maximum_weather_severity
    )

    weather_risk_message = (
        build_weather_risk_message(
            weather_risk=weather_risk,
            route_weather=route_weather,
        )
    )

    return {
        # Raw route samples
        "pickup": pickup,
        "midpoint": midpoint,
        "delivery": delivery,

        # Simple normalized labels
        "pickup_weather": pickup[
            "weather"
        ],

        "midpoint_weather": midpoint[
            "weather"
        ],

        "delivery_weather": delivery[
            "weather"
        ],

        # Aggregates
        "maximum_rainfall": round(
            maximum_rainfall,
            2,
        ),

        "average_temperature": round(
            average_temperature,
            2,
        ),

        "maximum_weather_severity": (
            maximum_weather_severity
        ),

        "adverse_weather_points": (
            adverse_points
        ),

        # Operational weather state
        "route_weather": (
            route_weather
        ),

        "weather_risk": (
            weather_risk
        ),

        "weather_risk_message": (
            weather_risk_message
        ),

        "midpoint_coordinates": (
            midpoint_coords
        ),
    }