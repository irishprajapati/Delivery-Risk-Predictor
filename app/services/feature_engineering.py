from datetime import datetime


def build_features(route_data: dict) -> dict:
    now = datetime.now()

    hour = now.hour
    day = now.weekday()

    is_peak = 1 if (8 <= hour <= 10 or 17 <= hour <= 19) else 0

    return {
        "distance_km": route_data["distance_km"],
        "hour_of_day": hour,
        "day_of_week": day,
        "is_peak_hour": is_peak
    }