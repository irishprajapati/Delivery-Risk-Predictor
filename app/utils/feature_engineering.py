"""
Shared feature engineering for training and inference.
Keep all transformation logic here to ensure consistency.
"""

PAYMENT_MAP = {
    "cod": "COD",
    "cash": "COD",
    "cash on delivery": "COD",
    "prepaid": "prepaid",
    "online": "prepaid",
}

WEATHER_MAP = {
    "clear": "normal",
    "normal": "normal",
    "rainy": "rain",
    "rain": "rain",
    "foggy": "extreme",
    "extreme": "extreme",
}

MODEL_FEATURE_COLUMNS = [
    "address_clarity",
    "area_density",
    "order_value_category",
    "weather_condition",
    "payment_method",
]


def normalize_payment(value: str) -> str:
    key = value.strip().lower()
    if key not in PAYMENT_MAP:
        raise ValueError(
            f"payment_method must be one of {list(PAYMENT_MAP.keys())}"
        )
    return PAYMENT_MAP[key]


def normalize_weather(value: str) -> str:
    key = value.strip().lower()
    if key not in WEATHER_MAP:
        raise ValueError(
            f"weather_condition must be one of {list(WEATHER_MAP.keys())}"
        )
    return WEATHER_MAP[key]


def compute_address_length(delivery_address: str) -> int:
    return len(delivery_address.strip())


def compute_address_clarity(delivery_address: str) -> str:
    """Short addresses are harder to locate."""
    length = compute_address_length(delivery_address)
    return "low" if length < 20 else "high"


def compute_area_density(delivery_address: str) -> str:
    """Infer density from city name in the delivery address."""
    address = delivery_address.strip().lower()
    if "kathmandu" in address:
        return "high"
    if "lalitpur" in address or "bhaktapur" in address:
        return "medium"
    return "low"


def compute_order_value_category(order_value: float) -> str:
    if order_value < 500:
        return "low"
    if order_value <= 2000:
        return "medium"
    return "high"


def resolve_weather_condition(raw: dict) -> str:
    """
    Weather is derived from live route sampling (see weather_service).
    Falls back to explicit weather_condition only for offline/training paths.
    """
    weather_info = raw.get("weather_info") or {}
    model_weather = weather_info.get("model_weather_condition")
    if model_weather in {"normal", "rain", "extreme"}:
        return model_weather

    if "weather_condition" in raw:
        return normalize_weather(raw["weather_condition"])

    raise ValueError("weather_info.model_weather_condition is required for inference")


def build_model_features(raw: dict) -> dict:
    """
    Transform raw user input into model-ready features.
    Only derived/processed fields are returned — no raw inputs.
    """
    delivery_address = raw["delivery_address"].strip()

    return {
        "address_clarity": compute_address_clarity(delivery_address),
        "area_density": compute_area_density(delivery_address),
        "order_value_category": compute_order_value_category(float(raw["order_value"])),
        "weather_condition": resolve_weather_condition(raw),
        "payment_method": normalize_payment(raw["payment_method"]),
    }


def build_model_features_batch(rows: list[dict]) -> list[dict]:
    return [build_model_features(row) for row in rows]


def process_input(data: dict) -> dict:
    """Transform raw API/training input into model-ready features."""
    return build_model_features(data)
