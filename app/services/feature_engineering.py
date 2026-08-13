from __future__ import annotations

from datetime import datetime
from typing import Any

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


def build_customer_features(customer) -> dict:
    """
    Build historical customer behaviour features.

    These features must represent information that was known
    before the current order was dispatched.
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

def build_order_features(
    quantity: int,
    total_price: float,
    is_cod: bool,
    prepaid_amount: float = 0.0,
    order_time: datetime | None = None,
) -> dict:
    """
    Build order-related features.
    """

    quantity = _safe_int(quantity)

    total_price = _safe_float(total_price)

    prepaid_amount = _safe_float(prepaid_amount)

    # Keep this as a categorical string.
    # train_model.py will use OneHotEncoder.
    payment_method = "cod" if is_cod else "prepaid"

    prepaid_ratio = (
        prepaid_amount / total_price
        if total_price > 0
        else 0.0
    )

    if order_time is None:
        order_time = datetime.now()

    hour = order_time.hour

    day_of_week = order_time.weekday()

    is_peak_hour = int(
        8 <= hour <= 10
        or 17 <= hour <= 19
    )

    return {
        "quantity": quantity,
        "total_price": total_price,
        "payment_method": payment_method,
        "prepaid_amount": prepaid_amount,
        "prepaid_ratio": round(prepaid_ratio, 4),
        "hour_of_day": hour,
        "day_of_week": day_of_week,
        "is_peak_hour": is_peak_hour,
    }


# ============================================================
# LOCATION FEATURES
# ============================================================

def build_location_features(
    location_data: dict | None,
) -> dict:
    """
    Build delivery-location and route features.

    Latitude and longitude are deliberately kept out of the
    ML feature vector. They remain important for maps and
    route services but are not directly used by the model.
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

    is_long_distance = int(
        distance_km > 15
    )

    is_long_duration = int(
        estimated_duration > 60
    )

    return {
        "address_quality": address_quality,
        "distance_km": distance_km,
        "estimated_duration": estimated_duration,
        "location_success_rate": location_success_rate,
        "is_long_distance": is_long_distance,
        "is_long_duration": is_long_duration,
    }

def build_environment_features(
    environment_data: dict | None,
) -> dict:
    """
    Build weather and traffic features.

    Categorical values remain strings so that the training
    pipeline can handle them using OneHotEncoder.
    """

    environment_data = environment_data or {}

    weather = str(
        environment_data.get(
            "weather",
            "CLEAR",
        )
    ).strip().upper()

    traffic = str(
        environment_data.get(
            "traffic_level",
            "LOW",
        )
    ).strip().upper()

    rainfall = _safe_float(
        environment_data.get("rainfall")
    )

    temperature = _safe_float(
        environment_data.get("temperature")
    )

    is_raining = int(
        weather in {"RAIN", "STORM"}
        or rainfall > 0
    )

    is_severe_weather = int(
        weather in {
            "STORM",
            "SNOW",
            "FOG",
        }
    )

    heavy_rain = int(
        rainfall >= 10
    )

    extreme_temperature = int(
        temperature >= 35
        or temperature <= 5
    )

    high_traffic = int(
        traffic in {
            "HIGH",
            "SEVERE",
        }
    )

    return {
        "weather": weather,
        "rainfall": rainfall,
        "temperature": temperature,
        "traffic_level": traffic,
        "is_raining": is_raining,
        "is_severe_weather": is_severe_weather,
        "heavy_rain": heavy_rain,
        "extreme_temperature": extreme_temperature,
        "high_traffic": high_traffic,
    }



def build_operational_features(
    operational_data: dict | None,
) -> dict:
    """
    Build operational conditions that are available
    before the delivery is dispatched.

    Important:
    We deliberately DO NOT use:

        attempt_count
        previous_attempt
        rider_load
        rider_overloaded

    as initial prediction features.

    Those values either occur after an attempt or depend on
    rider assignment. They belong to the operational system
    and database, but should not leak into the initial
    pre-dispatch prediction.
    """

    operational_data = operational_data or {}

    hub_delay_minutes = _safe_float(
        operational_data.get(
            "hub_delay_minutes"
        )
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

    hub_delay = int(
        hub_delay_minutes >= 30
    )

    return {
        "hub_delay_minutes": hub_delay_minutes,
        "route_status": route_status,
        "vehicle_status": vehicle_status,
        "hub_delay": hub_delay,
    }


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
    """
    Build the complete pre-dispatch feature vector.

    Feature groups:

        CUSTOMER
        ORDER
        LOCATION
        ENVIRONMENT
        OPERATIONS
    """

    features = {}

    # Customer
    features.update(
        build_customer_features(customer)
    )

    # Order
    features.update(
        build_order_features(
            quantity=quantity,
            total_price=total_price,
            is_cod=is_cod,
            prepaid_amount=prepaid_amount,
            order_time=order_time,
        )
    )

    # Location
    features.update(
        build_location_features(
            location_data
        )
    )

    # Environment
    features.update(
        build_environment_features(
            environment_data
        )
    )

    # Operations
    features.update(
        build_operational_features(
            operational_data
        )
    )

    return features


MODEL_FEATURES = [


    "total_orders",
    "failed_deliveries",
    "failure_rate",
    "unreachable_count",
    "unreachable_rate",

    "quantity",
    "total_price",
    "payment_method",
    "prepaid_amount",
    "prepaid_ratio",
    "hour_of_day",
    "day_of_week",
    "is_peak_hour",

    "address_quality",
    "distance_km",
    "estimated_duration",
    "location_success_rate",
    "is_long_distance",
    "is_long_duration",
    "weather",
    "rainfall",
    "temperature",
    "traffic_level",
    "is_raining",
    "is_severe_weather",
    "heavy_rain",
    "extreme_temperature",
    "high_traffic",

    "hub_delay_minutes",
    "route_status",
    "vehicle_status",
    "hub_delay",
]