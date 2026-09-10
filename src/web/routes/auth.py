"""
Auth routes:
  POST /api/auth/register   — create account with email+password
  POST /api/auth/login      — sign in, return JWT
  POST /api/auth/logout     — invalidate session
  GET  /api/auth/me         — return current user profile
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from src.web.database import get_db, get_admin_db
from src.web.middleware.auth import get_current_user, require_auth
from src.web.models.user import AuthResponse, LoginRequest, RegisterRequest, Tier, UserProfile

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest) -> AuthResponse:
    """Register a new user with email + password. Auto-confirms email via admin API."""
    admin = get_admin_db()
    db = get_db()

    # Use admin API to create user with email pre-confirmed — no confirmation email needed
    try:
        resp = admin.auth.admin.create_user({
            "email": req.email,
            "password": req.password,
            "email_confirm": True,
        })
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {exc}",
        )

    if not resp.user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed: no user returned",
        )

    user = resp.user

    # Upsert profile row
    try:
        admin.table("profiles").upsert({
            "id": user.id,
            "email": user.email,
            "tier": Tier.free,
            "monthly_scan_count": 0,
        }).execute()
    except Exception:
        pass

    # Sign in immediately to get a session token
    try:
        sign_in = db.auth.sign_in_with_password({"email": req.email, "password": req.password})
        session = sign_in.session
    except Exception:
        session = None

    if not session:
        raise HTTPException(
            status_code=status.HTTP_201_CREATED,
            detail="Account created. You can now log in.",
        )

    return AuthResponse(
        access_token=session.access_token,
        user_id=user.id,
        email=user.email,
        tier=Tier.free,
    )


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest) -> AuthResponse:
    """Authenticate with email + password, return JWT."""
    db = get_db()
    try:
        resp = db.auth.sign_in_with_password({"email": req.email, "password": req.password})
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {exc}",
        )

    if not resp.user or not resp.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    user = resp.user
    session = resp.session

    # Load tier from profiles
    tier = Tier.free
    try:
        profile = db.table("profiles").select("tier").eq("id", user.id).maybe_single().execute()
        if profile.data:
            tier = Tier(profile.data.get("tier", "free"))
    except Exception:
        pass

    return AuthResponse(
        access_token=session.access_token,
        user_id=user.id,
        email=user.email,
        tier=tier,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(user: UserProfile = Depends(require_auth)) -> None:
    """Sign out the current user (invalidates JWT server-side)."""
    try:
        db = get_db()
        db.auth.sign_out()
    except Exception:
        pass


@router.get("/me", response_model=UserProfile)
async def me(user: UserProfile = Depends(require_auth)) -> UserProfile:
    """Return the current authenticated user's profile."""
    return user
