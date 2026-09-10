"""JWT authentication middleware and dependency."""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.web.database import get_db
from src.web.models.user import Tier, UserProfile

_bearer = HTTPBearer(auto_error=False)


async def _fetch_user_profile(user_id: str) -> UserProfile:
    """Load user profile from Supabase profiles table."""
    db = get_db()
    result = db.table("profiles").select("*").eq("id", user_id).maybe_single().execute()
    if result.data:
        return UserProfile(
            id=result.data["id"],
            email=result.data.get("email"),
            tier=Tier(result.data.get("tier", "free")),
            stripe_customer_id=result.data.get("stripe_customer_id"),
            monthly_scan_count=result.data.get("monthly_scan_count", 0),
            billing_period_start=result.data.get("billing_period_start"),
        )
    return UserProfile(id=user_id)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[UserProfile]:
    """
    Returns UserProfile if a valid JWT is present, None for anonymous.
    Raises 401 only if a malformed/invalid token was supplied.
    """
    if credentials is None:
        return None

    token = credentials.credentials
    db = get_db()
    try:
        resp = db.auth.get_user(token)
        if resp and resp.user:
            return await _fetch_user_profile(resp.user.id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return None


async def require_auth(
    user: Optional[UserProfile] = Depends(get_current_user),
) -> UserProfile:
    """Dependency that requires authenticated user."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user
