from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.model import (
    Delivery,
    DeliveryLocation,
    Order,
)


# ============================================================
# CONFIGURATION
# ============================================================

# Exact/nearby location history.
NEARBY_RADIUS_METERS = 250.0

# Minimum completed delivery outcomes required before nearby
# history is trusted as a location-specific estimate.
MIN_NEARBY_HISTORY = 5

# Broader local-area history.
LOCAL_RADIUS_METERS = 1000.0

# Minimum completed delivery outcomes required before the
# broader local-area estimate is trusted.
MIN_LOCAL_HISTORY = 10

# No historical location information exists yet.
#
# This is a neutral prior, NOT a measured location success rate.
DEFAULT_GLOBAL_SUCCESS_RATE = 0.50


# ============================================================
# STATUS DEFINITIONS
# ============================================================

SUCCESS_STATUSES = frozenset(
    {
        "delivered",
        "completed",
        "successful",
        "success",
    }
)

FAILURE_STATUSES = frozenset(
    {
        "failed",
        "failure",
        "delivery_failed",
        "returned",
        "return_to_sender",
        "return_to_sender_completed",
    }
)

UNREACHABLE_STATUSES = frozenset(
    {
        "unreachable",
        "customer_unreachable",
        "no_answer",
        "not_reachable",
        "customer_not_available",
        "not_available",
    }
)


# ============================================================
# SAFE HELPERS
# ============================================================

def _normalize_status(
    value: Any,
) -> str:
    """
    Normalize statuses/reasons into a stable comparison format.

    Examples:

        "Delivered"             -> "delivered"
        "delivery failed"       -> "delivery_failed"
        "Customer Unreachable"  -> "customer_unreachable"
    """

    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


def _safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    Safely convert a value to float.
    """

    if value is None:
        return default

    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return default


def _valid_coordinate_pair(
    latitude: Any,
    longitude: Any,
) -> bool:
    """
    Return True only for finite, globally valid coordinate pairs.
    """

    try:
        lat = float(latitude)
        lon = float(longitude)
    except (
        TypeError,
        ValueError,
    ):
        return False

    if not (
        math.isfinite(lat)
        and math.isfinite(lon)
    ):
        return False

    if not (
        -90.0 <= lat <= 90.0
        and -180.0 <= lon <= 180.0
    ):
        return False

    # Treat the common placeholder pair as invalid history.
    if lat == 0.0 and lon == 0.0:
        return False

    return True


def _haversine_distance_meters(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate great-circle distance between two coordinate pairs.
    """

    earth_radius_m = 6_371_000.0

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    delta_lat = math.radians(
        lat2 - lat1
    )

    delta_lon = math.radians(
        lon2 - lon1
    )

    a = (
        math.sin(delta_lat / 2.0) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(delta_lon / 2.0) ** 2
    )

    a = min(
        max(a, 0.0),
        1.0,
    )

    return (
        2.0
        * earth_radius_m
        * math.atan2(
            math.sqrt(a),
            math.sqrt(1.0 - a),
        )
    )


# ============================================================
# DELIVERY OUTCOME CLASSIFICATION
# ============================================================

def classify_delivery_outcome(
    delivery: Delivery | None,
) -> str:
    """
    Convert a real Delivery record into an analytical outcome.

    Priority:

        1. delivered_at -> SUCCESS
        2. explicit success status -> SUCCESS
        3. unreachable status/reason -> UNREACHABLE
        4. explicit failure status/reason -> FAILURE
        5. otherwise -> UNKNOWN

    UNKNOWN records are excluded from the historical denominator.

    IMPORTANT:
    A model prediction is NEVER considered a delivery outcome.
    """

    if delivery is None:
        return "UNKNOWN"

    # --------------------------------------------------------
    # Strongest success signal
    # --------------------------------------------------------

    if delivery.delivered_at is not None:
        return "SUCCESS"

    # --------------------------------------------------------
    # Explicit delivery status
    # --------------------------------------------------------

    status = _normalize_status(
        getattr(
            delivery,
            "status",
            None,
        )
    )

    if status in SUCCESS_STATUSES:
        return "SUCCESS"

    if status in UNREACHABLE_STATUSES:
        return "UNREACHABLE"

    if status in FAILURE_STATUSES:
        return "FAILURE"

    # --------------------------------------------------------
    # Failure reason fallback
    # --------------------------------------------------------

    failure_reason = _normalize_status(
        getattr(
            delivery,
            "failure_reason",
            None,
        )
    )

    if not failure_reason:
        return "UNKNOWN"

    # Explicit unreachable reasons.
    unreachable_tokens = (
        "unreachable",
        "no_answer",
        "not_reach",
        "not_available",
        "customer_unavailable",
        "customer_not_available",
        "phone_unreachable",
    )

    if any(
        token in failure_reason
        for token in unreachable_tokens
    ):
        return "UNREACHABLE"

    # Any other non-empty failure reason is treated as a failure.
    return "FAILURE"


# ============================================================
# HISTORICAL DELIVERY QUERY
# ============================================================

def _load_historical_deliveries(
    db: Session,
    before_time: datetime,
) -> list[
    tuple[
        Order,
        Delivery,
        DeliveryLocation | None,
    ]
]:
    """
    Load historical delivery records and their location records.

    Uses a LEFT OUTER JOIN for DeliveryLocation so historical
    deliveries without a dedicated location row are still
    available for GLOBAL history.

    Only orders created before before_time are eligible.

    The query intentionally avoids the N+1 pattern that would
    occur if DeliveryLocation were queried separately inside
    the processing loop.
    """

    rows = (
        db.query(
            Order,
            Delivery,
            DeliveryLocation,
        )
        .join(
            Delivery,
            Delivery.order_id == Order.id,
        )
        .outerjoin(
            DeliveryLocation,
            DeliveryLocation.order_id == Order.id,
        )
        .filter(
            Order.created_at < before_time
        )
        .all()
    )

    return rows


# ============================================================
# GLOBAL HISTORY
# ============================================================

def _calculate_global_history(
    rows: list[
        tuple[
            Order,
            Delivery,
            DeliveryLocation | None,
        ]
    ],
) -> dict[str, Any]:
    """
    Calculate historical delivery performance across all
    eligible completed/outcome-known deliveries.

    This is used when there is not enough location-specific
    history.
    """

    successful = 0
    failed = 0
    unreachable = 0

    for _, delivery, _ in rows:
        outcome = classify_delivery_outcome(
            delivery
        )

        if outcome == "SUCCESS":
            successful += 1

        elif outcome == "FAILURE":
            failed += 1

        elif outcome == "UNREACHABLE":
            unreachable += 1

    eligible = (
        successful
        + failed
        + unreachable
    )

    if eligible == 0:
        return {
            "success_rate": (
                DEFAULT_GLOBAL_SUCCESS_RATE
            ),
            "historical_deliveries": 0,
            "successful_deliveries": 0,
            "failed_deliveries": 0,
            "unreachable_deliveries": 0,
            "source": "global_default",
        }

    # Unreachable means the delivery did not successfully
    # reach the customer, so it is included in the denominator
    # but not in the successful count.
    success_rate = (
        successful / eligible
    )

    return {
        "success_rate": round(
            success_rate,
            4,
        ),
        "historical_deliveries": eligible,
        "successful_deliveries": successful,
        "failed_deliveries": failed,
        "unreachable_deliveries": unreachable,
        "source": "global_history",
    }


# ============================================================
# LOCATION RECORD SUMMARY
# ============================================================

def _summarize_location_records(
    records: list[
        tuple[
            float,
            Order,
            Delivery,
            DeliveryLocation | None,
        ]
    ],
) -> dict[str, Any]:
    """
    Summarize known delivery outcomes for a geographic area.

    UNKNOWN outcomes are excluded.
    """

    successful = 0
    failed = 0
    unreachable = 0

    distances = []

    for (
        distance_m,
        _,
        delivery,
        _,
    ) in records:
        distances.append(
            distance_m
        )

        outcome = classify_delivery_outcome(
            delivery
        )

        if outcome == "SUCCESS":
            successful += 1

        elif outcome == "FAILURE":
            failed += 1

        elif outcome == "UNREACHABLE":
            unreachable += 1

    eligible = (
        successful
        + failed
        + unreachable
    )

    if eligible == 0:
        return {
            "success_rate": (
                DEFAULT_GLOBAL_SUCCESS_RATE
            ),
            "historical_deliveries": 0,
            "successful_deliveries": 0,
            "failed_deliveries": 0,
            "unreachable_deliveries": 0,
            "average_distance_m": None,
            "nearest_distance_m": None,
            "source": "no_location_history",
        }

    success_rate = (
        successful / eligible
    )

    return {
        "success_rate": round(
            success_rate,
            4,
        ),
        "historical_deliveries": eligible,
        "successful_deliveries": successful,
        "failed_deliveries": failed,
        "unreachable_deliveries": unreachable,
        "average_distance_m": round(
            sum(distances) / len(distances),
            2,
        )
        if distances
        else None,
        "nearest_distance_m": round(
            min(distances),
            2,
        )
        if distances
        else None,
        "source": "location_history",
    }


# ============================================================
# MAIN LOCATION HISTORY
# ============================================================

def get_location_history(
    db: Session,
    latitude: float,
    longitude: float,
    before_time: datetime | None = None,
) -> dict[str, Any]:
    """
    Calculate historical delivery performance for a geographic
    location.

    Selection strategy:

        nearby <= 250m
            ↓
        local <= 1km
            ↓
        global historical outcomes
            ↓
        neutral global default

    Location-specific history is used only when enough REAL
    delivery outcomes exist.

    Current/future deliveries cannot influence the result because
    before_time is enforced.
    """

    latitude = _safe_float(
        latitude,
        default=float("nan"),
    )

    longitude = _safe_float(
        longitude,
        default=float("nan"),
    )

    if not _valid_coordinate_pair(
        latitude,
        longitude,
    ):
        raise ValueError(
            "Invalid latitude/longitude for "
            "location history lookup."
        )

    if before_time is None:
        before_time = datetime.utcnow()

    rows = _load_historical_deliveries(
        db=db,
        before_time=before_time,
    )

    nearby_records: list[
        tuple[
            float,
            Order,
            Delivery,
            DeliveryLocation | None,
        ]
    ] = []

    local_records: list[
        tuple[
            float,
            Order,
            Delivery,
            DeliveryLocation | None,
        ]
    ] = []

    # ========================================================
    # GEO FILTER
    # ========================================================

    for (
        order,
        delivery,
        location,
    ) in rows:

        historical_lat = None
        historical_lon = None

        # ----------------------------------------------------
        # Preferred dedicated location record
        # ----------------------------------------------------

        if location is not None:
            if _valid_coordinate_pair(
                location.latitude,
                location.longitude,
            ):
                historical_lat = float(
                    location.latitude
                )
                historical_lon = float(
                    location.longitude
                )

        # ----------------------------------------------------
        # Fallback to order coordinates
        # ----------------------------------------------------

        if (
            historical_lat is None
            or historical_lon is None
        ):
            if _valid_coordinate_pair(
                order.latitude,
                order.longitude,
            ):
                historical_lat = float(
                    order.latitude
                )
                historical_lon = float(
                    order.longitude
                )

        # Without coordinates we cannot associate this
        # historical delivery with a physical location.
        if (
            historical_lat is None
            or historical_lon is None
        ):
            continue

        distance_m = _haversine_distance_meters(
            latitude,
            longitude,
            historical_lat,
            historical_lon,
        )

        # Only outcome-known deliveries should contribute to
        # location-specific history.
        outcome = classify_delivery_outcome(
            delivery
        )

        if outcome == "UNKNOWN":
            continue

        record = (
            distance_m,
            order,
            delivery,
            location,
        )

        if distance_m <= NEARBY_RADIUS_METERS:
            nearby_records.append(
                record
            )

        if distance_m <= LOCAL_RADIUS_METERS:
            local_records.append(
                record
            )

    # ========================================================
    # NEARBY HISTORY
    # ========================================================

    nearby_result = _summarize_location_records(
        nearby_records
    )

    if (
        nearby_result["historical_deliveries"]
        >= MIN_NEARBY_HISTORY
    ):
        return {
            **nearby_result,
            "source": "nearby_location",
            "radius_m": NEARBY_RADIUS_METERS,
        }

    # ========================================================
    # LOCAL HISTORY
    # ========================================================

    local_result = _summarize_location_records(
        local_records
    )

    if (
        local_result["historical_deliveries"]
        >= MIN_LOCAL_HISTORY
    ):
        return {
            **local_result,
            "source": "local_area",
            "radius_m": LOCAL_RADIUS_METERS,
        }

    # ========================================================
    # GLOBAL HISTORY
    # ========================================================

    global_result = _calculate_global_history(
        rows
    )

    return {
        **global_result,

        # Helpful debugging information.
        "nearby_history_count": (
            nearby_result[
                "historical_deliveries"
            ]
        ),

        "local_history_count": (
            local_result[
                "historical_deliveries"
            ]
        ),

        "lookup_latitude": latitude,
        "lookup_longitude": longitude,
    }


# ============================================================
# SIMPLE ML ADAPTER
# ============================================================

def get_location_success_rate(
    db: Session,
    latitude: float,
    longitude: float,
    before_time: datetime | None = None,
) -> float:
    """
    Return only the historical success rate required by the
    ML feature vector.

    This function contains no prediction logic.
    """

    result = get_location_history(
        db=db,
        latitude=latitude,
        longitude=longitude,
        before_time=before_time,
    )

    return float(
        result["success_rate"]
    )
