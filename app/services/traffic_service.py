"""
Traffic intelligence service for pre-dispatch delivery prediction.

This service DOES NOT pretend to provide live traffic.

Traffic is estimated from information available before dispatch:

    - day of week
    - time of day
    - weekday/weekend
    - morning/evening peak
    - school/office peak
    - route distance
    - baseline route duration
    - current route weather
    - optional historical route delay

The output is aligned with the 41-feature ML contract:

    traffic_level
    traffic_delay_minutes
    traffic_delay_ratio

Traffic source values:

    time_pattern_estimator
    historical_route_estimator
    historical_plus_time_pattern

Routing itself belongs to ors_service.py.
Weather retrieval itself belongs to weather_service.py.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


# ============================================================
# CONSTANTS
# ============================================================

VALID_TRAFFIC_LEVELS = frozenset(
    {
        "LOW",
        "MEDIUM",
        "HIGH",
        "SEVERE",
    }
)

VALID_TRAFFIC_SOURCES = frozenset(
    {
        "time_pattern_estimator",
        "historical_route_estimator",
        "historical_plus_time_pattern",
    }
)

MAX_ESTIMATED_DELAY_MINUTES = 90.0

# Never allow the estimated traffic delay to exceed 150%
# of the baseline duration.
MAX_DELAY_RATIO = 1.50


# ============================================================
# SAFE CONVERSION
# ============================================================

def _safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """Safely convert a value to float."""

    if value is None:
        return default

    try:
        result = float(value)

        if result != result:  # NaN
            return default

        if result in (
            float("inf"),
            float("-inf"),
        ):
            return default

        return result

    except (
        TypeError,
        ValueError,
    ):
        return default


def _safe_int(
    value: Any,
    default: int = 0,
) -> int:
    """Safely convert a value to int."""

    if value is None:
        return default

    try:
        return int(value)
    except (
        TypeError,
        ValueError,
    ):
        return default


# ============================================================
# TIME CLASSIFICATION
# ============================================================

def classify_day_type(
    day_of_week: int,
) -> str:
    """
    Python weekday:

        0-4 -> WEEKDAY
        5   -> SATURDAY
        6   -> SUNDAY
    """

    day_of_week = _safe_int(
        day_of_week,
        0,
    )

    if day_of_week == 5:
        return "SATURDAY"

    if day_of_week == 6:
        return "SUNDAY"

    return "WEEKDAY"


def classify_time_period(
    hour: int,
) -> str:
    """
    Time-period contract shared with feature_engineering.py.

        00-05 -> NIGHT
        06-07 -> EARLY_MORNING
        08-10 -> MORNING
        11-14 -> MIDDAY
        15-16 -> AFTERNOON
        17-19 -> EVENING
        20-23 -> LATE_NIGHT
    """

    hour = max(
        0,
        min(
            _safe_int(hour, 0),
            23,
        ),
    )

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


def is_weekend(
    day_of_week: int,
) -> bool:
    """Return True for Saturday/Sunday."""

    return _safe_int(
        day_of_week,
        0,
    ) >= 5


def is_morning_peak(
    hour: int,
    day_of_week: int,
) -> bool:
    """Weekday morning commuting period."""

    return (
        not is_weekend(day_of_week)
        and 8 <= hour <= 10
    )


def is_evening_peak(
    hour: int,
    day_of_week: int,
) -> bool:
    """Weekday evening commuting period."""

    return (
        not is_weekend(day_of_week)
        and 17 <= hour <= 19
    )


def is_school_peak(
    hour: int,
    day_of_week: int,
) -> bool:
    """
    Temporal school-period indicator.

    This is contextual information, not a claim that every
    road has school traffic at these exact hours.
    """

    return (
        not is_weekend(day_of_week)
        and (
            7 <= hour <= 9
            or 15 <= hour <= 17
        )
    )


def is_office_peak(
    hour: int,
    day_of_week: int,
) -> bool:
    """
    Temporal office-period indicator.

    This is contextual information, not live traffic.
    """

    return (
        not is_weekend(day_of_week)
        and (
            8 <= hour <= 10
            or 16 <= hour <= 19
        )
    )


# ============================================================
# WEATHER NORMALIZATION
# ============================================================

def normalize_weather(
    weather: Any,
) -> str:
    """Normalize weather into the ML-compatible categories."""

    value = str(
        weather or "CLEAR"
    ).strip().upper()

    aliases = {
        "NORMAL": "CLEAR",
        "SUNNY": "CLEAR",
        "CLOUD": "CLOUDY",
        "CLOUDS": "CLOUDY",
        "DRIZZLE": "RAIN",
        "RAINY": "RAIN",
        "FOGGY": "FOG",
        "MIST": "FOG",
        "THUNDERSTORM": "STORM",
    }

    value = aliases.get(
        value,
        value,
    )

    valid_values = {
        "CLEAR",
        "CLOUDY",
        "FOG",
        "RAIN",
        "STORM",
        "SNOW",
    }

    if value not in valid_values:
        return "CLOUDY"

    return value


# ============================================================
# TRAFFIC LEVEL
# ============================================================

def classify_traffic_level(
    delay_minutes: float,
) -> str:
    """
    Convert estimated traffic delay into the frozen
    traffic categories.

        < 5 min   -> LOW
        < 15 min  -> MEDIUM
        < 30 min  -> HIGH
        >= 30 min -> SEVERE
    """

    delay_minutes = max(
        _safe_float(
            delay_minutes
        ),
        0.0,
    )

    if delay_minutes < 5:
        return "LOW"

    if delay_minutes < 15:
        return "MEDIUM"

    if delay_minutes < 30:
        return "HIGH"

    return "SEVERE"


# ============================================================
# TIME PATTERN SCORE
# ============================================================

def _time_pattern_score(
    hour: int,
    day_of_week: int,
) -> float:
    """
    Estimate congestion pressure from time/day context.

    This is a transparent estimator, not a live traffic reading.
    """

    score = 0.10

    weekend = is_weekend(
        day_of_week
    )

    morning_peak = is_morning_peak(
        hour,
        day_of_week,
    )

    evening_peak = is_evening_peak(
        hour,
        day_of_week,
    )

    school_peak = is_school_peak(
        hour,
        day_of_week,
    )

    office_peak = is_office_peak(
        hour,
        day_of_week,
    )

    if weekend:
        score += 0.05
    else:
        score += 0.10

    if morning_peak:
        score += 0.30

    if evening_peak:
        score += 0.35

    if school_peak:
        score += 0.10

    if office_peak:
        score += 0.15

    if (
        11 <= hour <= 14
        and not weekend
    ):
        score -= 0.05

    if 0 <= hour <= 5:
        score -= 0.10

    return max(
        0.0,
        min(
            score,
            1.0,
        ),
    )


# ============================================================
# ROUTE CONTRIBUTION
# ============================================================

def _route_score(
    distance_km: float,
    baseline_duration_min: float,
) -> float:
    """
    Estimate additional traffic pressure from route scale.

    Long routes are not automatically considered congested.
    They simply provide more opportunity for delay.
    """

    distance_km = max(
        _safe_float(distance_km),
        0.0,
    )

    baseline_duration_min = max(
        _safe_float(
            baseline_duration_min
        ),
        0.0,
    )

    score = 0.0

    if distance_km >= 15:
        score += 0.20
    elif distance_km >= 10:
        score += 0.12
    elif distance_km >= 5:
        score += 0.06

    if baseline_duration_min >= 60:
        score += 0.20
    elif baseline_duration_min >= 40:
        score += 0.12
    elif baseline_duration_min >= 25:
        score += 0.06

    return min(
        score,
        0.40,
    )


# ============================================================
# WEATHER CONTRIBUTION
# ============================================================

def _weather_score(
    weather: Any,
    rainfall: float,
) -> float:
    """
    Estimate traffic pressure caused by adverse weather.
    """

    weather = normalize_weather(
        weather
    )

    rainfall = max(
        _safe_float(
            rainfall
        ),
        0.0,
    )

    score = 0.0

    if weather == "CLOUDY":
        score += 0.01

    elif weather == "FOG":
        score += 0.12

    elif weather == "RAIN":
        score += 0.15

    elif weather == "STORM":
        score += 0.30

    elif weather == "SNOW":
        score += 0.25

    if rainfall >= 20:
        score += 0.20

    elif rainfall >= 10:
        score += 0.12

    elif rainfall > 0:
        score += 0.04

    return min(
        score,
        0.50,
    )


# ============================================================
# DELAY ESTIMATION
# ============================================================

def estimate_time_pattern_delay(
    hour: int,
    day_of_week: int,
    distance_km: float,
    baseline_duration_min: float,
    weather: str = "CLEAR",
    rainfall: float = 0.0,
) -> float:
    """
    Estimate additional traffic delay.

    This is NOT the total route duration.
    """

    baseline_duration_min = max(
        _safe_float(
            baseline_duration_min
        ),
        1.0,
    )

    time_score = _time_pattern_score(
        hour,
        day_of_week,
    )

    route_score = _route_score(
        distance_km,
        baseline_duration_min,
    )

    weather_score = _weather_score(
        weather,
        rainfall,
    )

    congestion_factor = (
        0.05
        + (time_score * 0.45)
        + (route_score * 0.35)
        + (weather_score * 0.20)
    )

    congestion_factor = max(
        0.0,
        min(
            congestion_factor,
            MAX_DELAY_RATIO,
        ),
    )

    delay_minutes = (
        baseline_duration_min
        * congestion_factor
    )

    return round(
        min(
            delay_minutes,
            MAX_ESTIMATED_DELAY_MINUTES,
        ),
        2,
    )


# ============================================================
# HISTORICAL DELAY
# ============================================================

def _normalize_historical_delay(
    historical_delay_minutes: float | None,
) -> float | None:
    """
    None means there is no historical observation.
    """

    if historical_delay_minutes is None:
        return None

    value = max(
        _safe_float(
            historical_delay_minutes
        ),
        0.0,
    )

    return min(
        value,
        MAX_ESTIMATED_DELAY_MINUTES,
    )


def combine_historical_and_pattern_delay(
    pattern_delay_minutes: float,
    historical_delay_minutes: float | None = None,
) -> tuple[float, str]:
    """
    Combine historical and temporal estimates.

    Historical observations are weighted more heavily because
    they represent actual observed route performance.
    """

    pattern = max(
        _safe_float(
            pattern_delay_minutes
        ),
        0.0,
    )

    historical = (
        _normalize_historical_delay(
            historical_delay_minutes
        )
    )

    if historical is None:
        return (
            round(
                min(
                    pattern,
                    MAX_ESTIMATED_DELAY_MINUTES,
                ),
                2,
            ),
            "time_pattern_estimator",
        )

    # Historical observation is authoritative when it exists.
    # We retain 30% of the temporal signal to account for current
    # day/time context.
    combined = (
        historical * 0.70
        + pattern * 0.30
    )

    return (
        round(
            min(
                combined,
                MAX_ESTIMATED_DELAY_MINUTES,
            ),
            2,
        ),
        "historical_plus_time_pattern",
    )


# ============================================================
# OUTPUT VALIDATION
# ============================================================

def validate_traffic_context(
    context: dict,
) -> None:
    """
    Validate the traffic object before it enters ML features.
    """

    traffic_level = context.get(
        "traffic_level"
    )

    if traffic_level not in VALID_TRAFFIC_LEVELS:
        raise ValueError(
            "Invalid traffic_level: "
            f"{traffic_level}"
        )

    traffic_delay_minutes = _safe_float(
        context.get(
            "traffic_delay_minutes"
        )
    )

    if traffic_delay_minutes < 0:
        raise ValueError(
            "traffic_delay_minutes cannot be negative"
        )

    if (
        traffic_delay_minutes
        > MAX_ESTIMATED_DELAY_MINUTES
    ):
        raise ValueError(
            "traffic_delay_minutes exceeds "
            "configured maximum"
        )

    baseline_duration = _safe_float(
        context.get(
            "baseline_duration_min"
        )
    )

    if baseline_duration <= 0:
        raise ValueError(
            "baseline_duration_min must be greater than 0"
        )

    ratio = _safe_float(
        context.get(
            "traffic_delay_ratio"
        )
    )

    if ratio < 0:
        raise ValueError(
            "traffic_delay_ratio cannot be negative"
        )

    if ratio > MAX_DELAY_RATIO:
        raise ValueError(
            "traffic_delay_ratio exceeds "
            "configured maximum"
        )

    source = context.get(
        "traffic_source"
    )

    if source not in VALID_TRAFFIC_SOURCES:
        raise ValueError(
            "Invalid traffic_source: "
            f"{source}"
        )


# ============================================================
# COMPLETE TRAFFIC ESTIMATION
# ============================================================

def estimate_traffic(
    *,
    distance_km: float,
    baseline_duration_min: float,
    order_time: datetime | None = None,
    weather: str = "CLEAR",
    rainfall: float = 0.0,
    historical_delay_minutes: float | None = None,
) -> dict:
    """
    Build complete traffic context.
    """

    if order_time is None:
        order_time = datetime.now()

    hour = int(
        order_time.hour
    )

    day_of_week = int(
        order_time.weekday()
    )

    distance_km = max(
        _safe_float(distance_km),
        0.0,
    )

    baseline_duration_min = max(
        _safe_float(
            baseline_duration_min
        ),
        1.0,
    )

    weather = normalize_weather(
        weather
    )

    rainfall = max(
        _safe_float(rainfall),
        0.0,
    )

    pattern_delay = (
        estimate_time_pattern_delay(
            hour=hour,
            day_of_week=day_of_week,
            distance_km=distance_km,
            baseline_duration_min=(
                baseline_duration_min
            ),
            weather=weather,
            rainfall=rainfall,
        )
    )

    (
        traffic_delay_minutes,
        traffic_source,
    ) = combine_historical_and_pattern_delay(
        pattern_delay_minutes=pattern_delay,
        historical_delay_minutes=(
            historical_delay_minutes
        ),
    )

    # Do the ratio calculation after the delay has been
    # finalized so the returned values can never disagree.
    traffic_delay_ratio = (
        traffic_delay_minutes
        / baseline_duration_min
    )

    traffic_delay_ratio = max(
        0.0,
        min(
            traffic_delay_ratio,
            MAX_DELAY_RATIO,
        ),
    )

    traffic_level = classify_traffic_level(
        traffic_delay_minutes
    )

    context = {
        "traffic_level": traffic_level,

        "traffic_delay_minutes": round(
            traffic_delay_minutes,
            2,
        ),

        "traffic_delay_ratio": round(
            traffic_delay_ratio,
            4,
        ),

        "traffic_source": traffic_source,

        "day_type": classify_day_type(
            day_of_week
        ),

        "time_period": classify_time_period(
            hour
        ),

        "is_weekend": int(
            is_weekend(day_of_week)
        ),

        "is_morning_peak": int(
            is_morning_peak(
                hour,
                day_of_week,
            )
        ),

        "is_evening_peak": int(
            is_evening_peak(
                hour,
                day_of_week,
            )
        ),

        "is_school_peak": int(
            is_school_peak(
                hour,
                day_of_week,
            )
        ),

        "is_office_peak": int(
            is_office_peak(
                hour,
                day_of_week,
            )
        ),

        "baseline_duration_min": round(
            baseline_duration_min,
            2,
        ),

        "estimated_duration_min": round(
            baseline_duration_min
            + traffic_delay_minutes,
            2,
        ),
    }

    validate_traffic_context(
        context
    )

    return context


# ============================================================
# PREDICT.PY ADAPTER
# ============================================================

def build_traffic_context(
    route_info: dict,
    weather_info: dict | None = None,
    order_time: datetime | None = None,
    historical_delay_minutes: float | None = None,
) -> dict:
    """
    Adapter used by predict.py.

    Converts route_info + weather_info into the traffic contract.
    """

    route_info = route_info or {}
    weather_info = weather_info or {}

    distance_km = _safe_float(
        route_info.get(
            "estimated_distance_km",
            0.0,
        )
    )

    baseline_duration_min = _safe_float(
        route_info.get(
            "baseline_duration_min",
            route_info.get(
                "estimated_duration_min",
                0.0,
            ),
        )
    )

    if baseline_duration_min <= 0:
        raise ValueError(
            "Route does not contain a valid baseline duration"
        )

    midpoint_data = (
        weather_info.get(
            "midpoint"
        )
        or {}
    )

    midpoint_weather = (
        midpoint_data.get(
            "weather"
        )
        or weather_info.get(
            "midpoint_weather"
        )
        or "CLEAR"
    )

    rainfall = _safe_float(
        midpoint_data.get(
            "rainfall",
            weather_info.get(
                "maximum_rainfall",
                0.0,
            ),
        )
    )

    return estimate_traffic(
        distance_km=distance_km,
        baseline_duration_min=(
            baseline_duration_min
        ),
        order_time=order_time,
        weather=midpoint_weather,
        rainfall=rainfall,
        historical_delay_minutes=(
            historical_delay_minutes
        ),
    )


# ============================================================
# SELF-TEST
# ============================================================

if __name__ == "__main__":

    test_cases = [
        (
            "Monday morning",
            datetime(
                2026,
                8,
                17,
                8,
                30,
            ),
        ),
        (
            "Friday evening",
            datetime(
                2026,
                8,
                14,
                18,
                30,
            ),
        ),
        (
            "Saturday midday",
            datetime(
                2026,
                8,
                15,
                12,
                30,
            ),
        ),
        (
            "Sunday night",
            datetime(
                2026,
                8,
                16,
                21,
                0,
            ),
        ),
    ]

    for label, test_time in test_cases:

        result = estimate_traffic(
            distance_km=7.5,
            baseline_duration_min=22.0,
            order_time=test_time,
            weather="RAIN",
            rainfall=5.0,
        )

        print(
            f"\n--- {label} ---"
        )

        for key, value in result.items():
            print(
                f"{key}: {value}"
            )