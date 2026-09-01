"""
Standalone pre-dispatch delivery-failure prediction endpoint.

Flow:

    Request
      ↓
    Request/schema validation
      ↓
    Customer lookup + verification
      ↓
    Map coordinates OR address geocoding
      ↓
    Baseline road route
      ↓
    Route weather
      ↓
    Traffic estimation
      ↓
    Feature engineering
      ↓
    Trained ML model
      ↓
    Failure probability
      ↓
    Risk level
      ↓
    Structured response

This endpoint:

- does NOT create orders
- does NOT persist predictions
- does NOT assign riders
- does NOT block orders
- does NOT calculate a second hand-written risk score

It is the prediction/orchestration layer only.
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.ml.predictor import predict
from app.model import Customer
from app.schemas import PredictionInput

from app.services.feature_engineering import build_features

from app.services.ors_service import (
    LocationValidationError,
    ORSServiceError,
    build_route_info,
)

from app.services.traffic_service import (
    build_traffic_context,
)

from app.services.weather_service import (
    WeatherServiceError,
    fetch_route_weather,
)

from app.utils.dependencies import get_current_user


logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# DATABASE
# ============================================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ============================================================
# AUTHORIZATION
# ============================================================

def _is_admin_user(current_user) -> bool:
    """
    Support both:
        - dictionary-style authenticated user
        - SQLAlchemy User object

    This keeps the route robust against dependency implementation
    differences elsewhere in the application.
    """

    if isinstance(
        current_user,
        dict,
    ):
        return (
            current_user.get("role")
            == "admin"
        )

    return (
        getattr(
            current_user,
            "role",
            None,
        )
        == "admin"
    )


# ============================================================
# WEATHER HELPERS
# ============================================================

def _extract_weather_point(
    weather_info: dict,
    key: str,
) -> dict:
    """
    Extract a structured weather sample.

    Preferred structure:

        weather_info["pickup"] = {
            "weather": "...",
            "rainfall": ...,
            "temperature": ...
        }

    Falls back safely if only a weather string exists.
    """

    value = weather_info.get(
        key
    )

    if isinstance(
        value,
        dict,
    ):
        return value

    return {
        "weather": (
            value
            if isinstance(
                value,
                str,
            )
            else "CLEAR"
        ),
        "rainfall": 0.0,
        "temperature": 0.0,
    }


def _extract_route_weather_inputs(
    weather_info: dict,
) -> tuple[str, float, float]:
    """
    Convert pickup/midpoint/delivery weather into one route-level
    representation used by feature engineering.

    Weather:
        midpoint weather is the representative route condition.

    Rainfall:
        maximum rainfall across sampled points.

    Temperature:
        average valid temperature across sampled points.
    """

    pickup = _extract_weather_point(
        weather_info,
        "pickup",
    )

    midpoint = _extract_weather_point(
        weather_info,
        "midpoint",
    )

    delivery = _extract_weather_point(
        weather_info,
        "delivery",
    )

    midpoint_weather = (
        midpoint.get("weather")
        or midpoint.get("condition")
        or weather_info.get(
            "midpoint_weather",
            "CLEAR",
        )
    )

    rainfall_values = [
        float(
            pickup.get(
                "rainfall",
                0.0,
            )
            or 0.0
        ),
        float(
            midpoint.get(
                "rainfall",
                0.0,
            )
            or 0.0
        ),
        float(
            delivery.get(
                "rainfall",
                0.0,
            )
            or 0.0
        ),
    ]

    temperature_values = [
        float(
            pickup.get(
                "temperature",
                0.0,
            )
            or 0.0
        ),
        float(
            midpoint.get(
                "temperature",
                0.0,
            )
            or 0.0
        ),
        float(
            delivery.get(
                "temperature",
                0.0,
            )
            or 0.0
        ),
    ]

    rainfall = max(
        rainfall_values
    )

    valid_temperatures = [
        value
        for value in temperature_values
        if value != 0.0
    ]

    temperature = (
        sum(valid_temperatures)
        / len(valid_temperatures)
        if valid_temperatures
        else 0.0
    )

    return (
        str(
            midpoint_weather
        ).upper(),
        round(
            rainfall,
            2,
        ),
        round(
            temperature,
            2,
        ),
    )


# ============================================================
# LOCATION FEATURE HELPERS
# ============================================================

def calculate_address_quality(
    address: str,
) -> float:
    """
    Temporary address-quality heuristic.

    IMPORTANT:
    This is NOT historical location success.

    The real historical location-success subsystem will replace
    the neutral location-history fallback later.
    """

    address = (
        address or ""
    ).strip()

    if not address:
        return 0.0

    score = 0.0

    if len(address) >= 20:
        score += 0.35

    elif len(address) >= 10:
        score += 0.20

    address_lower = address.lower()

    location_terms = [
        "road",
        "street",
        "ward",
        "tole",
        "chowk",
        "area",
        "marg",
        "nagar",
        "lane",
        "house",
        "building",
    ]

    if any(
        term in address_lower
        for term in location_terms
    ):
        score += 0.35

    if any(
        character.isdigit()
        for character in address
    ):
        score += 0.30

    return round(
        min(
            score,
            1.0,
        ),
        4,
    )


def get_location_success_rate(
    db: Session,
    address: str,
) -> float:
    """
    Temporary neutral value.

    0.50 means unknown, not a measured real-world statistic.
    """

    _ = db
    _ = address

    return 0.50


# ============================================================
# PREDICTION ENDPOINT
# ============================================================

@router.post("/predict")
def predict_delivery(
    data: PredictionInput,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Generate a pre-dispatch delivery-failure prediction.

    Admin only.
    """

    # ========================================================
    # AUTHORIZATION
    # ========================================================

    if not _is_admin_user(
        current_user
    ):
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    # ========================================================
    # CUSTOMER
    # ========================================================

    customer = (
        db.query(Customer)
        .filter(
            Customer.phone
            == data.phone_number
        )
        .first()
    )

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    if not customer.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Customer is not verified",
        )

    # ========================================================
    # LOCATION + BASELINE ROUTE
    # ========================================================

    try:
        route_info = build_route_info(
            pickup_address=(
                data.pickup_address
            ),
            delivery_address=(
                data.delivery_address
            ),
            pickup_latitude=(
                data.pickup_latitude
            ),
            pickup_longitude=(
                data.pickup_longitude
            ),
            delivery_latitude=(
                data.delivery_latitude
            ),
            delivery_longitude=(
                data.delivery_longitude
            ),
        )

    except LocationValidationError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except ORSServiceError as exc:
        # Safe fallback for ORS failures - use estimates instead of failing completely
        logger.warning(
            f"ORS service failed for prediction, using fallback estimates: {exc}"
        )
        
        # Use provided coordinates if available, otherwise estimate
        distance_km = 5.0
        baseline_duration = 20.0
        
        if data.delivery_latitude and data.delivery_longitude:
            # If coordinates are supplied, we can at least validate they're in Nepal
            # and use a neutral estimate
            try:
                from app.services.ors_service import _validate_coordinates
                _validate_coordinates(
                    data.delivery_latitude,
                    data.delivery_longitude
                )
                # If valid, use a slightly better estimate based on general distance
                distance_km = 8.0
                baseline_duration = 30.0
            except Exception:
                pass  # Use defaults if validation fails
        
        route_info = {
            "estimated_distance_km": distance_km,
            "baseline_duration_min": baseline_duration,
            "estimated_duration_min": baseline_duration,
            "pickup_district": "Kathmandu",
            "delivery_district": "Kathmandu",
            "pickup_coordinates": {
                "lat": data.pickup_latitude or 27.6710,
                "lng": data.pickup_longitude or 85.3380,
            },
            "delivery_coordinates": {
                "lat": data.delivery_latitude or 27.7172,
                "lng": data.delivery_longitude or 85.3240,
            },
            "route_source": "fallback_estimate",
            "route_polyline": [],
        }

    # ========================================================
    # WEATHER
    # ========================================================

    try:
        weather_info = fetch_route_weather(
            route_info
        )

    except WeatherServiceError as exc:
        # Safe fallback for weather service failures
        logger.warning(
            f"Weather service failed for prediction, using fallback: {exc}"
        )
        
        weather_info = {
            "pickup": {
                "weather": "CLEAR",
                "rainfall": 0.0,
                "temperature": 22.0,
            },
            "midpoint": {
                "weather": "CLEAR",
                "rainfall": 0.0,
                "temperature": 22.0,
            },
            "delivery": {
                "weather": "CLEAR",
                "rainfall": 0.0,
                "temperature": 22.0,
            },
            "route_weather": "CLEAR",
            "weather_risk": "LOW",
            "maximum_rainfall": 0.0,
            "average_temperature": 22.0,
        }

    (
        route_weather,
        rainfall,
        temperature,
    ) = _extract_route_weather_inputs(
        weather_info
    )

    # ========================================================
    # TRAFFIC
    # ========================================================

    try:
        traffic_context = build_traffic_context(
            route_info=route_info,
            weather_info=weather_info,
            order_time=datetime.now(),
            historical_delay_minutes=None,
        )

    except ValueError as exc:

        logger.exception(
            "Traffic context validation failed"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Traffic context validation failed: "
                f"{exc}"
            ),
        ) from exc

    except Exception as exc:

        logger.exception(
            "Traffic estimation failed"
        )

        raise HTTPException(
            status_code=503,
            detail="Traffic estimation service failed",
        ) from exc

    traffic_level = traffic_context[
        "traffic_level"
    ]

    traffic_delay_minutes = (
        traffic_context[
            "traffic_delay_minutes"
        ]
    )

    traffic_delay_ratio = (
        traffic_context[
            "traffic_delay_ratio"
        ]
    )

    traffic_source = traffic_context[
        "traffic_source"
    ]

    baseline_duration = traffic_context[
        "baseline_duration_min"
    ]

    estimated_duration_with_traffic = (
        traffic_context[
            "estimated_duration_min"
        ]
    )

    # ========================================================
    # LOCATION FEATURES
    # ========================================================

    address_quality = (
        calculate_address_quality(
            data.delivery_address
        )
    )

    location_success_rate = (
        get_location_success_rate(
            db=db,
            address=data.delivery_address,
        )
    )

    location_data = {
        "address_quality": (
            address_quality
        ),

        "distance_km": route_info[
            "estimated_distance_km"
        ],

        # IMPORTANT:
        # The ML feature "estimated_duration" must represent
        # the same operational quantity used during training.
        #
        # We use the traffic-adjusted ETA here because traffic
        # is one of the factors available before dispatch.
        "estimated_duration": (
        baseline_duration
    ),

        "location_success_rate": (
            location_success_rate
        ),
    }

    # ========================================================
    # ENVIRONMENT + TRAFFIC
    # ========================================================

    environment_data = {
        "weather": route_weather,

        "rainfall": rainfall,

        "temperature": temperature,

        "traffic_level": (
            traffic_level
        ),

        "traffic_delay_minutes": (
            traffic_delay_minutes
        ),

        "baseline_duration": (
            baseline_duration
        ),
    }

    # ========================================================
    # PRE-DISPATCH OPERATIONS
    # ========================================================

    operational_data = {
        "hub_delay_minutes": 0.0,
        "route_status": "NORMAL",
        "vehicle_status": "AVAILABLE",
    }

    # ========================================================
    # ORDER FEATURES
    # ========================================================

    payment_method = (
        data.payment_method
        .strip()
        .lower()
    )

    is_cod = (
        payment_method == "cod"
    )

    quantity = data.quantity

    prepaid_amount = (
        data.prepaid_amount
    )

    # ========================================================
    # FEATURE ENGINEERING
    # ========================================================

    order_time = datetime.now()

    try:

        features = build_features(
            customer=customer,

            quantity=quantity,

            total_price=data.order_value,

            is_cod=is_cod,

            prepaid_amount=prepaid_amount,

            order_time=order_time,

            location_data=location_data,

            environment_data=environment_data,

            operational_data=operational_data,
        )

    except ValueError as exc:

        logger.exception(
            "Feature contract validation failed"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Feature engineering failed: "
                f"{exc}"
            ),
        ) from exc

    except Exception as exc:

        logger.exception(
            "Feature engineering failed"
        )

        raise HTTPException(
            status_code=500,
            detail="Feature engineering failed",
        ) from exc

    logger.info(
        "Generated pre-dispatch model features: %s",
        features,
    )

    # ========================================================
    # MACHINE LEARNING
    # ========================================================

    try:

        result = predict(
            features
        )

    except Exception as exc:

        logger.exception(
            "Prediction service raised an exception"
        )

        raise HTTPException(
            status_code=500,
            detail="Prediction service failed",
        ) from exc

    if not result.get(
        "success"
    ):
        raise HTTPException(
            status_code=500,
            detail=result.get(
                "detail",
                "Prediction failed",
            ),
        )

    # ========================================================
    # RESPONSE
    # ========================================================

    return {
        "prediction": result[
            "prediction"
        ],

        "probability": result[
            "probability"
        ],

        "risk": result[
            "risk"
        ],

        "phone_number": (
            data.phone_number
        ),

        "customer": {
            "id": customer.id,

            "total_orders": (
                customer.total_orders
                or 0
            ),

            "failed_deliveries": (
                customer.failed_deliveries
                or 0
            ),

            "unreachable_count": (
                customer.unreachable_count
                or 0
            ),
        },

        "route": {
            "distance_km": (
                route_info[
                    "estimated_distance_km"
                ]
            ),

            "baseline_duration_min": (
                baseline_duration
            ),

            "estimated_duration_min": (
                estimated_duration_with_traffic
            ),

            "traffic_level": (
                traffic_level
            ),

            "traffic_delay_min": (
                traffic_delay_minutes
            ),

            "traffic_delay_ratio": (
                traffic_delay_ratio
            ),

            "traffic_source": (
                traffic_source
            ),

            "pickup_district": (
                route_info[
                    "pickup_district"
                ]
            ),

            "delivery_district": (
                route_info[
                    "delivery_district"
                ]
            ),

            "pickup_coordinates": (
                route_info[
                    "pickup_coordinates"
                ]
            ),

            "delivery_coordinates": (
                route_info[
                    "delivery_coordinates"
                ]
            ),

            "pickup_location_source": (
                route_info.get(
                    "pickup_location_source"
                )
            ),

            "delivery_location_source": (
                route_info.get(
                    "delivery_location_source"
                )
            ),

            "pickup_label": (
                route_info.get(
                    "pickup_label"
                )
            ),

            "delivery_label": (
                route_info.get(
                    "delivery_label"
                )
            ),

            "route_source": (
                route_info.get(
                    "route_source"
                )
            ),

            "route_polyline": (
                route_info.get(
                    "route_polyline",
                    [],
                )
            ),
        },

        "weather": {
            "pickup": weather_info.get(
                "pickup_weather"
            ),

            "midpoint": weather_info.get(
                "midpoint_weather"
            ),

            "delivery": weather_info.get(
                "delivery_weather"
            ),

            "rainfall": round(
                rainfall,
                2,
            ),

            "temperature": round(
                temperature,
                2,
            ),

            "route_weather": (
                weather_info.get(
                    "route_weather",
                    "LOW",
                )
            ),

            "weather_risk": (
                weather_info.get(
                    "weather_risk",
                    "LOW",
                )
            ),

            "weather_risk_message": (
                weather_info.get(
                    "weather_risk_message"
                )
            ),
        },

        "features": features,
    }