from __future__ import annotations

import math
import re

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)

from app.services.feature_engineering import PAYMENT_MAP

NEPAL_MOBILE_PATTERN = r"^(?:\+977)?(?:97|98)\d{8}$"

MIN_PASSWORD_LENGTH = 6

def validate_nepal_mobile(
    value: str,
) -> str:
    """
    Validate Nepal mobile numbers.

    Accepted examples:

        9841878273
        9741234567
        +9779841878273
    """

    if not isinstance(value, str):
        raise ValueError(
            "Phone number must be a string"
        )

    value = value.strip()

    if not re.fullmatch(
        NEPAL_MOBILE_PATTERN,
        value,
    ):
        raise ValueError(
            "Invalid Nepal mobile number format"
        )

    return value


def validate_payment(
    value: str,
) -> str:
    """
    Normalize payment method to the canonical values
    used by the ML and order layers.

    Examples:

        COD               -> cod
        cash              -> cod
        cash on delivery  -> cod
        prepaid           -> prepaid
        online            -> prepaid
    """

    if not isinstance(value, str):
        raise ValueError(
            "payment_method must be a string"
        )

    key = value.strip().lower()

    if key not in PAYMENT_MAP:
        raise ValueError(
            "payment_method must be one of "
            f"{list(PAYMENT_MAP.keys())}"
        )

    return PAYMENT_MAP[key]


def validate_address(
    value: str,
) -> str:
    """
    Validate a non-empty human-readable address.

    The address is used for display/geocoding.
    Map coordinates become authoritative when a map pin
    is selected.
    """

    if not isinstance(value, str):
        raise ValueError(
            "Address must be a string"
        )

    value = value.strip()

    if not value:
        raise ValueError(
            "Address must not be empty"
        )

    if len(value) < 3:
        raise ValueError(
            "Address is too short"
        )

    return value


def validate_password(
    value: str,
) -> str:
    """
    Basic password validation.

    Authentication/hashing remains a security-layer concern;
    this validator only rejects obviously invalid input.
    """

    if not isinstance(value, str):
        raise ValueError(
            "Password must be a string"
        )

    value = value.strip()

    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least "
            f"{MIN_PASSWORD_LENGTH} characters long"
        )

    return value


def validate_otp(
    value: str,
) -> str:
    """Validate a 4-6 digit OTP."""

    if not isinstance(value, str):
        raise ValueError(
            "OTP must be a string"
        )

    value = value.strip()

    if not re.fullmatch(
        r"\d{4,6}",
        value,
    ):
        raise ValueError(
            "OTP must contain 4 to 6 digits"
        )

    return value


def validate_latitude(
    value: float,
) -> float:
    """Validate global latitude range."""

    value = float(value)

    if not math.isfinite(value):
        raise ValueError(
            "Latitude must be a finite number"
        )

    if not -90 <= value <= 90:
        raise ValueError(
            "Latitude must be between -90 and 90"
        )

    return value


def validate_longitude(
    value: float,
) -> float:
    """Validate global longitude range."""

    value = float(value)

    if not math.isfinite(value):
        raise ValueError(
            "Longitude must be a finite number"
        )

    if not -180 <= value <= 180:
        raise ValueError(
            "Longitude must be between -180 and 180"
        )

    return value

def validate_map_coordinate(
    latitude: float,
    longitude: float,
) -> tuple[float, float]:
    """
    Validate a map coordinate pair before it enters the database.

    This performs basic coordinate sanity checks only.

    Nepal/service-area validation remains the responsibility
    of ors_service.py.
    """

    latitude = validate_latitude(
        latitude
    )

    longitude = validate_longitude(
        longitude
    )

    # (0, 0) is a common placeholder and is not a valid
    # customer delivery location for this system.
    if (
        latitude == 0.0
        and longitude == 0.0
    ):
        raise ValueError(
            "Latitude and longitude cannot both be zero"
        )

    return latitude, longitude

def validate_positive_float(
    value: float,
    field_name: str,
) -> float:
    """
    Validate a strictly positive finite float.
    """

    value = float(value)

    if not math.isfinite(value):
        raise ValueError(
            f"{field_name} must be a finite number"
        )

    if value <= 0:
        raise ValueError(
            f"{field_name} must be greater than 0"
        )

    return value


def validate_non_negative_float(
    value: float,
    field_name: str,
) -> float:
    """
    Validate a finite float >= 0.
    """

    value = float(value)

    if not math.isfinite(value):
        raise ValueError(
            f"{field_name} must be a finite number"
        )

    if value < 0:
        raise ValueError(
            f"{field_name} cannot be negative"
        )

    return value


# ============================================================
# AUTH
# ============================================================

class LoginRequest(BaseModel):
    username: str
    password: str

    @field_validator(
        "username",
        mode="before",
    )
    @classmethod
    def validate_username(
        cls,
        value: str,
    ) -> str:
        if not isinstance(value, str):
            raise ValueError(
                "Username must be a string"
            )

        value = value.strip()

        if not value:
            raise ValueError(
                "Username must not be empty"
            )

        return value

    @field_validator(
        "password",
        mode="before",
    )
    @classmethod
    def validate_login_password(
        cls,
        value: str,
    ) -> str:
        return validate_password(value)


class RegisterRequest(BaseModel):
    phone: str
    password: str

    @field_validator(
        "phone",
        mode="before",
    )
    @classmethod
    def validate_phone(
        cls,
        value: str,
    ) -> str:
        return validate_nepal_mobile(value)

    @field_validator(
        "password",
        mode="before",
    )
    @classmethod
    def validate_register_password(
        cls,
        value: str,
    ) -> str:
        return validate_password(value)


class VerifyOTPRequest(BaseModel):
    phone: str
    otp: str

    @field_validator(
        "phone",
        mode="before",
    )
    @classmethod
    def validate_phone(
        cls,
        value: str,
    ) -> str:
        return validate_nepal_mobile(value)

    @field_validator(
        "otp",
        mode="before",
    )
    @classmethod
    def validate_otp_value(
        cls,
        value: str,
    ) -> str:
        return validate_otp(value)


# ============================================================
# PROFILE & ACCOUNT MANAGEMENT
# ============================================================

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator(
        "current_password",
        "new_password",
        mode="before",
    )
    @classmethod
    def validate_password_field(
        cls,
        value: str,
    ) -> str:
        return validate_password(value)


class CustomerUpdateProfileRequest(BaseModel):
    phone: str | None = None

    @field_validator(
        "phone",
        mode="before",
    )
    @classmethod
    def validate_customer_phone(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        return validate_nepal_mobile(value)


class AdminToggleCustomerStatusRequest(BaseModel):
    is_verified: bool


# ============================================================
# ORDER CREATION
# ============================================================

class OrderCreate(BaseModel):
    """
    Customer order request.

    address:
        Human-readable address.

    latitude/longitude:
        Optional map-pin coordinates.

    Coordinates must either both be present or both be absent.
    Actual Nepal/service-area validation remains in ors_service.py.
    """

    item_id: int = Field(
        ...,
        gt=0,
    )

    quantity: int = Field(
        ...,
        gt=0,
    )

    payment_method: str

    prepaid_amount: float = Field(
        default=0.0,
        ge=0,
        allow_inf_nan=False,
    )

    address: str

    latitude: float | None = Field(
        default=None,
        allow_inf_nan=False,
    )

    longitude: float | None = Field(
        default=None,
        allow_inf_nan=False,
    )

    @field_validator(
        "payment_method",
        mode="before",
    )
    @classmethod
    def validate_payment_method(
        cls,
        value: str,
    ) -> str:
        return validate_payment(value)

    @field_validator(
        "prepaid_amount",
        mode="before",
    )
    @classmethod
    def validate_prepaid(
        cls,
        value: float,
    ) -> float:
        return validate_non_negative_float(
            value,
            "prepaid_amount",
        )

    @field_validator(
        "address",
        mode="before",
    )
    @classmethod
    def validate_order_address(
        cls,
        value: str,
    ) -> str:
        return validate_address(value)

    @field_validator(
        "latitude",
        mode="before",
    )
    @classmethod
    def validate_order_latitude(
        cls,
        value: float | None,
    ) -> float | None:
        if value is None:
            return None

        return validate_latitude(value)

    @field_validator(
        "longitude",
        mode="before",
    )
    @classmethod
    def validate_order_longitude(
        cls,
        value: float | None,
    ) -> float | None:
        if value is None:
            return None

        return validate_longitude(value)

    @model_validator(mode="after")
    def validate_order_consistency(self):
        """
        Validate cross-field order invariants.

        Schema-level validation handles:
            - payment consistency
            - coordinate pairing
            - obviously invalid placeholder coordinates

        Actual Nepal/Kathmandu Valley validation is handled by
        ors_service.py before the order is persisted.
        """

        # --------------------------------------------------------
        # COD + prepaid
        # --------------------------------------------------------

        if (
            self.payment_method == "cod"
            and self.prepaid_amount > 0
        ):
            raise ValueError(
                "COD orders cannot have a prepaid amount"
            )

        # --------------------------------------------------------
        # Coordinate pairing
        # --------------------------------------------------------

        latitude_present = (
            self.latitude is not None
        )

        longitude_present = (
            self.longitude is not None
        )

        if (
            latitude_present
            != longitude_present
        ):
            raise ValueError(
                "latitude and longitude must "
                "either both be provided or both be omitted"
            )

        # --------------------------------------------------------
        # Reject placeholder coordinates
        # --------------------------------------------------------

        if (
            self.latitude == 0.0
            and self.longitude == 0.0
        ):
            raise ValueError(
                "Latitude and longitude cannot both be zero"
            )

        return self

# ============================================================
# ML PREDICTION
# ============================================================

class PredictionInput(BaseModel):
    """
    Request used by the standalone pre-dispatch prediction endpoint.

    Coordinates are optional for development/backward compatibility.

    Recommended production/frontend flow:

        user selects map pin
            ↓
        frontend sends coordinates
            ↓
        backend uses exact coordinates for routing

    The addresses are still retained for display/geocoding.
    """

    pickup_address: str
    delivery_address: str

    order_value: float = Field(
        ...,
        gt=0,
        allow_inf_nan=False,
    )

    payment_method: str

    phone_number: str

    quantity: int = Field(
        default=1,
        gt=0,
    )

    prepaid_amount: float = Field(
        default=0.0,
        ge=0,
        allow_inf_nan=False,
    )

    pickup_latitude: float | None = Field(
        default=None,
        allow_inf_nan=False,
    )

    pickup_longitude: float | None = Field(
        default=None,
        allow_inf_nan=False,
    )

    delivery_latitude: float | None = Field(
        default=None,
        allow_inf_nan=False,
    )

    delivery_longitude: float | None = Field(
        default=None,
        allow_inf_nan=False,
    )

    # --------------------------------------------------------
    # ADDRESS
    # --------------------------------------------------------

    @field_validator(
        "pickup_address",
        "delivery_address",
        mode="before",
    )
    @classmethod
    def validate_prediction_addresses(
        cls,
        value: str,
    ) -> str:
        return validate_address(value)

    # --------------------------------------------------------
    # PAYMENT
    # --------------------------------------------------------

    @field_validator(
        "payment_method",
        mode="before",
    )
    @classmethod
    def validate_prediction_payment(
        cls,
        value: str,
    ) -> str:
        return validate_payment(value)

    @field_validator(
        "prepaid_amount",
        mode="before",
    )
    @classmethod
    def validate_prediction_prepaid(
        cls,
        value: float,
    ) -> float:
        return validate_non_negative_float(
            value,
            "prepaid_amount",
        )

    # --------------------------------------------------------
    # PHONE
    # --------------------------------------------------------

    @field_validator(
        "phone_number",
        mode="before",
    )
    @classmethod
    def validate_prediction_phone(
        cls,
        value: str,
    ) -> str:
        return validate_nepal_mobile(value)

    # --------------------------------------------------------
    # COORDINATES
    # --------------------------------------------------------

    @field_validator(
        "pickup_latitude",
        "delivery_latitude",
        mode="before",
    )
    @classmethod
    def validate_prediction_latitudes(
        cls,
        value: float | None,
    ) -> float | None:
        if value is None:
            return None

        return validate_latitude(value)

    @field_validator(
        "pickup_longitude",
        "delivery_longitude",
        mode="before",
    )
    @classmethod
    def validate_prediction_longitudes(
        cls,
        value: float | None,
    ) -> float | None:
        if value is None:
            return None

        return validate_longitude(value)

    # --------------------------------------------------------
    # CROSS-FIELD VALIDATION
    # --------------------------------------------------------

    @model_validator(mode="after")
    def validate_prediction_consistency(self):
        """
        Validate relationships between fields.
        """

        # --------------------------------------------
        # prepaid <= order_value
        # --------------------------------------------

        if (
            self.prepaid_amount
            > self.order_value
        ):
            raise ValueError(
                "prepaid_amount cannot exceed order_value"
            )

        # --------------------------------------------
        # COD + prepaid amount
        # --------------------------------------------

        if (
            self.payment_method == "cod"
            and self.prepaid_amount > 0
        ):
            raise ValueError(
                "COD orders cannot have a prepaid amount"
            )
        
        pickup_lat_present = (
            self.pickup_latitude is not None
        )

        pickup_lng_present = (
            self.pickup_longitude is not None
        )

        if (
            pickup_lat_present
            != pickup_lng_present
        ):
            raise ValueError(
                "pickup_latitude and pickup_longitude "
                "must either both be provided or both be omitted"
            )

        delivery_lat_present = (
            self.delivery_latitude is not None
        )

        delivery_lng_present = (
            self.delivery_longitude is not None
        )

        if (
            delivery_lat_present
            != delivery_lng_present
        ):
            raise ValueError(
                "delivery_latitude and delivery_longitude "
                "must either both be provided or both be omitted"
            )


        if (
            self.pickup_latitude == 0
            and self.pickup_longitude == 0
        ):
            raise ValueError(
                "Pickup latitude and longitude cannot both be zero"
            )

        if (
            self.delivery_latitude == 0
            and self.delivery_longitude == 0
        ):
            raise ValueError(
                "Delivery latitude and longitude cannot both be zero"
            )

        if (
            self.pickup_latitude is not None
            and self.pickup_longitude is not None
            and self.delivery_latitude is not None
            and self.delivery_longitude is not None
            and self.pickup_latitude
            == self.delivery_latitude
            and self.pickup_longitude
            == self.delivery_longitude
        ):
            raise ValueError(
                "Pickup and delivery locations must be different"
            )

        return self