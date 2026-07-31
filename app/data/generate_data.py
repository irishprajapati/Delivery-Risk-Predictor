import csv
import random
import sys
from pathlib import Path

# Allow imports when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.utils.feature_engineering import build_model_features

OUTPUT_FILE = Path(__file__).resolve().parent / "delivery_data.csv"
NUM_ROWS = 2000

CITIES = [
    ("Kathmandu", "Thamel, Kathmandu"),
    ("Kathmandu", "Baneshwor, Kathmandu"),
    ("Lalitpur", "Patan Durbar Square, Lalitpur"),
    ("Lalitpur", "Jawalakhel, Lalitpur"),
    ("Bhaktapur", "Durbar Square, Bhaktapur"),
    ("Pokhara", "Lakeside, Pokhara"),
    ("Biratnagar", "Main Road, Biratnagar"),
]

PAYMENT_METHODS = ["COD", "prepaid", "cod", "online"]
WEATHER_CONDITIONS = ["normal", "rainy", "clear", "foggy", "extreme"]


def random_address() -> str:
    city_label, base = random.choice(CITIES)
    if random.random() < 0.3:
        return base
    return f"Ward {random.randint(1, 32)}, {base}"


def random_phone() -> str:
    return f"98{random.randint(10000000, 99999999)}"


def calculate_failure(features: dict) -> int:
    risk_score = 0

    if features["payment_method"] == "COD":
        risk_score += 2
    if features["address_clarity"] == "low":
        risk_score += 2
    if features["area_density"] == "high":
        risk_score += 1
    if features["order_value_category"] == "high":
        risk_score += 1
    if features["weather_condition"] == "extreme":
        risk_score += 2
    if features["weather_condition"] == "rain":
        risk_score += 1

    probability = min(0.1 + risk_score * 0.1, 0.9)
    return 1 if random.random() < probability else 0


def generate_row() -> dict:
    delivery_address = random_address()
    order_value = round(random.uniform(100, 5000), 2)

    raw = {
        "pickup_address": "Central Warehouse, Kathmandu",
        "delivery_address": delivery_address,
        "order_value": order_value,
        "payment_method": random.choice(PAYMENT_METHODS),
        "weather_condition": random.choice(WEATHER_CONDITIONS),
        "phone_number": random_phone(),
    }

    features = build_model_features(raw)
    raw["failed"] = calculate_failure(features)
    return raw


def main():
    fieldnames = [
        "pickup_address",
        "delivery_address",
        "order_value",
        "payment_method",
        "weather_condition",
        "phone_number",
        "failed",
    ]

    with open(OUTPUT_FILE, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for _ in range(NUM_ROWS):
            writer.writerow(generate_row())

    print(f"Generated {NUM_ROWS} rows -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
