"""
Location utilities for Kathmandu Valley deliveries.
Geocoding and district validation are delegated to OpenRouteService.
"""

import math

from app.services.ors_service import (
    VALLEY_ONLY_MESSAGE,
    LocationValidationError,
    build_route_info,
    geocode_address,
)

DISTANCE_RISK_THRESHOLD_KM = 15.0

__all__ = [
    "VALLEY_ONLY_MESSAGE",
    "DISTANCE_RISK_THRESHOLD_KM",
    "LocationValidationError",
    "geocode_address",
    "compute_route_info",
    "apply_distance_risk",
    "haversine_km",
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def compute_route_info(pickup_address: str, delivery_address: str) -> dict:
    """Build full route info using OpenRouteService geocoding and driving directions."""
    return build_route_info(pickup_address, delivery_address)


def apply_distance_risk(probability: float, risk: str, distance_km: float) -> tuple[float, str]:
    if distance_km <= DISTANCE_RISK_THRESHOLD_KM:
        return probability, risk

    boosted_probability = min(probability + 0.15, 0.99)

    if boosted_probability >= 0.7:
        new_risk = "HIGH"
    elif boosted_probability > 0.4:
        new_risk = "MEDIUM"
    else:
        new_risk = "LOW"

    return boosted_probability, new_risk
