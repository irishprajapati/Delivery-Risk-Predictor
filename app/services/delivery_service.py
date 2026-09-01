from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.model import (
    Customer,
    Delivery,
    DeliveryLocation,
    Order,
    Rider,
    RiderAreaPerformance,
)


# ============================================================
# DELIVERY STATUS
# ============================================================

STATUS_UNASSIGNED = "unassigned"
STATUS_ASSIGNED = "assigned"
STATUS_PICKED_UP = "picked_up"
STATUS_OUT_FOR_DELIVERY = "out_for_delivery"
STATUS_DELIVERED = "delivered"
STATUS_FAILED = "failed"
STATUS_UNREACHABLE = "unreachable"
STATUS_CANCELLED = "cancelled"
STATUS_RETURNED = "returned"


VALID_STATUSES = {
    STATUS_UNASSIGNED,
    STATUS_ASSIGNED,
    STATUS_PICKED_UP,
    STATUS_OUT_FOR_DELIVERY,
    STATUS_DELIVERED,
    STATUS_FAILED,
    STATUS_UNREACHABLE,
    STATUS_CANCELLED,
    STATUS_RETURNED,
}


# ============================================================
# DELIVERY STATE TRANSITIONS
# ============================================================

ALLOWED_TRANSITIONS = {
    STATUS_UNASSIGNED: {
        STATUS_ASSIGNED,
        STATUS_CANCELLED,
    },

    STATUS_ASSIGNED: {
        STATUS_PICKED_UP,
        STATUS_CANCELLED,
    },

    STATUS_PICKED_UP: {
        STATUS_OUT_FOR_DELIVERY,
        STATUS_FAILED,
        STATUS_UNREACHABLE,
        STATUS_RETURNED,
    },

    STATUS_OUT_FOR_DELIVERY: {
        STATUS_DELIVERED,
        STATUS_FAILED,
        STATUS_UNREACHABLE,
        STATUS_RETURNED,
    },

    STATUS_FAILED: {
        STATUS_ASSIGNED,
        STATUS_RETURNED,
        STATUS_CANCELLED,
    },

    STATUS_UNREACHABLE: {
        STATUS_ASSIGNED,
        STATUS_RETURNED,
        STATUS_CANCELLED,
    },

    STATUS_RETURNED: {
        STATUS_CANCELLED,
    },

    STATUS_DELIVERED: set(),

    STATUS_CANCELLED: set(),
}


# ============================================================
# ORDER STATUS
# ============================================================

ORDER_STATUS_PLACED = "placed"
ORDER_STATUS_ASSIGNED = "assigned"
ORDER_STATUS_OUT_FOR_DELIVERY = "out_for_delivery"
ORDER_STATUS_DELIVERED = "delivered"
ORDER_STATUS_FAILED = "failed"
ORDER_STATUS_RETURNED = "returned"
ORDER_STATUS_CANCELLED = "cancelled"


# ============================================================
# RETRY POLICY
# ============================================================

MAX_DELIVERY_ATTEMPTS = 3


# ============================================================
# RIDER LOCATION CONFIGURATION
# ============================================================

# Rider GPS is considered fresh for proximity scoring for this
# amount of time.
RIDER_LOCATION_FRESH_MINUTES = 60

# If the location is older than this, we still allow the rider
# to participate but heavily reduce its proximity contribution.
RIDER_LOCATION_STALE_MINUTES = 180


# ============================================================
# AREA HISTORY CONFIGURATION
# ============================================================

# Minimum number of completed/failed attempts before area
# history is considered established.
MIN_AREA_HISTORY = 5

# Neutral prior prevents a new rider from being treated as
# either excellent or terrible.
AREA_HISTORY_PRIOR_WEIGHT = 5.0

DEFAULT_SUCCESS_RATE = 0.50


# ============================================================
# RISK WEIGHTS
# ============================================================

# The ranking algorithm deliberately changes its priorities
# based on the ML risk level.
#
# LOW:
#   proximity and workload matter more.
#
# MEDIUM:
#   balanced operational decision.
#
# HIGH:
#   reliability and area experience matter more.
RISK_WEIGHT_PROFILES = {
    "LOW": {
        "proximity": 0.40,
        "workload": 0.30,
        "overall_success": 0.20,
        "area_success": 0.10,
    },

    "MEDIUM": {
        "proximity": 0.30,
        "workload": 0.25,
        "overall_success": 0.20,
        "area_success": 0.25,
    },

    "HIGH": {
        "proximity": 0.20,
        "workload": 0.15,
        "overall_success": 0.25,
        "area_success": 0.40,
    },
}


# ============================================================
# SAFE HELPERS
# ============================================================

def _normalize_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
    )


def _safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    if value is None:
        return default

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def _safe_int(
    value: Any,
    default: int = 0,
) -> int:
    if value is None:
        return default

    try:
        return int(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def _clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    return max(
        minimum,
        min(
            value,
            maximum,
        ),
    )


# ============================================================
# DISTANCE
# ============================================================

def _haversine_distance_km(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    """
    Calculate great-circle distance between two GPS points.
    """

    earth_radius_km = 6371.0

    from math import (
        atan2,
        cos,
        radians,
        sin,
        sqrt,
    )

    lat1 = radians(
        latitude_1
    )

    lat2 = radians(
        latitude_2
    )

    delta_lat = radians(
        latitude_2
        - latitude_1
    )

    delta_lon = radians(
        longitude_2
        - longitude_1
    )

    a = (
        sin(
            delta_lat / 2
        ) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(
            delta_lon / 2
        ) ** 2
    )

    a = _clamp(
        a
    )

    return (
        2
        * earth_radius_km
        * atan2(
            sqrt(a),
            sqrt(
                1 - a
            ),
        )
    )


# ============================================================
# ENTITY LOADING
# ============================================================

def get_delivery(
    db: Session,
    delivery_id: int,
) -> Delivery:

    delivery = (
        db.query(
            Delivery
        )
        .filter(
            Delivery.id
            == delivery_id
        )
        .first()
    )

    if delivery is None:
        raise ValueError(
            "Delivery not found."
        )

    return delivery


def get_rider(
    db: Session,
    rider_id: int,
) -> Rider:

    rider = (
        db.query(
            Rider
        )
        .filter(
            Rider.id
            == rider_id
        )
        .first()
    )

    if rider is None:
        raise ValueError(
            "Rider not found."
        )

    return rider


# ============================================================
# RIDER ELIGIBILITY
# ============================================================

def is_rider_eligible(
    rider: Rider,
) -> bool:
    """
    Hard operational constraints.

    A rider must:

    - be active
    - have a valid capacity
    - have remaining capacity
    """

    if not rider.is_active:
        return False

    current_orders = _safe_int(
        rider.current_order_count
    )

    maximum_orders = _safe_int(
        rider.max_orders_per_day
    )

    if maximum_orders <= 0:
        return False

    if current_orders >= maximum_orders:
        return False

    return True


# ============================================================
# RIDER GPS
# ============================================================

def get_rider_location_status(
    rider: Rider,
) -> dict[str, Any]:
    """
    Evaluate whether current rider GPS is available and fresh.
    """

    latitude = rider.current_latitude
    longitude = rider.current_longitude
    updated_at = rider.last_location_update

    if (
        latitude is None
        or longitude is None
    ):
        return {
            "available": False,
            "fresh": False,
            "stale": False,
            "age_minutes": None,
        }

    if updated_at is None:
        return {
            "available": True,
            "fresh": False,
            "stale": True,
            "age_minutes": None,
        }

    now = datetime.utcnow()

    age_minutes = max(
        (
            now - updated_at
        ).total_seconds()
        / 60,
        0.0,
    )

    return {
        "available": True,
        "fresh": (
            age_minutes
            <= RIDER_LOCATION_FRESH_MINUTES
        ),
        "stale": (
            age_minutes
            > RIDER_LOCATION_STALE_MINUTES
        ),
        "age_minutes": round(
            age_minutes,
            2,
        ),
    }


# ============================================================
# RIDER PERFORMANCE
# ============================================================

def rider_failure_rate(
    rider: Rider,
) -> float:

    completed = _safe_int(
        rider.completed_orders
    )

    failed = _safe_int(
        rider.failed_deliveries
    )

    total = (
        completed
        + failed
    )

    if total <= 0:
        return 0.0

    return (
        failed / total
    )


def rider_success_rate(
    rider: Rider,
) -> float:
    """
    Smoothed overall rider success rate.

    This avoids treating a new rider as either 0% or 100%.
    """

    completed = _safe_int(
        rider.completed_orders
    )

    failed = _safe_int(
        rider.failed_deliveries
    )

    total = (
        completed
        + failed
    )

    if total <= 0:
        return DEFAULT_SUCCESS_RATE

    smoothed_success = (
        completed
        + (
            DEFAULT_SUCCESS_RATE
            * AREA_HISTORY_PRIOR_WEIGHT
        )
    ) / (
        total
        + AREA_HISTORY_PRIOR_WEIGHT
    )

    return _clamp(
        smoothed_success
    )


# ============================================================
# DELIVERY AREA
# ============================================================

def _infer_delivery_area(
    order: Order,
    delivery_location: DeliveryLocation | None,
) -> str | None:


    texts = []

    if order.address:
        texts.append(
            _normalize_text(
                order.address
            )
        )

    if delivery_location is not None:
        texts.append(
            _normalize_text(
                delivery_location.address
            )
        )

    combined = " ".join(
        texts
    )

    for district in (
        "kathmandu",
        "lalitpur",
        "bhaktapur",
    ):
        if district in combined:
            return district

    return None


def _get_delivery_area(
    order: Order,
    delivery_location: DeliveryLocation | None,
) -> str | None:
    return _infer_delivery_area(
        order=order,
        delivery_location=delivery_location,
    )
# ============================================================
# AREA HISTORY
# ============================================================

def get_rider_area_performance(
    db: Session,
    rider: Rider,
    area: str | None,
) -> dict[str, Any]:
    """
    Read rider performance for a specific service area.

    A neutral Bayesian-style prior is used when history is small.
    """

    normalized_area = _normalize_text(
        area
    )

    if not normalized_area:
        return {
            "area": None,
            "success_rate": DEFAULT_SUCCESS_RATE,
            "total_deliveries": 0,
            "successful_deliveries": 0,
            "failed_deliveries": 0,
            "source": "no_area_identified",
        }

    history = (
        db.query(
            RiderAreaPerformance
        )
        .filter(
            RiderAreaPerformance.rider_id
            == rider.id,
            func.lower(
                RiderAreaPerformance.area
            )
            == normalized_area,
        )
        .first()
    )

    if history is None:
        return {
            "area": normalized_area,
            "success_rate": DEFAULT_SUCCESS_RATE,
            "total_deliveries": 0,
            "successful_deliveries": 0,
            "failed_deliveries": 0,
            "source": "no_history",
        }

    total = _safe_int(
        history.total_deliveries
    )

    successful = _safe_int(
        history.successful_deliveries
    )

    failed = _safe_int(
        history.failed_deliveries
    )

    # Defensive correction if old/inconsistent data exists.
    observed_total = (
        successful
        + failed
    )

    if total < observed_total:
        total = observed_total

    smoothed_success = (
        successful
        + (
            DEFAULT_SUCCESS_RATE
            * AREA_HISTORY_PRIOR_WEIGHT
        )
    ) / (
        total
        + AREA_HISTORY_PRIOR_WEIGHT
    )

    return {
        "area": normalized_area,
        "success_rate": round(
            _clamp(
                smoothed_success
            ),
            4,
        ),
        "total_deliveries": total,
        "successful_deliveries": successful,
        "failed_deliveries": failed,
        "source": (
            "area_history"
            if total > 0
            else "no_history"
        ),
    }


def _update_rider_area_performance(
    db: Session,
    rider: Rider | None,
    order: Order,
    success: bool,
) -> None:
    """
    Update area-specific rider history after an actual outcome.

    This function is called only after a real delivery attempt
    reaches a terminal success/failure outcome.
    """

    if rider is None:
        return

    delivery_location = (
        order.location
        if order is not None
        else None
    )

    area = _infer_delivery_area(
        order=order,
        delivery_location=delivery_location,
    )

    if not area:
        return

    history = (
        db.query(
            RiderAreaPerformance
        )
        .filter(
            RiderAreaPerformance.rider_id
            == rider.id,
            func.lower(
                RiderAreaPerformance.area
            )
            == area,
        )
        .first()
    )

    if history is None:
        history = RiderAreaPerformance(
            rider_id=rider.id,
            area=area,
            total_deliveries=0,
            successful_deliveries=0,
            failed_deliveries=0,
            success_rate=DEFAULT_SUCCESS_RATE,
        )

        db.add(
            history
        )

    history.total_deliveries = (
        _safe_int(
            history.total_deliveries
        )
        + 1
    )

    if success:
        history.successful_deliveries = (
            _safe_int(
                history.successful_deliveries
            )
            + 1
        )

    else:
        history.failed_deliveries = (
            _safe_int(
                history.failed_deliveries
            )
            + 1
        )

    total = (
        history.successful_deliveries
        + history.failed_deliveries
    )

    history.success_rate = (
        history.successful_deliveries
        / total
        if total > 0
        else DEFAULT_SUCCESS_RATE
    )


# ============================================================
# AREA MATCHING
# ============================================================

def rider_area_matches_delivery(
    rider: Rider,
    delivery_location: DeliveryLocation | None,
    order: Order,
) -> bool:
    """
    Broad service-area familiarity bonus.

    GPS and historical area performance remain the stronger
    signals.
    """

    rider_area = _normalize_text(
        rider.area
    )

    if not rider_area:
        return False

    texts = [
        _normalize_text(
            order.address
        )
    ]

    if delivery_location is not None:
        texts.append(
            _normalize_text(
                delivery_location.address
            )
        )

    combined_text = " ".join(
        texts
    )

    return (
        rider_area in combined_text
        or combined_text in rider_area
    )


# ============================================================
# PROXIMITY SCORE
# ============================================================

def calculate_proximity_score(
    rider: Rider,
    delivery_location: DeliveryLocation | None,
) -> tuple[float, dict[str, Any]]:
    """
    Calculate rider-to-delivery distance score.

    Score:

        <= 1km  -> near 1.0
        10km    -> near 0.0

    Fresh GPS gets full confidence.
    Stale GPS gets reduced confidence.
    Missing GPS gets neutral/low confidence.
    """

    location_status = (
        get_rider_location_status(
            rider
        )
    )

    if (
        not location_status["available"]
        or delivery_location is None
        or delivery_location.latitude is None
        or delivery_location.longitude is None
    ):
        return (
            0.0,
            {
                "available": False,
                "distance_km": None,
                "proximity_score": 0.0,
                "location_age_minutes": (
                    location_status[
                        "age_minutes"
                    ]
                ),
            },
        )

    distance_km = (
        _haversine_distance_km(
            float(
                rider.current_latitude
            ),
            float(
                rider.current_longitude
            ),
            float(
                delivery_location.latitude
            ),
            float(
                delivery_location.longitude
            ),
        )
    )

    # 0 km = 1.0
    # 10+ km = 0.0
    proximity_score = _clamp(
        1.0
        - (
            distance_km
            / 10.0
        )
    )

    if location_status["stale"]:
        proximity_score *= 0.35

    elif not location_status["fresh"]:
        proximity_score *= 0.70

    return (
        round(
            proximity_score,
            4,
        ),
        {
            "available": True,
            "distance_km": round(
                distance_km,
                2,
            ),
            "proximity_score": round(
                proximity_score,
                4,
            ),
            "location_age_minutes": (
                location_status[
                    "age_minutes"
                ]
            ),
            "location_fresh": (
                location_status[
                    "fresh"
                ]
            ),
            "location_stale": (
                location_status[
                    "stale"
                ]
            ),
        },
    )


# ============================================================
# WORKLOAD SCORE
# ============================================================

def calculate_workload_score(
    rider: Rider,
) -> float:

    current_orders = _safe_int(
        rider.current_order_count
    )

    max_orders = max(
        _safe_int(
            rider.max_orders_per_day
        ),
        1,
    )

    load_ratio = _clamp(
        current_orders
        / max_orders
    )

    return round(
        1.0
        - load_ratio,
        4,
    )


# ============================================================
# RISK LEVEL
# ============================================================

def normalize_risk_level(
    risk_level: str | None,
) -> str:
    value = _normalize_text(
        risk_level
    ).upper()

    if value in {
        "LOW",
        "MEDIUM",
        "HIGH",
    }:
        return value

    return "MEDIUM"


def get_order_risk_level(
    order: Order,
) -> str:
    """
    Get the most recent ML prediction risk associated with
    this order, when available.

    If no prediction exists, use MEDIUM as neutral.
    """

    predictions = getattr(
        order,
        "predictions",
        None,
    )

    if not predictions:
        return "MEDIUM"

    latest = max(
        predictions,
        key=lambda item: (
            item.created_at
            or datetime.min
        ),
    )

    return normalize_risk_level(
        latest.risk
    )


# ============================================================
# RIDER SCORE
# ============================================================

def score_rider_for_delivery(
    db: Session,
    rider: Rider,
    delivery_location: DeliveryLocation | None,
    order: Order,
    risk_level: str | None = None,
) -> tuple[
    float,
    dict[str, Any],
]:
    risk = normalize_risk_level(
        risk_level
        or get_order_risk_level(
            order
        )
    )

    weights = (
        RISK_WEIGHT_PROFILES[
            risk
        ]
    )

    proximity_score, proximity_details = (
        calculate_proximity_score(
            rider=rider,
            delivery_location=delivery_location,
        )
    )

    workload_score = (
        calculate_workload_score(
            rider
        )
    )

    overall_success = (
        rider_success_rate(
            rider
        )
    )

    area = _infer_delivery_area(
        order=order,
        delivery_location=delivery_location,
    )

    area_history = (
        get_rider_area_performance(
            db=db,
            rider=rider,
            area=area,
        )
    )

    area_success = _clamp(
        _safe_float(
            area_history[
                "success_rate"
            ],
            DEFAULT_SUCCESS_RATE,
        )
    )

    area_match = (
        rider_area_matches_delivery(
            rider=rider,
            delivery_location=(
                delivery_location
            ),
            order=order,
        )
    )

    # --------------------------------------------------------
    # Dynamic proximity weight
    #
    # A rider without usable GPS should not be punished as if
    # we knew they were far away.
    # --------------------------------------------------------

    effective_weights = dict(
        weights
    )

    if not proximity_details[
        "available"
    ]:
        effective_weights[
            "proximity"
        ] = 0.0

    total_weight = sum(
        effective_weights.values()
    )

    if total_weight <= 0:
        total_weight = 1.0

    # Normalize because some signals may be unavailable.
    normalized_weights = {
        key: (
            value
            / total_weight
        )
        for key, value in (
            effective_weights.items()
        )
    }

    score = (
        proximity_score
        * normalized_weights[
            "proximity"
        ]
    )

    score += (
        workload_score
        * normalized_weights[
            "workload"
        ]
    )

    score += (
        overall_success
        * normalized_weights[
            "overall_success"
        ]
    )

    score += (
        area_success
        * normalized_weights[
            "area_success"
        ]
    )

    # High-risk orders receive an additional reliability bonus
    # when area history is actually established.
    reliability_bonus = 0.0

    if (
        risk == "HIGH"
        and area_history[
            "total_deliveries"
        ] >= MIN_AREA_HISTORY
    ):
        reliability_bonus = (
            area_success
            * 0.05
        )

    score += reliability_bonus

    score = _clamp(
        score,
        0.0,
        1.0,
    )

    current_orders = _safe_int(
        rider.current_order_count
    )

    max_orders = max(
        _safe_int(
            rider.max_orders_per_day
        ),
        1,
    )

    details = {
        "risk_level": risk,

        "assignment_algorithm": (
            "risk_aware_multi_criteria_ranking"
        ),

        "assignment_score": round(
            score,
            4,
        ),

        "proximity": (
            proximity_details
        ),

        "workload": {
            "current_order_count": (
                current_orders
            ),
            "max_orders": (
                max_orders
            ),
            "load_ratio": round(
                current_orders
                / max_orders,
                4,
            ),
            "score": workload_score,
        },

        "overall_performance": {
            "success_rate": round(
                overall_success,
                4,
            ),
            "failure_rate": round(
                rider_failure_rate(
                    rider
                ),
                4,
            ),
            "completed_orders": (
                _safe_int(
                    rider.completed_orders
                )
            ),
            "failed_deliveries": (
                _safe_int(
                    rider.failed_deliveries
                )
            ),
        },

        "area_performance": (
            area_history
        ),

        "area_match": area_match,

        "reliability_bonus": round(
            reliability_bonus,
            4,
        ),
    }

    return (
        round(score, 4),
        details,
    )


# ============================================================
# RANK RIDERS
# ============================================================

def rank_riders(
    db: Session,
    delivery_id: int,
    risk_level: str | None = None,
    exclude_rider_id: int | None = None,
) -> list[dict[str, Any]]:
    """
    Return eligible riders ranked from best to worst.

    Dispatch policy:

    1. Active riders only.
    2. Rider must have available capacity.
    3. If the delivery area is known and matching-area riders
       exist, only matching-area riders are considered.
    4. If no matching-area rider is available, the algorithm
       falls back to other eligible active riders.
    5. Candidates are ranked using:
         - workload
         - overall success
         - area-specific success
         - proximity
         - ML risk
    """

    delivery = get_delivery(
        db,
        delivery_id,
    )

    order = delivery.order

    if order is None:
        raise ValueError(
            "Delivery is not linked to an order."
        )

    delivery_location = order.location

    risk = normalize_risk_level(
        risk_level
        or get_order_risk_level(order)
    )

    delivery_area = _get_delivery_area(
        order=order,
        delivery_location=delivery_location,
    )

    riders = (
        db.query(Rider)
        .filter(
            Rider.is_active.is_(True)
        )
        .all()
    )

    # --------------------------------------------------------
    # HARD ELIGIBILITY: active + capacity
    # --------------------------------------------------------

    eligible_riders = []

    for rider in riders:

        if (
            exclude_rider_id is not None
            and rider.id == exclude_rider_id
        ):
            continue

        if not is_rider_eligible(rider):
            continue

        eligible_riders.append(rider)

    if not eligible_riders:
        return []

    # --------------------------------------------------------
    # AREA MATCHING
    # --------------------------------------------------------

    matching_area_riders = []

    if delivery_area:

        for rider in eligible_riders:

            rider_area = _normalize_text(
                rider.area
            )

            if (
                rider_area
                and rider_area == delivery_area
            ):
                matching_area_riders.append(
                    rider
                )

    # --------------------------------------------------------
    # HARD AREA PREFERENCE
    #
    # If matching-area riders exist, use ONLY them.
    #
    # If none exist, safely fall back to all eligible riders.
    # --------------------------------------------------------

    if matching_area_riders:

        selected_pool = matching_area_riders
        area_fallback = False

    else:

        selected_pool = eligible_riders
        area_fallback = bool(
            delivery_area
        )

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    candidates = []

    for rider in selected_pool:

        score, details = (
            score_rider_for_delivery(
                db=db,
                rider=rider,
                delivery_location=delivery_location,
                order=order,
                risk_level=risk,
            )
        )

        details["delivery_area"] = (
            delivery_area
        )

        details["area_fallback"] = (
            area_fallback
        )

        candidates.append(
            {
                "rider_id": rider.id,
                "rider_name": rider.name,
                "rider_area": rider.area,
                "score": score,
                "details": details,
            }
        )

    # --------------------------------------------------------
    # DETERMINISTIC RANKING
    # --------------------------------------------------------

    candidates.sort(
        key=lambda row: (
            row["score"],
            row["details"][
                "overall_performance"
            ]["success_rate"],
            row["details"][
                "workload"
            ]["score"],
            -row["rider_id"],
        ),
        reverse=True,
    )

    for index, candidate in enumerate(
        candidates,
        start=1,
    ):
        candidate["rank"] = index

    return candidates

def find_best_rider(
    db: Session,
    delivery: Delivery,
    risk_level: str | None = None,
    exclude_rider_id: int | None = None,
) -> tuple[
    Rider,
    dict[str, Any],
]:
    """
    Select highest ranked eligible rider.
    """

    ranked = rank_riders(
        db=db,
        delivery_id=delivery.id,
        risk_level=(
            risk_level
            or get_order_risk_level(
                delivery.order
            )
        ),
        exclude_rider_id=(
            exclude_rider_id
        ),
    )

    if not ranked:
        raise ValueError(
            "No eligible rider is currently available."
        )

    best = ranked[0]

    rider = get_rider(
        db=db,
        rider_id=best[
            "rider_id"
        ],
    )

    details = best[
        "details"
    ]

    details[
        "assignment_score"
    ] = best[
        "score"
    ]

    return (
        rider,
        details,
    )


# ============================================================
# ROUTE INFORMATION
# ============================================================

def update_delivery_route(
    db: Session,
    delivery_id: int,
    distance_km: float,
    estimated_duration: float,
) -> Delivery:

    delivery = get_delivery(
        db,
        delivery_id,
    )

    distance_km = _safe_float(
        distance_km
    )

    estimated_duration = _safe_float(
        estimated_duration
    )

    if distance_km <= 0:
        raise ValueError(
            "distance_km must be greater than zero."
        )

    if estimated_duration <= 0:
        raise ValueError(
            "estimated_duration must be greater than zero."
        )

    delivery.distance_km = round(
        distance_km,
        2,
    )

    delivery.estimated_duration = round(
        estimated_duration,
        2,
    )

    try:
        db.commit()

    except Exception:
        db.rollback()
        raise

    db.refresh(
        delivery
    )

    return delivery


# ============================================================
# ASSIGN DELIVERY
# ============================================================

def assign_delivery(
    db: Session,
    delivery_id: int,
    rider_id: int | None = None,
    risk_level: str | None = None,
) -> dict[str, Any]:
    """
    Assign a delivery.

    Manual rider selection:
        rider_id supplied

    Automatic selection:
        rider_id omitted

    The automatic algorithm is separate from ML.

    ML:
        predicts delivery risk.

    Dispatch algorithm:
        chooses operationally suitable rider.
    """

    delivery = get_delivery(
        db,
        delivery_id,
    )

    current_status = _normalize_text(
        delivery.status
    )

    if current_status not in {
        STATUS_UNASSIGNED,
        STATUS_ASSIGNED,
        STATUS_FAILED,
        STATUS_UNREACHABLE,
    }:
        raise ValueError(
            f"Delivery cannot be assigned "
            f"from status '{delivery.status}'."
        )

    # --------------------------------------------------------
    # Determine risk from latest ML prediction when available.
    # --------------------------------------------------------

    resolved_risk = normalize_risk_level(
        risk_level
        or get_order_risk_level(
            delivery.order
        )
    )

    old_rider_id = delivery.rider_id

    # --------------------------------------------------------
    # Select rider
    # --------------------------------------------------------

    if rider_id is not None:

        rider = get_rider(
            db=db,
            rider_id=rider_id,
        )

        if not is_rider_eligible(
            rider
        ):
            raise ValueError(
                "Selected rider is not eligible "
                "for another delivery."
            )

        delivery_location = (
            delivery.order.location
            if delivery.order
            else None
        )

        score, assignment_details = (
            score_rider_for_delivery(
                db=db,
                rider=rider,
                delivery_location=(
                    delivery_location
                ),
                order=delivery.order,
                risk_level=resolved_risk,
            )
        )

        assignment_details[
            "assignment_score"
        ] = score

        assignment_details[
            "selection_mode"
        ] = "manual"

    else:

        rider, assignment_details = (
            find_best_rider(
                db=db,
                delivery=delivery,
                risk_level=resolved_risk,
                exclude_rider_id=(
                    old_rider_id
                ),
            )
        )

        assignment_details[
            "selection_mode"
        ] = "automatic"

    # --------------------------------------------------------
    # Lock selected rider row before changing workload.
    #
    # This is important when two admin requests try to assign
    # deliveries to the same rider at almost the same time.
    # --------------------------------------------------------

    rider = (
        db.query(
            Rider
        )
        .filter(
            Rider.id == rider.id
        )
        .with_for_update()
        .populate_existing()
        .first()
    )

    if rider is None:
        raise ValueError(
            "Selected rider no longer exists."
        )

    if not is_rider_eligible(
        rider
    ):
        raise ValueError(
            "Selected rider is no longer available."
        )

    # --------------------------------------------------------
    # Increment active rider workload and release previous rider.
    # --------------------------------------------------------

    rider.current_order_count = (
        _safe_int(
            rider.current_order_count
        )
        + 1
    )

    if old_rider_id is not None and old_rider_id != rider.id:
        old_rider = db.query(Rider).filter(Rider.id == old_rider_id).first()
        _release_rider_load(old_rider)

    # --------------------------------------------------------
    # Update delivery.
    # --------------------------------------------------------

    delivery.rider_id = rider.id

    delivery.status = (
        STATUS_ASSIGNED
    )

    delivery.assigned_at = (
        datetime.utcnow()
    )

    if delivery.order is not None:
        delivery.order.status = (
            ORDER_STATUS_ASSIGNED
        )

    try:
        db.commit()

    except Exception:
        db.rollback()
        raise

    db.refresh(
        delivery
    )

    db.refresh(
        rider
    )

    return {
        "delivery_id": delivery.id,
        "order_id": delivery.order_id,
        "rider_id": rider.id,
        "rider_name": rider.name,
        "rider_area": rider.area,

        "delivery_status": (
            delivery.status
        ),

        "assigned_at": (
            delivery.assigned_at
        ),

        "risk_level": (
            resolved_risk
        ),

        "assignment": (
            assignment_details
        ),
    }


# ============================================================
# START DELIVERY
# ============================================================

def start_delivery(
    db: Session,
    delivery_id: int,
) -> dict[str, Any]:
    """
    Start an actual delivery attempt.

    assigned
        ↓
    picked_up
        ↓
    out_for_delivery
    """

    delivery = get_delivery(
        db,
        delivery_id,
    )

    current_status = _normalize_text(
        delivery.status
    )

    if current_status != STATUS_ASSIGNED:
        raise ValueError(
            "Only an assigned delivery "
            "can be started."
        )

    if delivery.rider_id is None:
        raise ValueError(
            "Delivery has no assigned rider."
        )

    attempts = _safe_int(
        delivery.attempt_count
    )

    if attempts >= MAX_DELIVERY_ATTEMPTS:
        raise ValueError(
            "Maximum delivery attempts reached."
        )

    delivery.attempt_count = (
        attempts + 1
    )

    delivery.status = (
        STATUS_PICKED_UP
    )

    if delivery.order is not None:
        delivery.order.status = (
            ORDER_STATUS_ASSIGNED
        )

    try:
        db.commit()

    except Exception:
        db.rollback()
        raise

    db.refresh(
        delivery
    )

    return {
        "delivery_id": delivery.id,
        "order_id": delivery.order_id,
        "rider_id": delivery.rider_id,
        "attempt_count": (
            delivery.attempt_count
        ),
        "status": delivery.status,
        "message": (
            "Delivery attempt started."
        ),
    }


# ============================================================
# MARK OUT FOR DELIVERY
# ============================================================

def mark_out_for_delivery(
    db: Session,
    delivery_id: int,
) -> Delivery:

    delivery = get_delivery(
        db,
        delivery_id,
    )

    current_status = _normalize_text(
        delivery.status
    )

    if current_status != STATUS_PICKED_UP:
        raise ValueError(
            "Only a picked-up delivery "
            "can be marked out for delivery."
        )

    delivery.status = (
        STATUS_OUT_FOR_DELIVERY
    )

    if delivery.order is not None:
        delivery.order.status = (
            ORDER_STATUS_OUT_FOR_DELIVERY
        )

    try:
        db.commit()

    except Exception:
        db.rollback()
        raise

    db.refresh(
        delivery
    )

    return delivery


# ============================================================
# RELEASE RIDER LOAD
# ============================================================

def _release_rider_load(
    rider: Rider | None,
) -> None:

    if rider is None:
        return

    current = _safe_int(
        rider.current_order_count
    )

    rider.current_order_count = max(
        current - 1,
        0,
    )


# ============================================================
# COMPLETE DELIVERY
# ============================================================

def complete_delivery(
    db: Session,
    delivery_id: int,
    actual_duration: float | None = None,
) -> dict[str, Any]:
    """
    Record successful delivery.

    This is also where:

        Rider performance
        Customer history
        Rider-area history

    become real historical data.
    """

    delivery = get_delivery(
        db,
        delivery_id,
    )

    current_status = _normalize_text(
        delivery.status
    )

    if current_status not in {
        STATUS_PICKED_UP,
        STATUS_OUT_FOR_DELIVERY,
    }:
        raise ValueError(
            "Only an active delivery attempt "
            "can be completed."
        )

    if delivery.order is None:
        raise ValueError(
            "Delivery is not linked to an order."
        )

    rider = delivery.rider
    customer = delivery.order.customer

    now = datetime.utcnow()

    delivery.status = (
        STATUS_DELIVERED
    )

    delivery.delivered_at = now

    if actual_duration is not None:

        actual_duration = _safe_float(
            actual_duration
        )

        if actual_duration <= 0:
            raise ValueError(
                "actual_duration must be greater than zero."
            )

        delivery.actual_duration = round(
            actual_duration,
            2,
        )

    _release_rider_load(
        rider
    )

    if rider is not None:

        rider.completed_orders = (
            _safe_int(
                rider.completed_orders
            )
            + 1
        )

    if customer is not None:

        customer.successful_deliveries = (
            _safe_int(
                customer.successful_deliveries
            )
            + 1
        )

        customer.last_successful_delivery = now

    delivery.order.status = (
        ORDER_STATUS_DELIVERED
    )

    # --------------------------------------------------------
    # Update rider-area history.
    # --------------------------------------------------------

    _update_rider_area_performance(
        db=db,
        rider=rider,
        order=delivery.order,
        success=True,
    )

    try:
        db.commit()

    except Exception:
        db.rollback()
        raise

    db.refresh(
        delivery
    )

    return {
        "delivery_id": delivery.id,
        "order_id": delivery.order_id,
        "rider_id": delivery.rider_id,
        "status": delivery.status,
        "delivered_at": (
            delivery.delivered_at
        ),
        "actual_duration": (
            delivery.actual_duration
        ),
        "attempt_count": (
            delivery.attempt_count
        ),
        "message": (
            "Delivery completed successfully."
        ),
    }


# ============================================================
# FAIL DELIVERY
# ============================================================

def fail_delivery(
    db: Session,
    delivery_id: int,
    failure_reason: str,
    unreachable: bool = False,
) -> dict[str, Any]:
    """
    Record a real failed delivery attempt.

    The rider's current workload is released.

    Rider/customer/area history is updated.

    A retry is possible until MAX_DELIVERY_ATTEMPTS.
    """

    delivery = get_delivery(
        db,
        delivery_id,
    )

    current_status = _normalize_text(
        delivery.status
    )

    if current_status not in {
        STATUS_PICKED_UP,
        STATUS_OUT_FOR_DELIVERY,
    }:
        raise ValueError(
            "Only an active delivery attempt "
            "can be marked failed."
        )

    reason = (
        str(
            failure_reason
            or ""
        )
        .strip()
    )

    if not reason:
        raise ValueError(
            "failure_reason is required."
        )

    if delivery.order is None:
        raise ValueError(
            "Delivery is not linked to an order."
        )

    rider = delivery.rider
    customer = delivery.order.customer

    delivery.failure_reason = reason

    if unreachable:
        delivery.status = (
            STATUS_UNREACHABLE
        )
    else:
        delivery.status = (
            STATUS_FAILED
        )

    _release_rider_load(
        rider
    )

    if rider is not None:

        rider.failed_deliveries = (
            _safe_int(
                rider.failed_deliveries
            )
            + 1
        )

    if customer is not None:

        if unreachable:

            customer.unreachable_count = (
                _safe_int(
                    customer.unreachable_count
                )
                + 1
            )

        else:

            customer.failed_deliveries = (
                _safe_int(
                    customer.failed_deliveries
                )
                + 1
            )

    # --------------------------------------------------------
    # Update rider-area history.
    # --------------------------------------------------------

    _update_rider_area_performance(
        db=db,
        rider=rider,
        order=delivery.order,
        success=False,
    )

    attempts = _safe_int(
        delivery.attempt_count
    )

    if attempts < MAX_DELIVERY_ATTEMPTS:

        delivery.order.status = (
            ORDER_STATUS_ASSIGNED
        )

        retry_available = True

    else:

        delivery.order.status = (
            ORDER_STATUS_RETURNED
        )

        delivery.status = (
            STATUS_RETURNED
        )

        retry_available = False

    try:
        db.commit()

    except Exception:
        db.rollback()
        raise

    db.refresh(
        delivery
    )

    return {
        "delivery_id": delivery.id,

        "order_id": (
            delivery.order_id
        ),

        "rider_id": (
            delivery.rider_id
        ),

        "status": (
            delivery.status
        ),

        "failure_reason": (
            delivery.failure_reason
        ),

        "attempt_count": (
            delivery.attempt_count
        ),

        "retry_available": (
            retry_available
        ),

        "max_attempts": (
            MAX_DELIVERY_ATTEMPTS
        ),

        "message": (
            "Delivery failed and may be reassigned."
            if retry_available
            else
            "Maximum delivery attempts reached. "
            "Order marked for return."
        ),
    }


# ============================================================
# CANCEL DELIVERY
# ============================================================

def cancel_delivery(
    db: Session,
    delivery_id: int,
    reason: str = (
        "Cancelled by customer or operations"
    ),
) -> Delivery:

    delivery = get_delivery(
        db,
        delivery_id,
    )

    current_status = _normalize_text(
        delivery.status
    )

    if current_status in {
        STATUS_DELIVERED,
        STATUS_CANCELLED,
        STATUS_RETURNED,
    }:
        raise ValueError(
            f"Delivery cannot be cancelled "
            f"from status '{delivery.status}'."
        )

    rider = delivery.rider
    customer = delivery.order.customer if delivery.order else None

    delivery.status = (
        STATUS_CANCELLED
    )

    delivery.failure_reason = (
        reason
        if reason
        else "Cancelled"
    )

    _release_rider_load(
        rider
    )

    if customer is not None:
        customer.cancellation_count = (
            _safe_int(
                customer.cancellation_count
            )
            + 1
        )

    if delivery.order is not None:
        delivery.order.status = (
            ORDER_STATUS_CANCELLED
        )

    try:
        db.commit()

    except Exception:
        db.rollback()
        raise

    db.refresh(
        delivery
    )

    return delivery


# ============================================================
# RETRY / REASSIGN
# ============================================================

def reassign_failed_delivery(
    db: Session,
    delivery_id: int,
) -> dict[str, Any]:
    """
    Reassign a failed/unreachable delivery.

    Important:
        The rider from the failed attempt is excluded from the
        next automatic selection so the same rider is not
        immediately given the same failed delivery again.
    """

    delivery = get_delivery(
        db,
        delivery_id,
    )

    current_status = _normalize_text(
        delivery.status
    )

    if current_status not in {
        STATUS_FAILED,
        STATUS_UNREACHABLE,
    }:
        raise ValueError(
            "Only failed or unreachable deliveries "
            "can be reassigned."
        )

    attempts = _safe_int(
        delivery.attempt_count
    )

    if attempts >= MAX_DELIVERY_ATTEMPTS:
        raise ValueError(
            "Maximum delivery attempts reached. "
            "Delivery cannot be reassigned."
        )

    previous_rider_id = (
        delivery.rider_id
    )

    delivery.rider_id = None

    delivery.status = (
        STATUS_UNASSIGNED
    )

    delivery.assigned_at = None

    if delivery.order is not None:
        delivery.order.status = (
            ORDER_STATUS_ASSIGNED
        )

    try:
        db.commit()

    except Exception:
        db.rollback()
        raise

    resolved_risk = (
        get_order_risk_level(
            delivery.order
        )
    )

    rider, assignment_details = (
        find_best_rider(
            db=db,
            delivery=delivery,
            risk_level=resolved_risk,
            exclude_rider_id=(
                previous_rider_id
            ),
        )
    )

    # We intentionally route through assign_delivery logic to
    # keep workload handling centralized.
    return assign_delivery(
        db=db,
        delivery_id=delivery.id,
        rider_id=rider.id,
        risk_level=resolved_risk,
    )


# ============================================================
# DELIVERY SUMMARY
# ============================================================

def get_delivery_summary(
    db: Session,
    delivery_id: int,
) -> dict[str, Any]:

    delivery = get_delivery(
        db,
        delivery_id,
    )

    order = delivery.order
    rider = delivery.rider

    location = (
        order.location
        if order is not None
        else None
    )

    rider_summary = None

    if rider is not None:

        area = _infer_delivery_area(
            order=order,
            delivery_location=location,
        )

        area_history = (
            get_rider_area_performance(
                db=db,
                rider=rider,
                area=area,
            )
        )

        rider_summary = {
            "id": rider.id,
            "name": rider.name,
            "phone": rider.phone,
            "area": rider.area,

            "current_latitude": (
                rider.current_latitude
            ),

            "current_longitude": (
                rider.current_longitude
            ),

            "last_location_update": (
                rider.last_location_update
            ),

            "is_active": (
                rider.is_active
            ),

            "current_order_count": (
                rider.current_order_count
            ),

            "max_orders_per_day": (
                rider.max_orders_per_day
            ),

            "completed_orders": (
                rider.completed_orders
            ),

            "failed_deliveries": (
                rider.failed_deliveries
            ),

            "overall_success_rate": round(
                rider_success_rate(
                    rider
                ),
                4,
            ),

            "area_performance": (
                area_history
            ),
        }

    prediction_summary = None
    if order is not None and order.predictions:
        latest_p = sorted(
            order.predictions,
            key=lambda p: p.created_at or datetime.min,
            reverse=True,
        )[0]
        prediction_summary = {
            "id": latest_p.id,
            "prediction": latest_p.prediction,
            "predicted_class": (
                "Delivery Failure Likely"
                if latest_p.prediction == 1
                else "Successful Delivery"
            ),
            "probability": latest_p.probability,
            "risk": str(latest_p.risk or order.risk_level or "LOW").upper(),
            "input_data": latest_p.input_data,
            "reasons": (latest_p.input_data or {}).get("reasons", []),
            "shap_factors": (latest_p.input_data or {}).get("shap_factors", []),
            "created_at": (
                latest_p.created_at.isoformat()
                if latest_p.created_at
                else None
            ),
        }

    return {
        "delivery_id": delivery.id,
        "order_id": delivery.order_id,
        "risk_level": (
            (prediction_summary.get("risk") if prediction_summary else None)
            or (order.risk_level if order else "LOW")
        ),
        "status": (
            delivery.status
        ),

        "attempt_count": (
            delivery.attempt_count
        ),

        "failure_reason": (
            delivery.failure_reason
        ),

        "distance_km": (
            delivery.distance_km
        ),

        "estimated_duration": (
            delivery.estimated_duration
        ),

        "actual_duration": (
            delivery.actual_duration
        ),

        "assigned_at": (
            delivery.assigned_at
        ),

        "delivered_at": (
            delivery.delivered_at
        ),

        "rider": rider_summary,
        "prediction": prediction_summary,

        "location": (
            None
            if location is None
            else {
                "address": location.address,
                "latitude": (
                    location.latitude
                ),
                "longitude": (
                    location.longitude
                ),
                "address_quality": (
                    location.address_quality
                ),
                "distance_km": (
                    location.distance_km
                ),
                "estimated_duration": (
                    location.estimated_duration
                ),
                "location_success_rate": (
                    location.location_success_rate
                ),
            }
        ),

        "order": (
            None
            if order is None
            else {
                "id": order.id,
                "customer_id": (
                    order.customer_id
                ),
                "customer_phone": (
                    order.customer.phone
                    if order.customer
                    else None
                ),
                "item_id": (
                    order.item_id
                ),
                "item_name": (
                    order.item.name
                    if order.item
                    else "Package"
                ),
                "quantity": (
                    order.quantity
                ),

                "total_price": (
                    order.total_price
                ),

                "is_cod": (
                    order.is_cod
                ),

                "prepaid_amount": (
                    order.prepaid_amount
                ),

                "address": (
                    order.address
                ),

                "area": (
                    _infer_delivery_area(
                        order=order,
                        delivery_location=location,
                    )
                ),

                "latitude": (
                    order.latitude
                ),

                "longitude": (
                    order.longitude
                ),

                "status": (
                    order.status
                ),

                "created_at": (
                    order.created_at.isoformat()
                    if order.created_at
                    else None
                ),
            }
        ),
    }


# ============================================================
# AUTOMATIC DISPATCH ENGINE
# ============================================================

def auto_dispatch_order(
    db: Session,
    order_id: int,
    delivery_id: int,
) -> dict[str, Any]:
    """
    Automated pre-dispatch pipeline triggered after order creation.
    
    1. Gathers pre-dispatch features for the order.
    2. Runs ML failure risk prediction (Logistic Regression).
    3. Persists Prediction record and saves risk_level on Order.
    4. Evaluates eligible fleet riders using multi-criteria ranking.
    5. Automatically assigns the top-ranked eligible rider using row locks.
    6. If no rider is available, leaves delivery as 'unassigned' safely without raising exceptions.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        from app.model import Order, Delivery, DeliveryLocation, Prediction, Customer
        from app.services.ors_service import build_route_info
        from app.services.weather_service import fetch_route_weather
        from app.services.traffic_service import build_traffic_context
        from app.services.feature_engineering import build_features
        from app.ml.predictor import predict, classify_risk

        order = db.query(Order).filter(Order.id == order_id).first()
        delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()

        if not order or not delivery:
            logger.warning(
                f"auto_dispatch_order: order {order_id} or delivery {delivery_id} not found."
            )
            return {
                "status": "unassigned",
                "reason": "Order or delivery record not found.",
            }

        if delivery.status not in {
            STATUS_UNASSIGNED,
            STATUS_FAILED,
            STATUS_UNREACHABLE,
        }:
            logger.info(
                f"auto_dispatch_order: delivery {delivery_id} already in status '{delivery.status}'."
            )
            return {
                "status": delivery.status,
                "rider_id": delivery.rider_id,
                "risk_level": order.risk_level,
            }

        delivery_loc = (
            order.location
            or db.query(DeliveryLocation)
            .filter(DeliveryLocation.order_id == order.id)
            .first()
        )

        # --------------------------------------------------------
        # Step 1: Spatial Route Info
        # --------------------------------------------------------
        try:
            route_info = build_route_info(
                pickup_address="Balkumari, Lalitpur, Nepal",
                pickup_latitude=27.6710,
                pickup_longitude=85.3380,
                delivery_address=order.address,
                delivery_latitude=order.latitude,
                delivery_longitude=order.longitude,
            )
        except Exception as exc:
            logger.warning(
                f"auto_dispatch_order: ORS routing failed, using fallback: {exc}"
            )
            route_info = {
                "distance_km": 5.0,
                "estimated_duration_min": 20.0,
                "pickup_district": "Lalitpur",
                "delivery_district": (
                    _infer_delivery_area(
                        order,
                        delivery_loc,
                    )
                    or "Kathmandu"
                ),
            }

        distance_km = float(
            route_info.get(
                "distance_km",
                5.0,
            )
        )
        estimated_duration = float(
            route_info.get(
                "estimated_duration_min",
                20.0,
            )
        )

        # Update delivery spatial baseline
        delivery.distance_km = round(
            distance_km,
            2,
        )
        delivery.estimated_duration = round(
            estimated_duration,
            2,
        )
        if delivery_loc:
            delivery_loc.distance_km = round(
                distance_km,
                2,
            )
            delivery_loc.estimated_duration = round(
                estimated_duration,
                2,
            )

        # --------------------------------------------------------
        # Step 2: Weather Info
        # --------------------------------------------------------
        try:
            weather_info = fetch_route_weather(route_info)
        except Exception as exc:
            logger.warning(
                f"auto_dispatch_order: Weather fetch failed, using fallback: {exc}"
            )
            weather_info = {
                "route_weather": "CLEAR",
                "rainfall": 0.0,
                "temperature": 22.0,
            }

        # --------------------------------------------------------
        # Step 3: Traffic Context
        # --------------------------------------------------------
        try:
            traffic_context = build_traffic_context(
                route_info=route_info,
                weather_info=weather_info,
                order_time=datetime.utcnow(),
                historical_delay_minutes=None,
            )
        except Exception as exc:
            logger.warning(
                f"auto_dispatch_order: Traffic estimation failed, using fallback: {exc}"
            )
            traffic_context = {
                "traffic_level": "MEDIUM",
                "traffic_delay_minutes": 5.0,
                "baseline_duration_min": estimated_duration,
                "traffic_delay_ratio": 0.25,
            }

        # --------------------------------------------------------
        # Step 4: Assemble 41 Features
        # --------------------------------------------------------
        customer = (
            order.customer
            or db.query(Customer)
            .filter(Customer.id == order.customer_id)
            .first()
        )

        location_data = {
            "address_quality": (
                0.85
                if order.latitude and order.longitude
                else 0.50
            ),
            "distance_km": distance_km,
            "estimated_duration": estimated_duration,
            "location_success_rate": 0.85,
        }

        environment_data = {
            "weather": weather_info.get(
                "route_weather",
                "CLEAR",
            ),
            "rainfall": weather_info.get(
                "rainfall",
                0.0,
            ),
            "temperature": weather_info.get(
                "temperature",
                22.0,
            ),
            "traffic_level": traffic_context.get(
                "traffic_level",
                "MEDIUM",
            ),
            "traffic_delay_minutes": traffic_context.get(
                "traffic_delay_minutes",
                0.0,
            ),
            "baseline_duration": estimated_duration,
        }

        operational_data = {
            "hub_delay_minutes": 0.0,
            "route_status": "NORMAL",
            "vehicle_status": "AVAILABLE",
        }

        features = build_features(
            customer=customer,
            quantity=order.quantity,
            total_price=order.total_price,
            is_cod=order.is_cod,
            prepaid_amount=order.prepaid_amount,
            location_data=location_data,
            environment_data=environment_data,
            operational_data=operational_data,
            order_time=(
                order.created_at
                or datetime.utcnow()
            ),
        )

        # --------------------------------------------------------
        # Step 5: Execute ML Prediction
        # --------------------------------------------------------
        ml_succeeded = False
        prob = None
        risk = "MEDIUM"

        try:
            pred_result = predict(features)
            prob = float(
                pred_result.get(
                    "probability",
                    0.35,
                )
            )
            risk = str(
                pred_result.get(
                    "risk",
                    classify_risk(prob),
                )
            ).upper()
            ml_succeeded = True
        except Exception as exc:
            logger.error(
                f"auto_dispatch_order: ML prediction failed ({exc}), falling back to MEDIUM risk policy for dispatch."
            )
            prob = None
            risk = "MEDIUM"
            ml_succeeded = False

        # --------------------------------------------------------
        # Step 6: Save Prediction record & Update Order
        # --------------------------------------------------------
        if ml_succeeded and prob is not None:
            order.risk_score = round(prob, 4)
            order.risk_level = risk

            try:
                pred_record = Prediction(
                    order_id=order.id,
                    input_data=features,
                    prediction=(
                        1
                        if prob >= 0.50
                        else 0
                    ),
                    probability=round(prob, 4),
                    risk=risk,
                )
                db.add(pred_record)
                db.flush()
            except Exception as exc:
                logger.warning(
                    f"auto_dispatch_order: Failed to persist Prediction record: {exc}"
                )
        else:
            order.risk_score = None
            order.risk_level = "MEDIUM"

        # --------------------------------------------------------
        # Step 7: Automatic Rider Assignment via row locking
        # --------------------------------------------------------
        try:
            assign_result = assign_delivery(
                db=db,
                delivery_id=delivery.id,
                rider_id=None,
                risk_level=risk,
            )
            db.commit()
            logger.info(
                f"auto_dispatch_order: Order {order.id} automatically assigned to Rider {delivery.rider_id} with risk {risk}."
            )
            return {
                "status": "assigned",
                "rider_id": delivery.rider_id,
                "risk_level": risk,
                "probability": (
                    round(prob, 4)
                    if prob is not None
                    else None
                ),
                "assignment": assign_result,
            }
        except ValueError as exc:
            # No eligible rider available or all riders full
            logger.warning(
                f"auto_dispatch_order: Could not assign rider for order {order.id}: {exc}"
            )
            db.commit()  # commit prediction and route baseline, leave delivery unassigned
            return {
                "status": "unassigned",
                "rider_id": None,
                "risk_level": risk,
                "probability": (
                    round(prob, 4)
                    if prob is not None
                    else None
                ),
                "reason": str(exc),
            }

    except Exception as exc:
        logger.exception(
            f"auto_dispatch_order: Unexpected error in auto-dispatch: {exc}"
        )
        db.rollback()
        return {
            "status": "unassigned",
            "rider_id": None,
            "error": str(exc),
        }