"""backend/schemas/feedback.py"""
import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class FeedbackIn(BaseModel):
    message: str = Field(..., min_length=3, max_length=2000, description="Your feedback")
    rating: Optional[int] = Field(None, ge=1, le=5, description="1 (poor) – 5 (great)")
    contact: Optional[str] = Field(None, max_length=200, description="Optional email/phone for a reply")

    model_config = {"extra": "forbid"}

    @field_validator("message", "contact")
    @classmethod
    def _clean(cls, v):
        if v is None:
            return v
        v = _CTRL.sub("", v).strip()
        return v or None

    @field_validator("message")
    @classmethod
    def _not_blank(cls, v):
        if not v or len(v) < 3:
            raise ValueError("Please write at least a few words.")
        return v


class FeedbackReceipt(BaseModel):
    id: int
    received: bool = True


class FeedbackRecord(BaseModel):
    id: int
    created_at: str
    user_id: Optional[int] = None
    rating: Optional[int] = None
    message: str
    contact: Optional[str] = None
