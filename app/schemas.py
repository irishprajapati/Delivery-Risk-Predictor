from pydantic import BaseModel, Field, field_validator
import re

from app.utils.feature_engineering import PAYMENT_MAP


class LoginRequest(BaseModel):
    username: str
    password: str


class PredictionInput(BaseModel):
    pickup_address: str = Field(..., min_length=1)
    delivery_address: str = Field(..., min_length=1)
    order_value: float = Field(..., gt=0)
    payment_method: str
    phone_number: str

    @field_validator("pickup_address", "delivery_address", "payment_method", "phone_number")
    @classmethod
    def strip_strings(cls, v: str) -> str:
        return v.strip()

    @field_validator("pickup_address", "delivery_address")
    @classmethod
    def addresses_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("Address must not be empty")
        return v

    @field_validator("payment_method")
    @classmethod
    def validate_payment(cls, v: str) -> str:
        key = v.strip().lower()
        if key not in PAYMENT_MAP:
            raise ValueError(
                f"payment_method must be one of {list(PAYMENT_MAP.keys())}"
            )
        return v

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        pattern = r"^(\+977)?(98\d{8}|97\d{8}|01\d{7})$"
        if not re.match(pattern, v):
            raise ValueError("Invalid Nepal phone number format")
        return v
