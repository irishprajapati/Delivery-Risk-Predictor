from __future__ import annotations

from datetime import datetime
from typing import Any


# ============================================================
# SAFE CONVERSION HELPERS
# ============================================================
# ============================================================
# PAYMENT NORMALIZATION
# ============================================================

PAYMENT_MAP = {
    "cod": "cod",
    "cash": "cod",
    "cash on delivery": "cod",
    "prepaid": "prepaid",
    "online": "prepaid",
}
def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    if value is None:
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to int."""
    if value is None:
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ============================================================
# CUSTOMER FEATURES
# ============================================================

def build_customer_features(customer) -> dict:
    """
    Build historical customer behaviour features.

    These values must describe behaviour known before the
    current order is dispatched.
    """

    total_orders = _safe_int(
        getattr(customer, "total_orders", 0)
    )

    failed_deliveries = _safe_int(
        getattr(customer, "failed_deliveries", 0)
    )

    unreachable_count = _safe_int(
        getattr(customer, "unreachable_count", 0)
    )

    failure_rate = (
        failed_deliveries / total_orders
        if total_orders > 0
        else 0.0
    )

    unreachable_rate = (
        unreachable_count / total_orders
        if total_orders > 0
        else 0.0
    )

    return {
        "total_orders": total_orders,
        "failed_deliveries": failed_deliveries,
        "failure_rate": round(failure_rate, 4),
        "unreachable_count": unreachable_count,
        "unreachable_rate": round(unreachable_rate, 4),
    }


# ============================================================
# ORDER + TIME FEATURES
# ============================================================

def _classify_day_type(day_of_week: int) -> str:
    """Classify Monday-Friday, Saturday, and Sunday."""
    if day_of_week == 5:
        return "SATURDAY"

    if day_of_week == 6:
        return "SUNDAY"

    return "WEEKDAY"


def _classify_time_period(hour: int) -> str:
    """
    Classify the hour into an operational period.

        00-05 -> NIGHT
        06-07 -> EARLY_MORNING
        08-10 -> MORNING
        11-14 -> MIDDAY
        15-16 -> AFTERNOON
        17-19 -> EVENING
        20-23 -> LATE_NIGHT
    """

    if 0 <= hour <= 5:
        return "NIGHT"

    if 6 <= hour <= 7:
        return "EARLY_MORNING"

    if 8 <= hour <= 10:
        return "MORNING"

    if 11 <= hour <= 14:
        return "MIDDAY"

    if 15 <= hour <= 16:
        return "AFTERNOON"

    if 17 <= hour <= 19:
        return "EVENING"

    return "LATE_NIGHT"


def build_order_features(
    quantity: int,
    total_price: float,
    is_cod: bool,
    prepaid_amount: float = 0.0,
    order_time: datetime | None = None,
) -> dict:
    """Build order, calendar, and time-of-day features."""

    quantity = _safe_int(quantity)
    total_price = _safe_float(total_price)
    prepaid_amount = _safe_float(prepaid_amount)

    payment_method = "cod" if is_cod else "prepaid"

    prepaid_ratio = (
        prepaid_amount / total_price
        if total_price > 0
        else 0.0
    )

    if order_time is None:
        order_time = datetime.now()

    hour = int(order_time.hour)
    day_of_week = int(order_time.weekday())

    day_type = _classify_day_type(day_of_week)
    time_period = _classify_time_period(hour)

    is_weekend = int(day_of_week >= 5)

    is_morning_peak = int(
        8 <= hour <= 10 and not is_weekend
    )

    is_evening_peak = int(
        17 <= hour <= 19 and not is_weekend
    )

    # Temporal context indicators. These are not guarantees
    # that traffic is high; the model learns their relationship
    # from the training data.
    is_school_peak = int(
        (7 <= hour <= 9 or 15 <= hour <= 17)
        and not is_weekend
    )

    is_office_peak = int(
        (8 <= hour <= 10 or 16 <= hour <= 19)
        and not is_weekend
    )

    is_peak_hour = int(
        is_morning_peak or is_evening_peak
    )

    return {
        "quantity": quantity,
        "total_price": round(total_price, 2),
        "payment_method": payment_method,
        "prepaid_amount": round(prepaid_amount, 2),
        "prepaid_ratio": round(prepaid_ratio, 4),
        "hour_of_day": hour,
        "day_of_week": day_of_week,
        "day_type": day_type,
        "time_period": time_period,
        "is_weekend": is_weekend,
        "is_peak_hour": is_peak_hour,
        "is_morning_peak": is_morning_peak,
        "is_evening_peak": is_evening_peak,
        "is_school_peak": is_school_peak,
        "is_office_peak": is_office_peak,
    }


# ============================================================
# LOCATION FEATURES
# ============================================================

def build_location_features(
    location_data: dict | None,
) -> dict:
    """
    Build delivery-location and route features.

    Latitude/longitude remain part of the routing/map subsystem
    and are deliberately excluded from the ML feature vector.
    """

    location_data = location_data or {}

    address_quality = _safe_float(
        location_data.get("address_quality")
    )

    distance_km = _safe_float(
        location_data.get("distance_km")
    )

    estimated_duration = _safe_float(
        location_data.get("estimated_duration")
    )

    location_success_rate = _safe_float(
        location_data.get("location_success_rate")
    )

    is_long_distance = int(distance_km > 15)
    is_long_duration = int(estimated_duration > 60)

    return {
        "address_quality": round(address_quality, 4),
        "distance_km": round(distance_km, 2),
        "estimated_duration": round(estimated_duration, 1),
        "location_success_rate": round(
            location_success_rate, 4
        ),
        "is_long_distance": is_long_distance,
        "is_long_duration": is_long_duration,
    }


# ============================================================
# ENVIRONMENT + TRAFFIC FEATURES
# ============================================================

def _normalize_weather(value: Any) -> str:
    """Normalize weather into the training categories."""

    weather = str(value or "CLEAR").strip().upper()

    aliases = {
        "NORMAL": "CLEAR",
        "SUNNY": "CLEAR",
        "CLOUDS": "CLOUDY",
        "CLOUD": "CLOUDY",
        "DRIZZLE": "RAIN",
        "RAINY": "RAIN",
        "FOGGY": "FOG",
        "MIST": "FOG",
        "THUNDERSTORM": "STORM",
    }

    weather = aliases.get(weather, weather)

    valid_weather = {
        "CLEAR",
        "CLOUDY",
        "FOG",
        "RAIN",
        "STORM",
        "SNOW",
    }

    return (
        weather
        if weather in valid_weather
        else "CLOUDY"
    )


def _normalize_traffic(value: Any) -> str:
    """
    Normalize traffic into the training categories.

    Valid categories:
        LOW
        MEDIUM
        HIGH
        SEVERE

    UNKNOWN/UNAVAILABLE are intentionally not emitted.
    """

    traffic = str(value or "LOW").strip().upper()

    aliases = {
        "LIGHT": "LOW",
        "MODERATE": "MEDIUM",
        "HEAVY": "HIGH",
        "VERY_HIGH": "SEVERE",
    }

    traffic = aliases.get(traffic, traffic)

    valid_traffic = {
        "LOW",
        "MEDIUM",
        "HIGH",
        "SEVERE",
    }

    return (
        traffic
        if traffic in valid_traffic
        else "LOW"
    )


def build_environment_features(
    environment_data: dict | None,
) -> dict:
    """
    Build weather and traffic features.

    traffic_delay_minutes can come from:
        - traffic-aware routing later, or
        - the historical/time-based traffic estimator.

    baseline_duration is used only to derive traffic_delay_ratio.
    """

    environment_data = environment_data or {}

    weather = _normalize_weather(
        environment_data.get("weather", "CLEAR")
    )

    traffic = _normalize_traffic(
        environment_data.get("traffic_level", "LOW")
    )

    rainfall = _safe_float(
        environment_data.get("rainfall")
    )

    temperature = _safe_float(
        environment_data.get("temperature")
    )

    traffic_delay_minutes = _safe_float(
        environment_data.get(
            "traffic_delay_minutes",
            environment_data.get("traffic_delay_min", 0.0),
        )
    )

    baseline_duration = _safe_float(
        environment_data.get(
            "baseline_duration",
            environment_data.get("baseline_duration_min", 0.0),
        )
    )

    traffic_delay_minutes = max(
        traffic_delay_minutes,
        0.0,
    )

    traffic_delay_ratio = (
        traffic_delay_minutes / baseline_duration
        if baseline_duration > 0
        else 0.0
    )

    is_raining = int(
        weather in {"RAIN", "STORM"}
        or rainfall > 0
    )

    is_severe_weather = int(
        weather in {"STORM", "SNOW", "FOG"}
    )

    heavy_rain = int(rainfall >= 10)

    extreme_temperature = int(
        temperature >= 35 or temperature <= 5
    )

    high_traffic = int(
        traffic in {"HIGH", "SEVERE"}
        or traffic_delay_minutes >= 15
    )

    return {
        "weather": weather,
        "rainfall": round(rainfall, 2),
        "temperature": round(temperature, 2),
        "traffic_level": traffic,
        "traffic_delay_minutes": round(
            traffic_delay_minutes,
            2,
        ),
        "traffic_delay_ratio": round(
            max(traffic_delay_ratio, 0.0),
            4,
        ),
        "is_raining": is_raining,
        "is_severe_weather": is_severe_weather,
        "heavy_rain": heavy_rain,
        "extreme_temperature": extreme_temperature,
        "high_traffic": high_traffic,
    }


# ============================================================
# PRE-DISPATCH OPERATIONAL FEATURES
# ============================================================

def build_operational_features(
    operational_data: dict | None,
) -> dict:
    """
    Build operational conditions known before dispatch.

    Included:
        hub_delay_minutes
        route_status
        vehicle_status
        hub_delay

    Deliberately excluded:
        attempt_count
        previous_attempt
        rider_load
        rider_overloaded

    Those belong to the later operational subsystem.
    """

    operational_data = operational_data or {}

    hub_delay_minutes = _safe_float(
        operational_data.get("hub_delay_minutes")
    )

    route_status = str(
        operational_data.get(
            "route_status",
            "NORMAL",
        )
    ).strip().upper()

    vehicle_status = str(
        operational_data.get(
            "vehicle_status",
            "AVAILABLE",
        )
    ).strip().upper()

    valid_route_statuses = {
        "NORMAL",
        "DELAYED",
        "BLOCKED",
    }

    valid_vehicle_statuses = {
        "AVAILABLE",
        "MAINTENANCE",
        "BREAKDOWN",
    }

    if route_status not in valid_route_statuses:
        route_status = "NORMAL"

    if vehicle_status not in valid_vehicle_statuses:
        vehicle_status = "AVAILABLE"

    hub_delay_minutes = max(
        hub_delay_minutes,
        0.0,
    )

    hub_delay = int(
        hub_delay_minutes >= 30
    )

    return {
        "hub_delay_minutes": round(
            hub_delay_minutes,
            2,
        ),
        "route_status": route_status,
        "vehicle_status": vehicle_status,
        "hub_delay": hub_delay,
    }


# ============================================================
# COMPLETE FEATURE VECTOR
# ============================================================

def build_features(
    customer,
    quantity: int,
    total_price: float,
    is_cod: bool,
    prepaid_amount: float = 0.0,
    order_time: datetime | None = None,
    location_data: dict | None = None,
    environment_data: dict | None = None,
    operational_data: dict | None = None,
) -> dict:
    """Build the complete pre-dispatch feature vector."""

    features: dict[str, Any] = {}

    features.update(
        build_customer_features(customer)
    )

    features.update(
        build_order_features(
            quantity=quantity,
            total_price=total_price,
            is_cod=is_cod,
            prepaid_amount=prepaid_amount,
            order_time=order_time,
        )
    )

    features.update(
        build_location_features(location_data)
    )

    features.update(
        build_environment_features(environment_data)
    )

    features.update(
        build_operational_features(operational_data)
    )

    validate_feature_contract(features)

    return features


# ============================================================
# FINAL ML FEATURE CONTRACT
# ============================================================

MODEL_FEATURES = [
    # CUSTOMER
    "total_orders",
    "failed_deliveries",
    "failure_rate",
    "unreachable_count",
    "unreachable_rate",

    # ORDER + TIME
    "quantity",
    "total_price",
    "payment_method",
    "prepaid_amount",
    "prepaid_ratio",
    "hour_of_day",
    "day_of_week",
    "day_type",
    "time_period",
    "is_weekend",
    "is_peak_hour",
    "is_morning_peak",
    "is_evening_peak",
    "is_school_peak",
    "is_office_peak",

    # LOCATION
    "address_quality",
    "distance_km",
    "estimated_duration",
    "location_success_rate",
    "is_long_distance",
    "is_long_duration",

    # ENVIRONMENT + TRAFFIC
    "weather",
    "rainfall",
    "temperature",
    "traffic_level",
    "traffic_delay_minutes",
    "traffic_delay_ratio",
    "is_raining",
    "is_severe_weather",
    "heavy_rain",
    "extreme_temperature",
    "high_traffic",

    # PRE-DISPATCH OPERATIONS
    "hub_delay_minutes",
    "route_status",
    "vehicle_status",
    "hub_delay",
]


# ============================================================
# FEATURE CONTRACT VALIDATION
# ============================================================

def validate_feature_contract(
    features: dict[str, Any],
) -> None:
    """Ensure generated features exactly match MODEL_FEATURES."""

    expected = set(MODEL_FEATURES)
    actual = set(features.keys())

    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)

    if missing:
        raise ValueError(
            "Missing model features: "
            + ", ".join(missing)
        )

    if unexpected:
        raise ValueError(
            "Unexpected model features: "
            + ", ".join(unexpected)
        )