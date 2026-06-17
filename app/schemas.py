from pydantic import BaseModel, field_validator, Field
from typing import Optional
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
    def strip_and_lower(cls, v):
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("delivery_time")
    @classmethod
    def fix_time(cls, v):
        if v not in TIME_MAP:
            raise ValueError("Invalid delivery_time")
        return TIME_MAP[v]


    @field_validator("payment_method")
    @classmethod
    def fix_payment(cls, v):
        if v not in PAYMENT_MAP:
            raise ValueError("Invalid payment_method")
        return PAYMENT_MAP[v]

    @field_validator("address_clarity")
    @classmethod
    def fix_clarity(cls, v):
        if v not in CLARITY_MAP:
            raise ValueError("Invalid address_clarity")
        return CLARITY_MAP[v]

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v):
        pattern = r"^(\+977)?(98\d{8}|97\d{8}|01\d{7})$"
        if not re.match(pattern, v):
            raise ValueError("Invalid Nepal phone number")
        return v