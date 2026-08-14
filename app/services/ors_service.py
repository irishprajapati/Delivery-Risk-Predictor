"""
Location and baseline-routing integration for the delivery system.

Responsibilities:

1. Forward geocoding using HeiGIT/Pelias.
2. Reverse geocoding for map-pin coordinates.
3. Validate coordinates are inside Nepal.
4. Validate the supported Kathmandu Valley service area.
5. Validate address ↔ selected map-pin consistency.
6. Calculate a baseline driving route using HeiGIT/OpenRouteService.
7. Return route geometry for map rendering.

Traffic is intentionally NOT handled here.

Traffic belongs to:
    app/services/traffic_service.py

Location strategy:

    MAP-PIN MODE
        user selects map pin
              ↓
        latitude / longitude
              ↓
        reverse geocoding
              ↓
        service-area validation
              ↓
        optional address consistency validation
              ↓
        baseline route

    ADDRESS MODE
        user enters address
              ↓
        forward geocoding
              ↓
        candidate validation
              ↓
        baseline route

Important:

- No addresses are hardcoded.
- No coordinates are hardcoded.
- Coordinates are authoritative when supplied.
- ORS/HeiGIT baseline routing does NOT provide live traffic.
- Traffic estimation is handled separately by traffic_service.py.

Environment variables:

    ORS_API_KEY=...

Current HeiGIT endpoints:

    https://api.heigit.org/pelias/v1/search
    https://api.heigit.org/pelias/v1/reverse
    https://api.heigit.org/openrouteservice/v2/...
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

PROJECT_ROOT = (
    Path(__file__).resolve()
    .parent.parent.parent
)

load_dotenv(
    PROJECT_ROOT / ".env"
)

logger = logging.getLogger(__name__)

ORS_API_KEY = os.getenv(
    "ORS_API_KEY"
)


# ============================================================
# API ENDPOINTS
# ============================================================

GEOCODE_URL = (
    "https://api.heigit.org/"
    "pelias/v1/search"
)

REVERSE_GEOCODE_URL = (
    "https://api.heigit.org/"
    "pelias/v1/reverse"
)

DIRECTIONS_URL = (
    "https://api.heigit.org/"
    "openrouteservice/v2/"
    "directions/driving-car/geojson"
)


# ============================================================
# SERVICE AREA
# ============================================================

ALLOWED_DISTRICTS = frozenset(
    {
        "kathmandu",
        "lalitpur",
        "bhaktapur",
    }
)

VALLEY_ONLY_MESSAGE = (
    "Service limited to Kathmandu Valley "
    "(Kathmandu, Lalitpur, Bhaktapur districts)"
)


# ============================================================
# EXCEPTIONS
# ============================================================

class LocationValidationError(Exception):
    """
    Raised when a user location cannot be safely validated.
    """


class ORSServiceError(Exception):
    """
    Raised when geocoding or routing services fail.
    """


# ============================================================
# CONFIGURATION
# ============================================================

def _require_ors_api_key() -> str:
    if not ORS_API_KEY:
        raise ORSServiceError(
            "ORS_API_KEY is not configured in .env"
        )

    return ORS_API_KEY


# ============================================================
# TEXT HELPERS
# ============================================================

def _normalize_text(
    value: Any,
) -> str | None:
    if value is None:
        return None

    value = str(value).strip()

    return value.lower() if value else None


def _normalize_query_for_matching(
    address: str,
) -> str:
    """
    Normalize user-entered address text for matching only.

    This normalized value is never sent to the geocoder.
    """

    value = str(address).lower()

    value = re.sub(
        r"[^a-z0-9\s]",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def _query_terms(
    address: str,
) -> list[str]:
    """
    Extract meaningful terms from an address.

    Administrative words are ignored.

    Example:

        "Sunakothi, Lalitpur"

    becomes approximately:

        ["sunakothi"]
    """

    ignored_terms = {
        "nepal",
        "kathmandu",
        "lalitpur",
        "bhaktapur",
        "district",
        "city",
        "municipality",
        "ward",
        "road",
        "street",
        "near",
        "to",
        "the",
        "area",
        "main",
        "marg",
        "road",
        "street",
    }

    normalized = _normalize_query_for_matching(
        address
    )

    terms: list[str] = []

    for word in normalized.split():
        if (
            len(word) >= 4
            and word not in ignored_terms
        ):
            terms.append(word)

    return terms


def _extract_explicit_district(
    address: str,
) -> str | None:
    """
    Detect an explicitly written district in the user's
    address.

    This is intentionally strict.

    Examples:

        "Jawalakhel, Kathmandu"
            -> kathmandu

        "Jawalakhel, Lalitpur"
            -> lalitpur

        "Suryabinayak, Bhaktapur"
            -> bhaktapur

        "Jawalakhel"
            -> None
    """

    normalized = _normalize_query_for_matching(
        address
    )

    district_aliases = {
        "kathmandu": "kathmandu",
        "lalitpur": "lalitpur",
        "bhaktapur": "bhaktapur",
    }

    for text, district in district_aliases.items():
        if re.search(
            rf"\b{re.escape(text)}\b",
            normalized,
        ):
            return district

    return None


# ============================================================
# GEOGRAPHIC VALIDATION
# ============================================================

def _is_in_nepal_bounds(
    longitude: float,
    latitude: float,
) -> bool:
    """
    Broad geographic sanity check.

    This only confirms that coordinates are plausibly inside
    Nepal. It does not determine district.
    """

    return (
        80.0 < longitude < 88.5
        and 26.0 < latitude < 30.5
    )


def _validate_coordinates(
    latitude: float,
    longitude: float,
) -> None:
    """
    Validate a coordinate pair before using it.
    """

    try:
        latitude = float(latitude)
        longitude = float(longitude)

    except (
        TypeError,
        ValueError,
    ) as exc:

        raise LocationValidationError(
            "Invalid latitude or longitude."
        ) from exc

    if not (
        -90.0
        <= latitude
        <= 90.0
    ):
        raise LocationValidationError(
            "Latitude must be between "
            "-90 and 90."
        )

    if not (
        -180.0
        <= longitude
        <= 180.0
    ):
        raise LocationValidationError(
            "Longitude must be between "
            "-180 and 180."
        )

    if not _is_in_nepal_bounds(
        longitude,
        latitude,
    ):
        raise LocationValidationError(
            "The selected location is "
            "outside Nepal."
        )


def _is_allowed_district(
    district: str | None,
) -> bool:
    return (
        district is not None
        and district in ALLOWED_DISTRICTS
    )


# ============================================================
# DISTRICT EXTRACTION
# ============================================================

def _extract_district(
    properties: dict,
) -> str | None:
    """
    Extract district from Pelias properties.
    """

    for field in (
        "county",
        "localadmin",
        "locality",
        "region",
    ):
        value = _normalize_text(
            properties.get(field)
        )

        if value in ALLOWED_DISTRICTS:
            return value

    return _normalize_text(
        properties.get("county")
    )


# ============================================================
# GEOCODING CANDIDATE PARSING
# ============================================================

def _parse_geocode_candidate(
    feature: dict,
    requested_address: str,
) -> dict | None:
    """
    Convert one Pelias feature into our internal
    candidate representation.
    """

    properties = (
        feature.get("properties")
        or {}
    )

    geometry = (
        feature.get("geometry")
        or {}
    )

    coordinates = geometry.get(
        "coordinates"
    )

    if (
        not coordinates
        or len(coordinates) < 2
    ):
        return None

    try:
        longitude = float(
            coordinates[0]
        )

        latitude = float(
            coordinates[1]
        )

    except (
        TypeError,
        ValueError,
    ):
        return None

    if not _is_in_nepal_bounds(
        longitude,
        latitude,
    ):
        return None

    district = _extract_district(
        properties
    )

    confidence = float(
        properties.get(
            "confidence",
            0.0,
        )
        or 0.0
    )

    label = (
        properties.get("label")
        or properties.get("name")
        or requested_address
    )

    matched_area = (
        properties.get("name")
        or properties.get("locality")
        or properties.get("neighbourhood")
        or properties.get("street")
        or requested_address
    )

    layer = _normalize_text(
        properties.get("layer")
    )

    searchable_text = " ".join(
        [
            str(label),
            str(matched_area),
            str(
                properties.get(
                    "locality"
                )
                or ""
            ),
            str(
                properties.get(
                    "neighbourhood"
                )
                or ""
            ),
            str(
                properties.get(
                    "street"
                )
                or ""
            ),
        ]
    ).lower()

    return {
        "lat": latitude,
        "lng": longitude,
        "district": district,
        "label": label,
        "matched_area": matched_area,
        "confidence": confidence,
        "layer": layer,
        "searchable_text": searchable_text,
        "raw_properties": properties,
    }


# ============================================================
# QUERY MATCHING
# ============================================================

def _candidate_matches_query(
    candidate: dict,
    address: str,
) -> tuple[bool, int]:
    """
    Check whether a geocoder candidate actually contains
    meaningful terms from the requested address.
    """

    terms = _query_terms(
        address
    )

    if not terms:
        return True, 0

    searchable = candidate[
        "searchable_text"
    ]

    matched_terms = sum(
        1
        for term in terms
        if term in searchable
    )

    return (
        matched_terms > 0,
        matched_terms,
    )


# ============================================================
# MAP-PIN / ADDRESS CONSISTENCY
# ============================================================

def _validate_address_against_pin(
    address: str | None,
    resolved_location: dict,
    location_name: str,
) -> None:
    """
    Validate an explicitly supplied address against a selected
    map-pin location.

    IMPORTANT:

    Coordinates remain authoritative.

    We do NOT require the reverse-geocoder's label to match every
    word typed by the user because geocoding providers often use
    different locality naming conventions.

    We DO reject an explicit district contradiction.

    Example:

        address:
            "Jawalakhel, Kathmandu"

        pin reverse-geocodes to:
            district = "lalitpur"

        Result:
            reject

    But:

        address:
            "Jawalakhel"

        pin:
            Lalitpur

        Result:
            accept
    """

    if not address:
        return

    explicit_district = (
        _extract_explicit_district(
            address
        )
    )

    if (
        explicit_district
        and explicit_district
        != resolved_location.get(
            "district"
        )
    ):
        actual_district = (
            resolved_location.get(
                "district"
            )
            or "unknown"
        )

        raise LocationValidationError(
            f"The selected {location_name} "
            f"map location is in "
            f"{actual_district.title()} district, "
            f"but the address says "
            f"{explicit_district.title()} district. "
            "Please correct the address or move "
            "the map pin."
        )


# ============================================================
# FORWARD GEOCODING
# ============================================================

def geocode_address(
    address: str,
) -> dict:
    """
    Convert a free-text address into validated coordinates.

    Used only when map coordinates were not supplied.
    """

    api_key = _require_ors_api_key()

    address = (
        address or ""
    ).strip()

    if not address:
        raise LocationValidationError(
            "Address cannot be empty."
        )

    params = {
        "api_key": api_key,
        "text": address,
        "size": 10,
        "boundary.country": "NP",
    }

    try:
        response = requests.get(
            GEOCODE_URL,
            params=params,
            timeout=15,
        )

        response.raise_for_status()

        data = response.json()

    except requests.RequestException as exc:

        logger.error(
            "Geocoding request failed "
            "for %r: %s",
            address,
            exc,
        )

        raise ORSServiceError(
            f"Geocoding service unavailable: "
            f"{exc}"
        ) from exc

    features = (
        data.get("features")
        or []
    )

    if not features:
        raise LocationValidationError(
            f"Could not find location: "
            f"{address}"
        )

    all_candidates: list[dict] = []

    for feature in features:

        candidate = (
            _parse_geocode_candidate(
                feature,
                address,
            )
        )

        if candidate is None:
            continue

        if not _is_allowed_district(
            candidate["district"]
        ):
            continue

        (
            matches_query,
            matched_count,
        ) = _candidate_matches_query(
            candidate,
            address,
        )

        candidate[
            "matches_query"
        ] = matches_query

        candidate[
            "matched_term_count"
        ] = matched_count

        all_candidates.append(
            candidate
        )

    if not all_candidates:
        raise LocationValidationError(
            f"Could not verify "
            f"'{address}' inside the "
            f"supported Kathmandu Valley "
            f"service area. "
            f"{VALLEY_ONLY_MESSAGE}"
        )

    # --------------------------------------------------------
    # Debug logging
    # --------------------------------------------------------

    for candidate in all_candidates:
        logger.info(
            "GEOCODE CANDIDATE | "
            "label=%s | district=%s | "
            "layer=%s | confidence=%s | "
            "matched_query=%s | "
            "matched_terms=%s | "
            "lat=%s | lng=%s",
            candidate["label"],
            candidate["district"],
            candidate["layer"],
            candidate["confidence"],
            candidate["matches_query"],
            candidate["matched_term_count"],
            candidate["lat"],
            candidate["lng"],
        )

    # --------------------------------------------------------
    # Specific match filtering
    # --------------------------------------------------------

    specific_candidates = [
        candidate
        for candidate in all_candidates
        if candidate["matches_query"]
    ]

    query_terms = _query_terms(
        address
    )

    if (
        query_terms
        and not specific_candidates
    ):
        raise LocationValidationError(
            f"Could not precisely locate "
            f"'{address}'. "
            "The geocoding service returned "
            "only generic area matches. "
            "Please provide a more precise "
            "address or select a location "
            "on the map."
        )

    candidates = (
        specific_candidates
        if specific_candidates
        else all_candidates
    )

    # --------------------------------------------------------
    # Candidate ranking
    # --------------------------------------------------------

    layer_priority = {
        "address": 6,
        "venue": 6,
        "neighbourhood": 5,
        "street": 4,
        "locality": 3,
        "localadmin": 2,
        "county": 1,
        "region": 1,
    }

    def candidate_score(
        candidate: dict,
    ) -> tuple:

        layer = (
            candidate[
                "layer"
            ]
            or ""
        )

        return (
            1
            if candidate[
                "matches_query"
            ]
            else 0,

            candidate[
                "matched_term_count"
            ],

            layer_priority.get(
                layer,
                0,
            ),

            candidate[
                "confidence"
            ],
        )

    candidates.sort(
        key=candidate_score,
        reverse=True,
    )

    best = candidates[0]

    # --------------------------------------------------------
    # Confidence validation
    # --------------------------------------------------------

    if (
        best["confidence"] > 0
        and best["confidence"] < 0.35
    ):
        raise LocationValidationError(
            f"Location '{address}' "
            "could not be verified with "
            "sufficient geocoding confidence. "
            "Please provide a more precise "
            "address or select a location "
            "on the map."
        )

    # --------------------------------------------------------
    # Ambiguity validation
    # --------------------------------------------------------

    if len(candidates) >= 2:

        first = candidates[0]
        second = candidates[1]

        first_score = candidate_score(
            first
        )

        second_score = candidate_score(
            second
        )

        if (
            first_score[:-1]
            == second_score[:-1]
            and abs(
                first["confidence"]
                - second["confidence"]
            ) < 0.05
            and first["label"]
            != second["label"]
        ):
            raise LocationValidationError(
                f"Location '{address}' "
                "is ambiguous. Please provide "
                "a more precise address or "
                "select a location on the map."
            )

    logger.info(
        "GEOCODE ACCEPTED | "
        "requested=%r | label=%s | "
        "district=%s | layer=%s | "
        "confidence=%.3f | "
        "lat=%.6f | lng=%.6f",
        address,
        best["label"],
        best["district"],
        best["layer"],
        best["confidence"],
        best["lat"],
        best["lng"],
    )

    return best


# ============================================================
# REVERSE GEOCODING
# ============================================================

def reverse_geocode(
    latitude: float,
    longitude: float,
) -> dict:
    """
    Convert selected map-pin coordinates into a validated
    location.

    This is the preferred location path.
    """

    _validate_coordinates(
        latitude,
        longitude,
    )

    api_key = _require_ors_api_key()

    params = {
        "api_key": api_key,
        "point.lat": latitude,
        "point.lon": longitude,
        "size": 1,
    }

    try:
        response = requests.get(
            REVERSE_GEOCODE_URL,
            params=params,
            timeout=15,
        )

        response.raise_for_status()

        data = response.json()

    except requests.RequestException as exc:

        logger.error(
            "Reverse geocoding failed "
            "for (%s, %s): %s",
            latitude,
            longitude,
            exc,
        )

        raise ORSServiceError(
            "Reverse geocoding service "
            "unavailable."
        ) from exc

    features = (
        data.get("features")
        or []
    )

    if not features:
        raise LocationValidationError(
            "The selected map location "
            "could not be identified."
        )

    feature = features[0]

    properties = (
        feature.get("properties")
        or {}
    )

    district = _extract_district(
        properties
    )

    if not _is_allowed_district(
        district
    ):
        district_name = (
            district
            or "unknown"
        )

        raise LocationValidationError(
            f"Selected location is in "
            f"{district_name.title()} district. "
            f"{VALLEY_ONLY_MESSAGE}"
        )

    label = (
        properties.get("label")
        or properties.get("name")
        or f"{latitude}, {longitude}"
    )

    matched_area = (
        properties.get("name")
        or properties.get("locality")
        or properties.get("neighbourhood")
        or properties.get("street")
        or label
    )

    logger.info(
        "REVERSE GEOCODE ACCEPTED | "
        "lat=%.6f | lng=%.6f | "
        "label=%s | district=%s",
        latitude,
        longitude,
        label,
        district,
    )

    return {
        "lat": float(latitude),
        "lng": float(longitude),
        "district": district,
        "label": label,
        "matched_area": matched_area,
        "raw_properties": properties,
    }


# ============================================================
# BASELINE DRIVING ROUTE
# ============================================================

def get_driving_route(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
) -> dict:
    """
    Fetch a real road-network route.

    Returns:

        distance_km
        duration_min
        polyline

    This is the baseline route only.
    """

    _validate_coordinates(
        origin_lat,
        origin_lng,
    )

    _validate_coordinates(
        dest_lat,
        dest_lng,
    )

    api_key = _require_ors_api_key()

    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }

    body = {
        "coordinates": [
            [
                float(origin_lng),
                float(origin_lat),
            ],
            [
                float(dest_lng),
                float(dest_lat),
            ],
        ],
    }

    try:
        response = requests.post(
            DIRECTIONS_URL,
            json=body,
            headers=headers,
            timeout=20,
        )

        response.raise_for_status()

        data = response.json()

    except requests.RequestException as exc:

        logger.error(
            "ORS directions request failed: "
            "%s",
            exc,
        )

        raise ORSServiceError(
            f"Routing service unavailable: "
            f"{exc}"
        ) from exc

    try:
        feature = (
            data["features"][0]
        )

        summary = (
            feature[
                "properties"
            ][
                "summary"
            ]
        )

        coordinates = (
            feature[
                "geometry"
            ][
                "coordinates"
            ]
        )

    except (
        KeyError,
        IndexError,
        TypeError,
    ) as exc:

        raise ORSServiceError(
            "Failed to parse driving route "
            "from OpenRouteService."
        ) from exc

    polyline: list[dict] = []

    for coordinate in coordinates:

        if (
            not coordinate
            or len(coordinate) < 2
        ):
            continue

        polyline.append(
            {
                "lat": float(
                    coordinate[1]
                ),
                "lng": float(
                    coordinate[0]
                ),
            }
        )

    distance_km = round(
        float(
            summary["distance"]
        ) / 1000,
        2,
    )

    duration_min = round(
        float(
            summary["duration"]
        ) / 60,
        1,
    )

    if distance_km <= 0:
        raise ORSServiceError(
            "Routing service returned "
            "an invalid route distance."
        )

    if duration_min <= 0:
        raise ORSServiceError(
            "Routing service returned "
            "an invalid route duration."
        )

    return {
        "distance_km": distance_km,
        "duration_min": duration_min,
        "polyline": polyline,
        "route_source": (
            "heigit_openrouteservice"
        ),
    }


# ============================================================
# COMPLETE ROUTE INFORMATION
# ============================================================

def build_route_info(
    pickup_address: str | None = None,
    delivery_address: str | None = None,
    pickup_latitude: float | None = None,
    pickup_longitude: float | None = None,
    delivery_latitude: float | None = None,
    delivery_longitude: float | None = None,
) -> dict:
    """
    Build complete location + baseline-route context.

    Map-pin mode is preferred.

    Coordinates are authoritative for routing, but if the user
    also supplied an address, explicit district contradictions
    are rejected.
    """

    # ========================================================
    # PICKUP
    # ========================================================

    pickup_has_lat = (
        pickup_latitude is not None
    )

    pickup_has_lng = (
        pickup_longitude is not None
    )

    if (
        pickup_has_lat
        != pickup_has_lng
    ):
        raise LocationValidationError(
            "Pickup latitude and longitude "
            "must both be provided or both "
            "be omitted."
        )

    if pickup_has_lat:

        pickup = reverse_geocode(
            latitude=float(
                pickup_latitude
            ),
            longitude=float(
                pickup_longitude
            ),
        )

        _validate_address_against_pin(
            address=pickup_address,
            resolved_location=pickup,
            location_name="pickup",
        )

        pickup_source = "map_pin"

    else:

        if not pickup_address:
            raise LocationValidationError(
                "Pickup address or pickup "
                "coordinates are required."
            )

        pickup = geocode_address(
            pickup_address
        )

        pickup_source = "geocoded_address"

    # ========================================================
    # DELIVERY
    # ========================================================

    delivery_has_lat = (
        delivery_latitude is not None
    )

    delivery_has_lng = (
        delivery_longitude is not None
    )

    if (
        delivery_has_lat
        != delivery_has_lng
    ):
        raise LocationValidationError(
            "Delivery latitude and longitude "
            "must both be provided or both "
            "be omitted."
        )

    if delivery_has_lat:

        delivery = reverse_geocode(
            latitude=float(
                delivery_latitude
            ),
            longitude=float(
                delivery_longitude
            ),
        )

        _validate_address_against_pin(
            address=delivery_address,
            resolved_location=delivery,
            location_name="delivery",
        )

        delivery_source = "map_pin"

    else:

        if not delivery_address:
            raise LocationValidationError(
                "Delivery address or delivery "
                "coordinates are required."
            )

        delivery = geocode_address(
            delivery_address
        )

        delivery_source = "geocoded_address"

    # ========================================================
    # PREVENT IDENTICAL LOCATIONS
    # ========================================================

    if (
        pickup["lat"]
        == delivery["lat"]
        and pickup["lng"]
        == delivery["lng"]
    ):
        raise LocationValidationError(
            "Pickup and delivery locations "
            "must be different."
        )

    # ========================================================
    # BASELINE ROUTE
    # ========================================================

    driving = get_driving_route(
        origin_lat=pickup["lat"],
        origin_lng=pickup["lng"],
        dest_lat=delivery["lat"],
        dest_lng=delivery["lng"],
    )

    # ========================================================
    # UNIFIED RESPONSE
    # ========================================================

    return {
        # Pickup
        "pickup_district": pickup[
            "district"
        ],

        "pickup_area": pickup[
            "matched_area"
        ],

        "pickup_label": pickup[
            "label"
        ],

        "pickup_geocode_confidence": pickup.get(
            "confidence"
        ),

        "pickup_coordinates": {
            "lat": pickup["lat"],
            "lng": pickup["lng"],
        },

        "pickup_location_source": (
            pickup_source
        ),

        # Delivery
        "delivery_district": delivery[
            "district"
        ],

        "delivery_area": delivery[
            "matched_area"
        ],

        "delivery_label": delivery[
            "label"
        ],

        "delivery_geocode_confidence": delivery.get(
            "confidence"
        ),

        "delivery_coordinates": {
            "lat": delivery["lat"],
            "lng": delivery["lng"],
        },

        "delivery_location_source": (
            delivery_source
        ),

        # Route
        "estimated_distance_km": driving[
            "distance_km"
        ],

        "baseline_duration_min": driving[
            "duration_min"
        ],

        # Keep this equal to baseline duration.
        # Traffic service will provide the traffic-adjusted
        # ETA separately.
        "estimated_duration_min": driving[
            "duration_min"
        ],

        "route_polyline": driving[
            "polyline"
        ],

        "route_source": driving[
            "route_source"
        ],
    }