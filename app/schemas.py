from pydantic import BaseModel, field_validator, Field
import re

TIME_MAP = {
    "morning": "morning",
    "am": "morning",
    "afternoon": "afternoon",
    "noon": "afternoon",
    "evening": "evening",
    "pm": "evening"
}

PAYMENT_MAP = {
    "cod": "COD",
    "cash": "COD",
    "cash on delivery": "COD",
    "prepaid": "prepaid",
    "online": "prepaid"
}

CLARITY_MAP = {
    "clear": "clear",
    "unclear": "unclear",
    "bad": "unclear"
}
class PredictionInput(BaseModel):

    delivery_time: str
    address_clarity: str
    payment_method: str

    order_value: str
    area_density: str
    accessibility: str
    weather_condition: str
    traffic_level: str

    address_length: int = Field(ge=1, le=200)
    phone_number: str

    @field_validator("*", mode="before")
    @classmethod
    def normalize_strings(cls, v):
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("delivery_time")
    @classmethod
    def validate_time(cls, v):
        if v not in TIME_MAP:
            raise ValueError("delivery_time must be morning/afternoon/evening or valid synonym")
        return TIME_MAP[v]

    @field_validator("payment_method")
    @classmethod
    def validate_payment(cls, v):
        if v not in PAYMENT_MAP:
            raise ValueError("payment_method must be COD or prepaid")
        return PAYMENT_MAP[v]

    @field_validator("address_clarity")
    @classmethod
    def validate_clarity(cls, v):
        if v not in CLARITY_MAP:
            raise ValueError("address_clarity must be clear or unclear")
        return CLARITY_MAP[v]

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v):
        pattern = r"^(\+977)?(98\d{8}|97\d{8}|01\d{7})$"
        if not re.match(pattern, v):
            raise ValueError("Invalid Nepal phone number format")
        return v