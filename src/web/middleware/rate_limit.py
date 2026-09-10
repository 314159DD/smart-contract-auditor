"""Per-user and per-IP rate limiting."""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import Optional

from fastapi import HTTPException, Request, status

from src.web.models.user import ANON_DAILY_LIMIT, TIER_LIMITS, Tier, UserProfile

# In-memory stores (swap for Redis in production)
_ip_store: dict[str, dict] = defaultdict(lambda: {"count": 0, "reset_at": 0.0})
_concurrent: dict[str, int] = defaultdict(int)
_lock = Lock()


def _day_reset() -> float:
    """Seconds until midnight UTC today."""
    now = time.time()
    return now - (now % 86400) + 86400


def check_anonymous_rate_limit(ip: str) -> None:
    """Allow 3 quick scans per day per IP."""
    with _lock:
        entry = _ip_store[ip]
        now = time.time()
        if now > entry["reset_at"]:
            entry["count"] = 0
            entry["reset_at"] = _day_reset()
        if entry["count"] >= ANON_DAILY_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Anonymous limit reached: {ANON_DAILY_LIMIT} quick scans/day. Sign up for more.",
            )
        entry["count"] += 1


def check_tier_scan_type(user: UserProfile, scan_type: str) -> None:
    """Raise 403 if user's tier doesn't permit this scan type."""
    limits = TIER_LIMITS[user.tier]
    if scan_type not in limits["allowed_types"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{scan_type} scans require a higher tier. Upgrade to unlock.",
        )


def check_monthly_quota(user: UserProfile) -> None:
    """Raise 402 if user has exhausted their monthly scan quota."""
    limits = TIER_LIMITS[user.tier]
    monthly_limit = limits["monthly_scans"]
    if monthly_limit is not None and user.monthly_scan_count >= monthly_limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Monthly scan limit reached ({monthly_limit}). "
                "Upgrade your plan at /pricing to continue."
            ),
        )


def check_line_limit(user: UserProfile, source: str) -> None:
    """Raise 413 if source exceeds tier's line limit."""
    limits = TIER_LIMITS[user.tier]
    max_lines = limits["max_lines"]
    if max_lines is not None:
        line_count = source.count("\n") + 1
        if line_count > max_lines:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Contract has {line_count} lines; your tier allows up to {max_lines}. Upgrade to scan larger contracts.",
            )


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
