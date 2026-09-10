"""Billing Pydantic models."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from src.web.models.user import Tier


class UsageResponse(BaseModel):
    tier: Tier
    monthly_scans_used: int
    monthly_scans_limit: Optional[int]  # None = unlimited
    allowed_scan_types: list[str]
    max_lines: Optional[int]


class UpgradeRequest(BaseModel):
    tier: Tier
    success_url: str
    cancel_url: str
    billing_period: str = "monthly"  # "monthly" or "annual"


class UpgradeResponse(BaseModel):
    checkout_url: str
    session_id: str


class PortalResponse(BaseModel):
    portal_url: str


class WebhookResponse(BaseModel):
    received: bool = True
