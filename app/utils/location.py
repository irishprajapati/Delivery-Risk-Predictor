"""
District-based location handling for Kathmandu Valley deliveries.
Maps sub-areas to districts and assigns coordinates per matched area.
"""

import math

AREA_MAP = {
    "kathmandu": ["kathmandu", "baneshwor", "koteshwor", "kalanki", "thamel"],
    "lalitpur": ["lalitpur", "patan", "jawalakhel"],
    "bhaktapur": ["bhaktapur", "thimi", "suryabinayak"],
}

DISTRICT_COORDINATES = {
    "kathmandu": (27.7172, 85.3240),
    "lalitpur": (27.6588, 85.3247),
    "bhaktapur": (27.6710, 85.4298),
}

COORDINATES = {
    "kathmandu": DISTRICT_COORDINATES["kathmandu"],
    "baneshwor": (27.6900, 85.3350),
    "koteshwor": (27.6780, 85.3490),
    "kalanki": (27.6930, 85.2810),
    "thamel": (27.7150, 85.3120),
    "lalitpur": DISTRICT_COORDINATES["lalitpur"],
    "patan": (27.6588, 85.3247),
    "jawalakhel": (27.6730, 85.3140),
    "bhaktapur": DISTRICT_COORDINATES["bhaktapur"],
    "thimi": (27.6833, 85.4000),
    "suryabinayak": (27.6560, 85.4270),
}

DISTANCE_RISK_THRESHOLD_KM = 15.0
VALLEY_ONLY_MESSAGE = "Service limited to Kathmandu Valley only"


def _all_area_keywords() -> list[tuple[str, str]]:
    """Return (keyword, district) pairs sorted longest-first for precise matching."""
    pairs: list[tuple[str, str]] = []
    for district, keywords in AREA_MAP.items():
        for keyword in keywords:
            pairs.append((keyword, district))
    pairs.sort(key=lambda item: len(item[0]), reverse=True)
    return pairs


def is_valid_valley_address(address: str) -> bool:
    address_lower = address.strip().lower()
    for keywords in AREA_MAP.values():
        for keyword in keywords:
            if keyword in address_lower:
                return True
    return False


def detect_district(address: str) -> str:
    address_lower = address.strip().lower()
    for keyword, district in _all_area_keywords():
        if keyword in address_lower:
            return district
    return "kathmandu"


def detect_matched_area(address: str) -> str | None:
    """Return the matched sub-area keyword, or None if no match."""
    address_lower = address.strip().lower()
    for keyword, _district in _all_area_keywords():
        if keyword in address_lower:
            return keyword
    return None


def get_address_coordinates(address: str) -> tuple[float, float, str, str]:
    """
    Return (lat, lng, district, matched_area).
    Uses sub-area coordinates when matched; falls back to district center.
    """
    district = detect_district(address)
    matched_area = detect_matched_area(address)

    if matched_area and matched_area in COORDINATES:
        lat, lng = COORDINATES[matched_area]
    else:
        lat, lng = DISTRICT_COORDINATES[district]
        matched_area = district

    return lat, lng, district, matched_area


def get_district_coordinates(district: str) -> tuple[float, float]:
    return DISTRICT_COORDINATES[district]


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
    pickup_lat, pickup_lon, pickup_district, pickup_area = get_address_coordinates(
        pickup_address
    )
    delivery_lat, delivery_lon, delivery_district, delivery_area = get_address_coordinates(
        delivery_address
    )

    distance_km = haversine_km(pickup_lat, pickup_lon, delivery_lat, delivery_lon)

    return {
        "pickup_district": pickup_district,
        "delivery_district": delivery_district,
        "pickup_area": pickup_area,
        "delivery_area": delivery_area,
        "pickup_coordinates": {"lat": pickup_lat, "lng": pickup_lon},
        "delivery_coordinates": {"lat": delivery_lat, "lng": delivery_lon},
        "estimated_distance_km": round(distance_km, 2),
    }


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
