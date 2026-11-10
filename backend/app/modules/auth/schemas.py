import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FarmerRegistration(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    display_name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=7, max_length=20)
    pin: str = Field(min_length=4, max_length=8)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not re.fullmatch(r"\+?[0-9]{7,19}", value):
            raise ValueError("Phone must contain 7 to 19 digits and an optional leading +.")
        return value

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("PIN must contain digits only.")
        return value


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=4, max_length=254)
    secret: str = Field(min_length=4, max_length=256)

    @model_validator(mode="after")
    def validate_identifier(self) -> "LoginRequest":
        if "@" not in self.identifier and not re.fullmatch(r"\+?[0-9]{7,19}", self.identifier):
            raise ValueError("Sign in with a valid email address or phone number.")
        return self


class UserResponse(BaseModel):
    id: str
    role: Literal["farmer", "auditor", "buyer", "bank_viewer", "admin"]
    display_name: str
    phone: str | None = None
    email: str | None = None
    kyc_verified: bool


class LoginResponse(BaseModel):
    user: UserResponse
    expires_in_seconds: int


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    display_name: str = Field(min_length=1, max_length=120)
