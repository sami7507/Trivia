"""backend/schemas/auth.py — request/response models for sign-in."""
import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

PHONE_RE = re.compile(r"^\+[1-9]\d{7,14}$")


def normalize_phone(raw: str) -> str:
    return re.sub(r"[\s\-().]", "", raw or "")


class PhoneRequest(BaseModel):
    phone: str = Field(..., description="Mobile number in international format, e.g. +919876543210")

    @field_validator("phone")
    @classmethod
    def _valid(cls, v: str) -> str:
        v = normalize_phone(v)
        if not PHONE_RE.match(v):
            raise ValueError("Enter your number with country code, e.g. +919876543210")
        return v


class OtpVerify(PhoneRequest):
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class ExchangeRequest(BaseModel):
    code: str = Field(..., min_length=10, max_length=200)


class OtpSent(BaseModel):
    sent: bool = True
    delivery: str = Field(..., description="'sms' or 'console' (demo mode)")
    expires_in: int
    dev_otp: Optional[str] = Field(None, description="Only present when OTP_DEV_ECHO=true")


class UserOut(BaseModel):
    id: int
    name: str
    provider: str
    email: Optional[str] = None
    phone_masked: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class ProvidersResponse(BaseModel):
    google: bool
    mobile: bool
    guest: bool
    sms_delivery: str
    auth_required: bool
