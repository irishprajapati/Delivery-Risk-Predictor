from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
import pandas as pd

N_ROWS = 75_000
SEED = 42
OUTPUT_PATH = Path("app/data/delivery_data.csv")
TARGET_COLUMN = "delivery_failure"

random.seed(SEED)
np.random.seed(SEED)

MODEL_FEATURES = [
    "total_orders", "failed_deliveries", "failure_rate",
    "unreachable_count", "unreachable_rate",
    "quantity", "total_price", "payment_method", "prepaid_amount",
    "prepaid_ratio", "hour_of_day", "day_of_week", "day_type",
    "time_period", "is_weekend", "is_peak_hour", "is_morning_peak",
    "is_evening_peak", "is_school_peak", "is_office_peak",
    "address_quality", "distance_km", "estimated_duration",
    "location_success_rate", "is_long_distance", "is_long_duration",
    "weather", "rainfall", "temperature", "traffic_level",
    "traffic_delay_minutes", "traffic_delay_ratio", "is_raining",
    "is_severe_weather", "heavy_rain", "extreme_temperature",
    "high_traffic", "hub_delay_minutes", "route_status",
    "vehicle_status", "hub_delay",
]


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def classify_day_type(day_of_week: int) -> str:
    if day_of_week == 5:
        return "SATURDAY"
    if day_of_week == 6:
        return "SUNDAY"
    return "WEEKDAY"


def classify_time_period(hour: int) -> str:
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


def generate_customer_history() -> dict:
    total_orders = int(clamp(int(np.random.geometric(1 / 22)), 1, 100))
    reliability = np.random.beta(8, 2)
    failure_probability = clamp(1.0 - reliability, 0.01, 0.55)
    failed_deliveries = int(np.random.binomial(total_orders, failure_probability))
    unreachable_probability = clamp(
        0.015 + (failed_deliveries / max(total_orders, 1)) * 0.45,
        0.01,
        0.45,
    )
    unreachable_count = int(np.random.binomial(total_orders, unreachable_probability))
    return {
        "total_orders": total_orders,
        "failed_deliveries": failed_deliveries,
        "failure_rate": round(failed_deliveries / total_orders, 4),
        "unreachable_count": unreachable_count,
        "unreachable_rate": round(unreachable_count / total_orders, 4),
    }


def generate_order() -> dict:
    quantity = int(random.choices(
        [1, 2, 3, 4, 5, 6, 8, 10, 15, 20],
        weights=[25, 23, 16, 12, 9, 5, 3.5, 2.5, 1.5, 0.5],
        k=1,
    )[0])
    total_price = clamp(float(np.random.lognormal(7.3, 0.75)), 100, 100_000)
    is_cod = bool(np.random.choice([True, False], p=[0.58, 0.42]))
    payment_method = "cod" if is_cod else "prepaid"
    prepaid_amount = 0.0 if is_cod else total_price * float(np.random.uniform(0.25, 1.0))
    prepaid_ratio = prepaid_amount / total_price if total_price > 0 else 0.0

    hour_of_day = int(np.random.randint(0, 24))
    day_of_week = int(np.random.randint(0, 7))
    day_type = classify_day_type(day_of_week)
    time_period = classify_time_period(hour_of_day)
    is_weekend = int(day_of_week >= 5)
    is_morning_peak = int(8 <= hour_of_day <= 10 and not is_weekend)
    is_evening_peak = int(17 <= hour_of_day <= 19 and not is_weekend)
    is_school_peak = int((7 <= hour_of_day <= 9 or 15 <= hour_of_day <= 17) and not is_weekend)
    is_office_peak = int((8 <= hour_of_day <= 10 or 16 <= hour_of_day <= 19) and not is_weekend)
    is_peak_hour = int(is_morning_peak or is_evening_peak)

    return {
        "quantity": quantity,
        "total_price": round(total_price, 2),
        "payment_method": payment_method,
        "prepaid_amount": round(prepaid_amount, 2),
        "prepaid_ratio": round(prepaid_ratio, 4),
        "hour_of_day": hour_of_day,
        "day_of_week": day_of_week,
        "day_type": day_type,
        "time_period": time_period,
        "is_weekend": is_weekend,
        "is_peak_hour": is_peak_hour,
        "is_morning_peak": is_morning_peak,
        "is_evening_peak": is_evening_peak,
        "is_school_peak": is_school_peak,
        "is_office_peak": is_office_peak,
    }


def generate_location() -> dict:
    latitude = np.random.uniform(27.62, 27.78)
    longitude = np.random.uniform(85.25, 85.43)
    hub_latitude, hub_longitude = 27.7172, 85.3240
    delta_lat = math.radians(latitude - hub_latitude)
    delta_lng = math.radians(longitude - hub_longitude)
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(math.radians(hub_latitude))
        * math.cos(math.radians(latitude))
        * math.sin(delta_lng / 2) ** 2
    )
    straight_distance = 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_km = max(0.8, straight_distance * float(np.random.uniform(1.20, 1.65)))
    base_speed = float(np.random.uniform(18, 30))
    estimated_duration = distance_km / base_speed * 60 + float(np.random.uniform(5, 18))
    location_success_rate = clamp(
        0.98 - min(distance_km / 80, 0.15) + float(np.random.normal(0, 0.025)),
        0.55,
        0.99,
    )
    address_quality = clamp(float(np.random.beta(8, 2)), 0.20, 1.0)
    return {
        "address_quality": round(address_quality, 4),
        "distance_km": round(distance_km, 2),
        "estimated_duration": round(estimated_duration, 1),
        "location_success_rate": round(location_success_rate, 4),
        "is_long_distance": int(distance_km > 15),
        "is_long_duration": int(estimated_duration > 60),
    }


def generate_environment(order: dict, location: dict) -> dict:
    weather = str(np.random.choice(
        ["CLEAR", "CLOUDY", "FOG", "RAIN", "STORM"],
        p=[0.42, 0.20, 0.10, 0.23, 0.05],
    ))
    if weather == "CLEAR":
        rainfall = 0.0
    elif weather in {"CLOUDY", "FOG"}:
        rainfall = float(np.random.uniform(0, 2))
    elif weather == "RAIN":
        rainfall = float(np.random.gamma(2.0, 3.5))
    else:
        rainfall = float(np.random.gamma(4.0, 5.0))

    temperature = clamp(float(np.random.normal(23, 5)), 5, 37)
    is_raining = int(weather in {"RAIN", "STORM"} or rainfall > 0)
    is_severe_weather = int(weather in {"STORM", "FOG"})
    heavy_rain = int(rainfall >= 10)
    extreme_temperature = int(temperature >= 35 or temperature <= 5)

    # Traffic is synthetic, but correlated with operationally meaningful
    # time/day/weather/route factors instead of being independent noise.
    traffic_score = 0.0
    if order["day_type"] == "WEEKDAY":
        traffic_score += 0.30
    elif order["day_type"] == "SATURDAY":
        traffic_score += 0.08
    else:
        traffic_score -= 0.08

    if order["is_morning_peak"]:
        traffic_score += 0.40
    if order["is_evening_peak"]:
        traffic_score += 0.45
    if order["is_school_peak"]:
        traffic_score += 0.20
    if order["is_office_peak"]:
        traffic_score += 0.10

    traffic_score += min(location["distance_km"] / 30.0, 0.30)

    if weather == "RAIN":
        traffic_score += 0.20
    elif weather == "STORM":
        traffic_score += 0.35
    elif weather == "FOG":
        traffic_score += 0.12
    if rainfall >= 10:
        traffic_score += 0.15

    traffic_score += float(np.random.normal(0, 0.12))
    traffic_score = clamp(traffic_score, 0.0, 1.5)

    if traffic_score < 0.35:
        traffic_level = "LOW"
    elif traffic_score < 0.70:
        traffic_level = "MEDIUM"
    elif traffic_score < 1.05:
        traffic_level = "HIGH"
    else:
        traffic_level = "SEVERE"

    baseline_duration = location["estimated_duration"]
    delay_ranges = {
        "LOW": (0.00, 0.10),
        "MEDIUM": (0.08, 0.30),
        "HIGH": (0.25, 0.65),
        "SEVERE": (0.55, 1.20),
    }
    low, high = delay_ranges[traffic_level]
    delay_factor = float(np.random.uniform(low, high))
    traffic_delay_minutes = max(0.0, baseline_duration * delay_factor)
    traffic_delay_ratio = traffic_delay_minutes / baseline_duration if baseline_duration > 0 else 0.0
    high_traffic = int(traffic_level in {"HIGH", "SEVERE"} or traffic_delay_minutes >= 15)

    return {
        "weather": weather,
        "rainfall": round(rainfall, 2),
        "temperature": round(temperature, 2),
        "traffic_level": traffic_level,
        "traffic_delay_minutes": round(traffic_delay_minutes, 2),
        "traffic_delay_ratio": round(traffic_delay_ratio, 4),
        "is_raining": is_raining,
        "is_severe_weather": is_severe_weather,
        "heavy_rain": heavy_rain,
        "extreme_temperature": extreme_temperature,
        "high_traffic": high_traffic,
    }


def generate_operations() -> dict:
    hub_delay_minutes = clamp(float(np.random.gamma(1.8, 7)), 0, 90)
    route_status = str(np.random.choice(
        ["NORMAL", "DELAYED", "BLOCKED"],
        p=[0.78, 0.19, 0.03],
    ))
    vehicle_status = str(np.random.choice(
        ["AVAILABLE", "MAINTENANCE", "BREAKDOWN"],
        p=[0.91, 0.075, 0.015],
    ))
    return {
        "hub_delay_minutes": round(hub_delay_minutes, 2),
        "route_status": route_status,
        "vehicle_status": vehicle_status,
        "hub_delay": int(hub_delay_minutes >= 30),
    }


def generate_failure(customer: dict, order: dict, location: dict, environment: dict, operations: dict) -> int:
    logit = -3.20

    # Customer history
    logit += customer["failure_rate"] * 3.2
    logit += customer["unreachable_rate"] * 2.0
    if customer["total_orders"] == 1:
        logit += 0.15

    # Order/payment
    logit += max(order["quantity"] - 5, 0) * 0.025
    if order["total_price"] > 10_000:
        logit += 0.20
    if order["total_price"] > 25_000:
        logit += 0.25
    if order["payment_method"] == "cod":
        logit += 0.18
    if order["prepaid_ratio"] >= 0.75:
        logit -= 0.15
    if (
        customer["total_orders"] == 1
        and order["payment_method"] == "cod"
        and order["total_price"] > 30_000
    ):
        logit += 0.40

    # Time context
    if order["is_morning_peak"]:
        logit += 0.10
    if order["is_evening_peak"]:
        logit += 0.14
    if order["is_school_peak"]:
        logit += 0.05
    if order["is_office_peak"]:
        logit += 0.06

    # Location
    logit += (1.0 - location["address_quality"]) * 1.4
    logit += max(location["distance_km"] - 8, 0) * 0.035
    logit += max(location["estimated_duration"] - 40, 0) * 0.012
    logit += (1.0 - location["location_success_rate"]) * 2.0

    # Weather
    if environment["weather"] == "RAIN":
        logit += 0.30
    elif environment["weather"] == "STORM":
        logit += 0.65
    elif environment["weather"] == "FOG":
        logit += 0.22
    logit += min(environment["rainfall"], 30) * 0.018
    if environment["heavy_rain"]:
        logit += 0.25
    if environment["extreme_temperature"]:
        logit += 0.20
    if environment["is_severe_weather"]:
        logit += 0.15

    # Traffic
    traffic_weights = {
        "LOW": 0.00,
        "MEDIUM": 0.10,
        "HIGH": 0.22,
        "SEVERE": 0.40,
    }
    logit += traffic_weights.get(environment["traffic_level"], 0.0)
    logit += min(environment["traffic_delay_ratio"], 1.0) * 0.30
    if environment["high_traffic"]:
        logit += 0.10

    # Pre-dispatch operations
    logit += min(operations["hub_delay_minutes"], 60) * 0.012
    if operations["route_status"] == "DELAYED":
        logit += 0.35
    elif operations["route_status"] == "BLOCKED":
        logit += 0.90
    if operations["vehicle_status"] == "MAINTENANCE":
        logit += 0.20
    elif operations["vehicle_status"] == "BREAKDOWN":
        logit += 0.65
    if operations["hub_delay"]:
        logit += 0.25

    logit += float(np.random.normal(0, 0.35))
    return int(np.random.random() < sigmoid(logit))


def generate_row() -> dict:
    customer = generate_customer_history()
    order = generate_order()
    location = generate_location()
    environment = generate_environment(order, location)
    operations = generate_operations()
    delivery_failure = generate_failure(customer, order, location, environment, operations)

    row = {}
    row.update(customer)
    row.update(order)
    row.update(location)
    row.update(environment)
    row.update(operations)
    row[TARGET_COLUMN] = delivery_failure
    return row


def main() -> None:
    print(f"[INFO] Generating {N_ROWS:,} synthetic pre-dispatch delivery records...")
    rows = [generate_row() for _ in range(N_ROWS)]
    df = pd.DataFrame(rows)
    df = df[MODEL_FEATURES + [TARGET_COLUMN]]

    expected_columns = MODEL_FEATURES + [TARGET_COLUMN]
    if df.columns.tolist() != expected_columns:
        raise ValueError(
            "Generated CSV does not match the model feature contract.\n"
            f"Expected: {expected_columns}\n"
            f"Actual:   {df.columns.tolist()}"
        )

    if df.isnull().any().any():
        missing = df.isnull().sum()
        missing = missing[missing > 0]
        raise ValueError(f"Generated dataset contains missing values:\n{missing}")

    if set(df["payment_method"].unique()) - {"cod", "prepaid"}:
        raise ValueError("Unexpected payment_method value found.")

    if set(df["traffic_level"].unique()) - {"LOW", "MEDIUM", "HIGH", "SEVERE"}:
        raise ValueError("Unexpected traffic_level value found.")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"[INFO] Dataset saved to: {OUTPUT_PATH}")
    print(f"[INFO] Shape: {df.shape}")
    print("[INFO] Target distribution:")
    print(df[TARGET_COLUMN].value_counts())
    print("[INFO] Target proportions:")
    print(df[TARGET_COLUMN].value_counts(normalize=True).round(4))
    print("[INFO] Traffic distribution:")
    print(df["traffic_level"].value_counts())
    print("[INFO] Day type distribution:")
    print(df["day_type"].value_counts())
    print("[INFO] Time period distribution:")
    print(df["time_period"].value_counts())
    print("[INFO] Dataset columns:")
    print(df.columns.tolist())
    print("[INFO] First 5 rows:")
    print(df.head())


if __name__ == "__main__":
    main()