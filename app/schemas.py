from pydantic import BaseModel, Field, field_validator
import re

from app.utils.feature_engineering import PAYMENT_MAP

class LoginRequest(BaseModel):
    username: str
    password: str
class RegisterRequest(BaseModel):
    phone:str
    password:str
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        pattern = r"^(\+977)?(98\d{8}|97\d{8}|01\d{7})$"
        if not re.match(pattern, v):
            raise ValueError("Invalid Nepal phone number format")
        return v
class VerifyOTPRequest(BaseModel):
    phone:str
    otp:str

class OrderCreate(BaseModel):
    item_id: int
    quantity: int = Field(..., gt=0)
    payment_method: str
    prepaid_amount: float = Field(default=0.0, ge=0)
    address: str

    @field_validator("payment_method", mode="before")
    @classmethod
    def validate_payment_method(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("payment_method must be a string")

        v = v.strip().lower()

        if v not in PAYMENT_MAP:
            raise ValueError(
                f"payment_method must be one of {list(PAYMENT_MAP.keys())}"
            )

        return v
    @field_validator("address", mode="before")
    @classmethod
    def validate_address(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Address must be a string")

        v = v.strip()

        if not v:
            raise ValueError("Address must not be empty")

        return v

class PredictionInput(BaseModel):
    pickup_address: str
    delivery_address: str
    order_value: float = Field(..., gt=0)
    payment_method: str
    phone_number: str

    @field_validator(
        "pickup_address",
        "delivery_address",
        "payment_method",
        "phone_number",
        mode="before"
    )
    @classmethod
    def strip_strings(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Value must be a string")

        return v.strip()

    @field_validator("pickup_address", "delivery_address")
    @classmethod
    def validate_addresses(cls, v: str) -> str:
        if not v:
            raise ValueError("Address must not be empty")

        return v

    @field_validator("payment_method")
    @classmethod
    def validate_payment(cls, v: str) -> str:
        key = v.lower()

        if key not in PAYMENT_MAP:
            raise ValueError(
                f"payment_method must be one of {list(PAYMENT_MAP.keys())}"
            )

        return key

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        pattern = r"^(?:\+977)?(?:98|97)\d{8}$"

        if not re.fullmatch(pattern, v):
            raise ValueError(
                "Invalid Nepal mobile number format"
            )

        return v