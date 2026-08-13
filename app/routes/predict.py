"""
Standalone pre-dispatch delivery-failure prediction endpoint.

Flow:

    Request
      ↓
    Customer lookup
      ↓
    ORS route information
      ↓
    Route weather
      ↓
    Feature engineering
      ↓
    Trained ML model
      ↓
    Failure probability
      ↓
    Risk level

This endpoint is for testing/admin prediction.

Order creation and persistence are handled separately by
the order-placement flow.
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
from app.services.ors_service import (
    LocationValidationError,
    ORSServiceError,
)
from app.services.weather_service import (
    WeatherServiceError,
    fetch_route_weather,
)
from app.utils.dependencies import get_current_user
from app.utils.feature_engineering import build_features
from app.utils.location import compute_route_info

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
# LOCATION FEATURE HELPERS
# ============================================================

def calculate_address_quality(address: str) -> float:
    """
    Basic address-quality estimate used only until the location
    history module is available.

    This is deliberately simple because the real location quality
    should eventually be derived from geocoding + historical
    delivery success.
    """

    address = (address or "").strip()

    if not address:
        return 0.0

    score = 0.0

    # More detailed addresses are generally easier to locate.
    if len(address) >= 20:
        score += 0.35
    elif len(address) >= 10:
        score += 0.20

    # Useful location indicators.
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
    ]

    if any(
        term in address_lower
        for term in location_terms
    ):
        score += 0.35

    # House/ward/building number.
    if any(
        character.isdigit()
        for character in address
    ):
        score += 0.30

    return round(
        min(score, 1.0),
        4,
    )


# ============================================================
# LOCATION HISTORY
# ============================================================

def get_location_success_rate(
    db: Session,
    address: str,
) -> float:
    """
    Temporary location success-rate calculation.

    At this stage we do not yet have a dedicated location-history
    table containing successful/failed delivery outcomes.

    Therefore:
        - new/unknown location -> neutral 0.50
        - exact historical logic can be added later

    IMPORTANT:
    Do not treat this fallback as a real-world measured statistic.
    """

    # Reserved for future historical location analytics.
    _ = db
    _ = address

    return 0.50


# ============================================================
# PREDICT
# ============================================================

@router.post("/predict")
def predict_delivery(
    data: PredictionInput,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Predict delivery failure probability for an order-like request.

    Admin only.
    """

    # ========================================================
    # AUTHORIZATION
    # ========================================================

    if current_user["role"] != "admin":
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
            Customer.phone == data.phone_number
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
    # ROUTE
    # ========================================================

    try:
        route_info = compute_route_info(
            data.pickup_address,
            data.delivery_address,
        )

    except LocationValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except ORSServiceError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    # ========================================================
    # WEATHER
    # ========================================================

    try:
        weather_info = fetch_route_weather(
            route_info
        )

    except WeatherServiceError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    # ========================================================
    # WEATHER DATA FOR MODEL
    # ========================================================

    # fetch_route_weather() returns weather at:
    #   pickup
    #   midpoint
    #   delivery
    #
    # The model needs one route-level representation.
    #
    # We use midpoint weather as the representative route
    # condition and maximum rainfall across the sampled route.

    midpoint_weather = weather_info[
        "midpoint_weather"
    ]

    pickup_weather = weather_info[
        "pickup_weather"
    ]

    delivery_weather = weather_info[
        "delivery_weather"
    ]

    pickup_data = weather_info.get(
        "pickup"
    ) or {}

    midpoint_data = weather_info.get(
        "midpoint"
    ) or {}

    delivery_data = weather_info.get(
        "delivery"
    ) or {}

    rainfall_values = [
        pickup_data.get(
            "rainfall",
            0.0,
        ),
        midpoint_data.get(
            "rainfall",
            0.0,
        ),
        delivery_data.get(
            "rainfall",
            0.0,
        ),
    ]

    temperature_values = [
        pickup_data.get(
            "temperature",
            0.0,
        ),
        midpoint_data.get(
            "temperature",
            0.0,
        ),
        delivery_data.get(
            "temperature",
            0.0,
        ),
    ]

    rainfall = max(
        rainfall_values
    )

    temperature = (
        sum(temperature_values)
        / len(temperature_values)
    )

    # ========================================================
    # CURRENT OPERATIONAL STATE
    # ========================================================

    # We currently don't have a dedicated live traffic or
    # dispatch-operations service integrated into this endpoint.
    #
    # Therefore these values are explicit defaults rather than
    # pretending we have real operational measurements.

    operational_data = {
        "hub_delay_minutes": 0.0,
        "route_status": "NORMAL",
        "vehicle_status": "AVAILABLE",
    }

    # ========================================================
    # LOCATION FEATURES
    # ========================================================

    address_quality = calculate_address_quality(
        data.delivery_address
    )

    location_success_rate = (
        get_location_success_rate(
            db=db,
            address=data.delivery_address,
        )
    )

    location_data = {
        "address_quality": address_quality,
        "distance_km": route_info[
            "estimated_distance_km"
        ],
        "estimated_duration": route_info.get(
            "estimated_duration_min",
            0.0,
        ),
        "location_success_rate": location_success_rate,
    }

    # ========================================================
    # ENVIRONMENT FEATURES
    # ========================================================

    # Use midpoint weather as route representative.
    #
    # If pickup/delivery also has rain, midpoint remains the
    # central route condition. Rainfall/temperature use the
    # route-level aggregates calculated above.

    environment_data = {
        "weather": midpoint_weather,
        "rainfall": rainfall,
        "temperature": temperature,

        # Traffic integration is a future module.
        "traffic_level": "LOW",
    }

    # ========================================================
    # ORDER FEATURES
    # ========================================================

    # PredictionInput currently contains:
    #
    #   order_value
    #   payment_method
    #
    # It does not yet contain:
    #   quantity
    #   prepaid_amount
    #
    # So we use sensible testing defaults here.
    #
    # These should move to OrderCreate / PredictionInput once
    # the request schema is expanded.

    quantity = 1

    payment_method = (
        data.payment_method
    )

    is_cod = (
        payment_method.strip().lower()
        in {
            "cod",
            "cash",
            "cash on delivery",
        }
    )

    prepaid_amount = 0.0

    # ========================================================
    # BUILD FEATURES
    # ========================================================

    features = build_features(
        customer=customer,

        quantity=quantity,

        total_price=data.order_value,

        is_cod=is_cod,

        payment_method=payment_method,

        prepaid_amount=prepaid_amount,

        order_time=datetime.now(),

        location_data=location_data,

        environment_data=environment_data,

        operational_data=operational_data,
    )

    logger.info(
        "Generated model features: %s",
        features,
    )
    result = predict(
        features
    )

    if not result.get("success"):
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

    # return {
    #     "prediction": result[
    #         "prediction"
    #     ],

    #     "probability": result[
    #         "probability"
    #     ],

    #     "risk": result[
    #         "risk"
    #     ],

    #     "phone_number": (
    #         data.phone_number
    #     ),

    #     "customer": {
    #         "id": customer.id,
    #         "total_orders": (
    #             customer.total_orders
    #             or 0
    #         ),
    #         "failed_deliveries": (
    #             customer.failed_deliveries
    #             or 0
    #         ),
    #         "unreachable_count": (
    #             customer.unreachable_count
    #             or 0
    #         ),
    #     },

    #     "route": {
    #         "distance_km": route_info[
    #             "estimated_distance_km"
    #         ],
    #         "estimated_duration_min": (
    #             route_info.get(
    #                 "estimated_duration_min"
    #             )
    #         ),
    #         "pickup_district": route_info[
    #             "pickup_district"
    #         ],
    #         "delivery_district": route_info[
    #             "delivery_district"
    #         ],
    #         "pickup_coordinates": route_info[
    #             "pickup_coordinates"
    #         ],
    #         "delivery_coordinates": route_info[
    #             "delivery_coordinates"
    #         ],
    #         "route_source": route_info.get(
    #             "route_source"
    #         ),
    #     },

    #     "weather": {
    #         "pickup": pickup_weather,
    #         "midpoint": midpoint_weather,
    #         "delivery": delivery_weather,
    #         "rainfall": round(
    #             rainfall,
    #             2,
    #         ),
    #         "temperature": round(
    #             temperature,
    #             2,
    #         ),
    #         "weather_risk": weather_info[
    #             "weather_risk"
    #         ],
    #         "weather_risk_message": (
    #             weather_info[
    #                 "weather_risk_message"
    #             ]
    #         ),
    #     },

    #     "features": features,
    # }
    return {
    "prediction": result["prediction"],
    "probability": result["probability"],
    "risk": result["risk"],
    "phone_number": data.phone_number,

    "customer": {
        "id": customer.id,
        "total_orders": customer.total_orders or 0,
        "failed_deliveries": customer.failed_deliveries or 0,
        "unreachable_count": customer.unreachable_count or 0,
    },

    "route": {
        "distance_km": route_info["estimated_distance_km"],
        "estimated_duration_min": route_info.get(
            "estimated_duration_min"
        ),
        "pickup_district": route_info["pickup_district"],
        "delivery_district": route_info["delivery_district"],
        "pickup_coordinates": route_info["pickup_coordinates"],
        "delivery_coordinates": route_info["delivery_coordinates"],
        "route_source": route_info.get("route_source"),
    },

    "weather": {
        "pickup": pickup_weather,
        "midpoint": midpoint_weather,
        "delivery": delivery_weather,
        "rainfall": round(rainfall, 2),
        "temperature": round(temperature, 2),
        "route_weather": weather_info.get(
            "route_weather",
            "LOW",
        ),
        "weather_severity": weather_info.get(
            "maximum_weather_severity",
            0.0,
        ),
        "adverse_weather_points": weather_info.get(
            "adverse_weather_points",
            0,
        ),
    },

    "features": features,
}