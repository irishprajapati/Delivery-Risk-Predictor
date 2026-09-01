from __future__ import annotations

import logging
import math
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
    """
    Return the configured ORS API key.
    """

    if not ORS_API_KEY:
        raise ORSServiceError(
            "ORS_API_KEY is not configured in .env"
        )

    key = str(
        ORS_API_KEY
    ).strip()

    if not key:
        raise ORSServiceError(
            "ORS_API_KEY is empty in .env"
        )

    return key


# ============================================================
# TEXT HELPERS
# ============================================================

def _normalize_text(
    value: Any,
) -> str | None:
    """
    Normalize text to lowercase.

    Returns None for empty values.
    """

    if value is None:
        return None

    value = str(
        value
    ).strip()

    return (
        value.lower()
        if value
        else None
    )


def _normalize_query_for_matching(
    address: str,
) -> str:
    """
    Normalize user-entered address text for matching only.

    This normalized value is never sent to the geocoder.
    """

    value = str(
        address
    ).lower()

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

    Administrative and generic words are ignored.

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
        "lane",
        "block",
        "plot",
    }

    normalized = (
        _normalize_query_for_matching(
            address
        )
    )

    terms: list[str] = []

    for word in normalized.split():

        if (
            len(word) >= 4
            and word not in ignored_terms
        ):
            terms.append(
                word
            )

    return terms


def _extract_explicit_district(
    address: str,
) -> str | None:
    """
    Detect an explicitly written district in the user's
    address.

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

    normalized = (
        _normalize_query_for_matching(
            address
        )
    )

    district_aliases = {
        "kathmandu": "kathmandu",
        "lalitpur": "lalitpur",
        "bhaktapur": "bhaktapur",
    }

    for text, district in (
        district_aliases.items()
    ):

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

    This is intentionally broader than the Kathmandu Valley.
    District validation is performed separately.

    These bounds are only a first-level geographic guard.
    """

    try:
        longitude = float(
            longitude
        )

        latitude = float(
            latitude
        )

    except (
        TypeError,
        ValueError,
    ):
        return False

    if not (
        math.isfinite(
            latitude
        )
        and math.isfinite(
            longitude
        )
    ):
        return False

    return (
        80.0
        <= longitude
        <= 88.5
        and 26.0
        <= latitude
        <= 30.5
    )


def _validate_coordinates(
    latitude: float,
    longitude: float,
) -> None:
    """
    Validate a coordinate pair before using it.

    Checks:

    - finite numeric values
    - global latitude/longitude ranges
    - explicit (0, 0) rejection
    - broad Nepal geographic bounds
    """

    try:
        latitude = float(
            latitude
        )

        longitude = float(
            longitude
        )

    except (
        TypeError,
        ValueError,
    ) as exc:

        raise LocationValidationError(
            "Invalid latitude or longitude."
        ) from exc

    if not (
        math.isfinite(
            latitude
        )
        and math.isfinite(
            longitude
        )
    ):
        raise LocationValidationError(
            "Latitude and longitude "
            "must be finite numbers."
        )

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

    # (0, 0) is not a valid delivery location
    # and is commonly caused by frontend/default-value bugs.
    if (
        latitude == 0.0
        and longitude == 0.0
    ):
        raise LocationValidationError(
            "Latitude and longitude "
            "cannot both be zero."
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
    """
    Check whether the district is inside the supported
    Kathmandu Valley service area.
    """

    normalized = _normalize_text(
        district
    )

    if not normalized:
        return False

    normalized = (
        normalized
        .replace(
            " district",
            "",
        )
        .strip()
    )

    return (
        normalized
        in ALLOWED_DISTRICTS
    )


def _normalize_district(
    value: Any,
) -> str | None:
    """
    Normalize district names returned by Pelias.

    Handles values such as:

        "Lalitpur"
        "Lalitpur District"
        "Lalitpur, Nepal"
    """

    normalized = _normalize_text(
        value
    )

    if not normalized:
        return None

    normalized = (
        normalized
        .replace(
            ", nepal",
            "",
        )
        .replace(
            " district",
            "",
        )
        .strip()
    )

    if (
        normalized
        in ALLOWED_DISTRICTS
    ):
        return normalized

    return normalized


# ============================================================
# DISTRICT EXTRACTION
# ============================================================

def _extract_district(
    properties: dict,
) -> str | None:
    """
    Extract a supported district from Pelias properties.

    Pelias may expose administrative information through
    different fields depending on the result.
    """

    possible_fields = (
        "county",
        "localadmin",
        "locality",
        "region",
        "macrocounty",
        "borough",
        "neighbourhood",
    )

    values: list[str] = []

    for field in possible_fields:

        value = _normalize_district(
            properties.get(
                field
            )
        )

        if value:
            values.append(
                value
            )

    # First prefer an exact supported district.
    for value in values:

        if (
            value
            in ALLOWED_DISTRICTS
        ):
            return value

    # Some providers may return a longer administrative value.
    # Check whether a supported district occurs as a full
    # administrative token.
    for value in values:

        for district in (
            "kathmandu",
            "lalitpur",
            "bhaktapur",
        ):

            if re.search(
                rf"\b{re.escape(district)}\b",
                value,
            ):
                return district

    return None


# ============================================================
# GEOCODING CANDIDATE PARSING
# ============================================================

def _parse_geocode_candidate(
    feature: dict,
    requested_address: str,
) -> dict | None:
    """
    Convert one Pelias feature into our internal candidate
    representation.
    """

    properties = (
        feature.get(
            "properties"
        )
        or {}
    )

    geometry = (
        feature.get(
            "geometry"
        )
        or {}
    )

    coordinates = (
        geometry.get(
            "coordinates"
        )
    )

    if (
        not isinstance(
            coordinates,
            (list, tuple),
        )
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

    # Reject invalid/non-finite values.
    if not (
        math.isfinite(
            latitude
        )
        and math.isfinite(
            longitude
        )
    ):
        return None

    # Reject locations outside Nepal.
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
        properties.get(
            "label"
        )
        or properties.get(
            "name"
        )
        or requested_address
    )

    matched_area = (
        properties.get(
            "name"
        )
        or properties.get(
            "locality"
        )
        or properties.get(
            "neighbourhood"
        )
        or properties.get(
            "street"
        )
        or requested_address
    )

    layer = _normalize_text(
        properties.get(
            "layer"
        )
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
            str(
                properties.get(
                    "name"
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

    Returns:

        (matches_query, matched_term_count)
    """

    terms = _query_terms(
        address
    )

    if not terms:
        return (
            True,
            0,
        )

    searchable = (
        candidate[
            "searchable_text"
        ]
    )

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

    Coordinates remain authoritative.

    We reject an explicit district contradiction.

    Example:

        address:
            "Jawalakhel, Kathmandu"

        pin:
            Lalitpur

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

    if not explicit_district:
        return

    actual_district = _normalize_district(
        resolved_location.get(
            "district"
        )
    )

    if (
        actual_district
        and explicit_district
        != actual_district
    ):
        raise LocationValidationError(
            f"The selected "
            f"{location_name} map location "
            f"is in "
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

    api_key = (
        _require_ors_api_key()
    )

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

    except ValueError as exc:

        logger.error(
            "Geocoding returned invalid JSON "
            "for %r",
            address,
        )

        raise ORSServiceError(
            "Geocoding service returned "
            "an invalid response."
        ) from exc

    features = (
        data.get(
            "features"
        )
        or []
    )

    if not features:
        raise LocationValidationError(
            f"Could not find location: "
            f"{address}"
        )

    all_candidates: list[
        dict[str, Any]
    ] = []

    for feature in features:

        candidate = (
            _parse_geocode_candidate(
                feature,
                address,
            )
        )

        if candidate is None:
            continue

        # A geocoded result is only usable for this application
        # if we can identify it as one of our service districts.
        if not _is_allowed_district(
            candidate[
                "district"
            ]
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

    for candidate in (
        all_candidates
    ):

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
        if candidate[
            "matches_query"
        ]
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
        "address": 7,
        "venue": 7,
        "building": 7,
        "house": 7,
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
    # Final candidate validation
    # --------------------------------------------------------

    if not _is_allowed_district(
        best.get(
            "district"
        )
    ):
        raise LocationValidationError(
            f"Resolved location for "
            f"'{address}' is outside the "
            f"supported Kathmandu Valley "
            f"service area. "
            f"{VALLEY_ONLY_MESSAGE}"
        )

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

    # --------------------------------------------------------
    # Final coordinate validation
    # --------------------------------------------------------

    _validate_coordinates(
        latitude=best["lat"],
        longitude=best["lng"],
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

    # Performs:
    # - finite-value validation
    # - valid latitude/longitude validation
    # - (0, 0) rejection
    # - Nepal bounds validation
    _validate_coordinates(
        latitude,
        longitude,
    )

    api_key = (
        _require_ors_api_key()
    )

    params = {
        "api_key": api_key,
        "point.lat": float(
            latitude
        ),
        "point.lon": float(
            longitude
        ),
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

    except ValueError as exc:

        logger.error(
            "Reverse geocoding returned "
            "invalid JSON for (%s, %s)",
            latitude,
            longitude,
        )

        raise ORSServiceError(
            "Reverse geocoding service "
            "returned an invalid response."
        ) from exc

    features = (
        data.get(
            "features"
        )
        or []
    )

    if not features:
        raise LocationValidationError(
            "The selected map location "
            "could not be identified."
        )

    feature = features[0]

    properties = (
        feature.get(
            "properties"
        )
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
        properties.get(
            "label"
        )
        or properties.get(
            "name"
        )
        or (
            f"{float(latitude)}, "
            f"{float(longitude)}"
        )
    )

    matched_area = (
        properties.get(
            "name"
        )
        or properties.get(
            "locality"
        )
        or properties.get(
            "neighbourhood"
        )
        or properties.get(
            "street"
        )
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
        "lat": float(
            latitude
        ),
        "lng": float(
            longitude
        ),
        "district": district,
        "label": label,
        "matched_area": matched_area,
        "raw_properties": properties,
    }


def resolve_map_pin_location(
    latitude: float,
    longitude: float,
    address: str | None = None,
) -> dict:
    """
    Resolve a map-pin location from supplied coordinates.

    Coordinates are authoritative. Reverse geocoding is attempted only
    for optional district/label enrichment. When reverse geocoding is
    unavailable, prediction and routing continue with the supplied
    coordinates.
    """

    _validate_coordinates(
        latitude,
        longitude,
    )

    lat = float(
        latitude
    )

    lng = float(
        longitude
    )

    try:
        return reverse_geocode(
            latitude=lat,
            longitude=lng,
        )

    except LocationValidationError as exc:

        # A successful reverse-geocode response that identifies the
        # location outside the service area must still be rejected.
        message = str(
            exc
        )

        if (
            VALLEY_ONLY_MESSAGE
            in message
            or "outside the supported"
            in message.lower()
        ):
            raise

        logger.warning(
            "Reverse geocoding could not identify "
            "(%s, %s); using supplied coordinates: %s",
            lat,
            lng,
            exc,
        )

    except ORSServiceError as exc:

        logger.warning(
            "Reverse geocoding unavailable for "
            "(%s, %s); using supplied coordinates: %s",
            lat,
            lng,
            exc,
        )

    address_text = (
        address or ""
    ).strip()

    district = (
        _extract_explicit_district(
            address_text
        )
        if address_text
        else None
    )

    return {
        "lat": lat,
        "lng": lng,
        "district": district,
        "label": (
            address_text
            if address_text
            else None
        ),
        "matched_area": (
            address_text
            if address_text
            else None
        ),
        "raw_properties": None,
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

    # Prevent accidental routing from/to the same location.
    if (
        float(origin_lat)
        == float(dest_lat)
        and float(origin_lng)
        == float(dest_lng)
    ):
        raise LocationValidationError(
            "Pickup and delivery "
            "locations must be different."
        )

    api_key = (
        _require_ors_api_key()
    )

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

    except ValueError as exc:

        logger.error(
            "ORS directions returned invalid JSON."
        )

        raise ORSServiceError(
            "Routing service returned "
            "an invalid response."
        ) from exc

    try:

        feature = (
            data[
                "features"
            ][0]
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

    polyline: list[
        dict[str, float]
    ] = []

    for coordinate in coordinates:

        if (
            not isinstance(
                coordinate,
                (list, tuple),
            )
            or len(coordinate) < 2
        ):
            continue

        try:
            route_longitude = float(
                coordinate[0]
            )

            route_latitude = float(
                coordinate[1]
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        if not (
            math.isfinite(
                route_latitude
            )
            and math.isfinite(
                route_longitude
            )
        ):
            continue

        polyline.append(
            {
                "lat": route_latitude,
                "lng": route_longitude,
            }
        )

    if not polyline:
        raise ORSServiceError(
            "Routing service returned "
            "an empty route geometry."
        )

    try:

        distance_km = round(
            float(
                summary[
                    "distance"
                ]
            ) / 1000,
            2,
        )

        duration_min = round(
            float(
                summary[
                    "duration"
                ]
            ) / 60,
            1,
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ) as exc:

        raise ORSServiceError(
            "Routing service returned "
            "invalid distance or duration."
        ) from exc

    if not math.isfinite(
        distance_km
    ) or distance_km <= 0:
        raise ORSServiceError(
            "Routing service returned "
            "an invalid route distance."
        )

    if not math.isfinite(
        duration_min
    ) or duration_min <= 0:
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

        pickup = resolve_map_pin_location(
            latitude=float(
                pickup_latitude
            ),
            longitude=float(
                pickup_longitude
            ),
            address=pickup_address,
        )

        if pickup.get(
            "district"
        ):
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

        pickup_source = (
            "geocoded_address"
        )

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

        delivery = resolve_map_pin_location(
            latitude=float(
                delivery_latitude
            ),
            longitude=float(
                delivery_longitude
            ),
            address=delivery_address,
        )

        if delivery.get(
            "district"
        ):
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

        delivery_source = (
            "geocoded_address"
        )

    # ========================================================
    # PREVENT IDENTICAL LOCATIONS
    # ========================================================

    if (
        float(
            pickup["lat"]
        )
        == float(
            delivery["lat"]
        )
        and float(
            pickup["lng"]
        )
        == float(
            delivery["lng"]
        )
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
        # ----------------------------------------------------
        # Pickup
        # ----------------------------------------------------

        "pickup_district": pickup[
            "district"
        ],

        "pickup_area": pickup[
            "matched_area"
        ],

        "pickup_label": pickup[
            "label"
        ],

        "pickup_geocode_confidence": (
            pickup.get(
                "confidence"
            )
        ),

        "pickup_coordinates": {
            "lat": pickup["lat"],
            "lng": pickup["lng"],
        },

        "pickup_location_source": (
            pickup_source
        ),

        # ----------------------------------------------------
        # Delivery
        # ----------------------------------------------------

        "delivery_district": delivery[
            "district"
        ],

        "delivery_area": delivery[
            "matched_area"
        ],

        "delivery_label": delivery[
            "label"
        ],

        "delivery_geocode_confidence": (
            delivery.get(
                "confidence"
            )
        ),

        "delivery_coordinates": {
            "lat": delivery["lat"],
            "lng": delivery["lng"],
        },

        "delivery_location_source": (
            delivery_source
        ),

        # ----------------------------------------------------
        # Route
        # ----------------------------------------------------

        "estimated_distance_km": driving[
            "distance_km"
        ],

        "baseline_duration_min": driving[
            "duration_min"
        ],

        # This intentionally remains the baseline duration.
        # Traffic service supplies the traffic-adjusted ETA.
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