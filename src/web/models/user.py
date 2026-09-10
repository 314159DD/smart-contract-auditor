"""User Pydantic models."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr


class Tier(str, Enum):
    free = "free"
    pro = "pro"
    enterprise = "enterprise"


TIER_LIMITS = {
    Tier.free: {
        "monthly_scans": 5,
        "allowed_types": ["quick"],
        "max_lines": 500,
        "concurrent": 1,
    },
    Tier.pro: {
        "monthly_scans": 50,
        "allowed_types": ["quick", "standard"],
        "max_lines": 5000,
        "concurrent": 5,
    },
    Tier.enterprise: {
        "monthly_scans": None,  # unlimited
        "allowed_types": ["quick", "standard", "deep"],
        "max_lines": None,
        "concurrent": None,
    },
}

ANON_DAILY_LIMIT = 3


class UserProfile(BaseModel):
    id: str
    email: Optional[str] = None
    tier: Tier = Tier.free
    stripe_customer_id: Optional[str] = None
    monthly_scan_count: int = 0
    billing_period_start: Optional[str] = None


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: Optional[str] = None
    tier: Tier = Tier.free
