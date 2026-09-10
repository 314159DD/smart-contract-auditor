"""
Billing routes:
  GET  /api/billing/usage        — return current tier + scan usage
  POST /api/billing/upgrade      — create Stripe Checkout session
  POST /api/billing/portal       — create Stripe Customer Portal session
  POST /api/billing/webhook      — Stripe webhook handler
"""
from __future__ import annotations

import os

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from src.config import settings
from src.web.database import get_db
from src.web.middleware.auth import require_auth
from src.web.models.billing import (
    PortalResponse,
    UpgradeRequest,
    UpgradeResponse,
    UsageResponse,
    WebhookResponse,
)
from src.web.models.user import TIER_LIMITS, Tier, UserProfile

router = APIRouter(prefix="/api/billing", tags=["billing"])


def _price_ids() -> dict[str, dict[str, str]]:
    """Price IDs loaded from environment variables at call time."""
    return {
        Tier.pro: {
            "monthly": os.getenv("STRIPE_PRICE_PRO_MONTHLY", "price_pro_monthly"),
            "annual": os.getenv("STRIPE_PRICE_PRO_ANNUAL", "price_pro_annual"),
        },
        Tier.enterprise: {
            "monthly": os.getenv("STRIPE_PRICE_ENTERPRISE_MONTHLY", "price_enterprise_monthly"),
            "annual": os.getenv("STRIPE_PRICE_ENTERPRISE_ANNUAL", "price_enterprise_annual"),
        },
    }


def _tier_from_price() -> dict[str, Tier]:
    """Reverse mapping: Stripe price ID → tier."""
    mapping: dict[str, Tier] = {}
    for tier, prices in _price_ids().items():
        for price_id in prices.values():
            mapping[price_id] = tier
    return mapping


def _get_stripe() -> stripe:
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing not configured",
        )
    stripe.api_key = settings.stripe_secret_key
    return stripe


@router.get("/usage", response_model=UsageResponse)
async def get_usage(user: UserProfile = Depends(require_auth)) -> UsageResponse:
    """Return current user's tier limits and scan usage."""
    limits = TIER_LIMITS[user.tier]
    return UsageResponse(
        tier=user.tier,
        monthly_scans_used=user.monthly_scan_count,
        monthly_scans_limit=limits["monthly_scans"],
        allowed_scan_types=limits["allowed_types"],
        max_lines=limits["max_lines"],
    )


@router.post("/upgrade", response_model=UpgradeResponse)
async def create_checkout(
    req: UpgradeRequest,
    user: UserProfile = Depends(require_auth),
) -> UpgradeResponse:
    """Create a Stripe Checkout session to upgrade tier."""
    if req.tier == Tier.free:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot checkout for free tier",
        )

    s = _get_stripe()
    billing_period = getattr(req, "billing_period", "monthly")
    price_id = _price_ids().get(req.tier, {}).get(billing_period)
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown tier or billing period: {req.tier}/{billing_period}",
        )

    # Ensure Stripe customer exists
    customer_id = user.stripe_customer_id
    if not customer_id:
        customer = s.Customer.create(email=user.email, metadata={"user_id": user.id})
        customer_id = customer.id
        try:
            db = get_db()
            db.table("profiles").update({"stripe_customer_id": customer_id}).eq("id", user.id).execute()
        except Exception:
            pass

    session = s.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=req.success_url,
        cancel_url=req.cancel_url,
        metadata={"user_id": user.id, "tier": req.tier},
    )

    return UpgradeResponse(checkout_url=session.url, session_id=session.id)


@router.post("/portal", response_model=PortalResponse)
async def customer_portal(user: UserProfile = Depends(require_auth)) -> PortalResponse:
    """Create a Stripe Customer Portal session for self-service management."""
    if not user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Stripe subscription found. Upgrade first.",
        )

    s = _get_stripe()
    session = s.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{settings.frontend_url}/dashboard",
    )
    return PortalResponse(portal_url=session.url)


@router.post("/webhook", response_model=WebhookResponse)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
) -> WebhookResponse:
    """Handle Stripe webhook events."""
    payload = await request.body()

    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Webhook not configured")

    s = _get_stripe()
    try:
        event = s.Webhook.construct_event(payload, stripe_signature, settings.stripe_webhook_secret)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    db = get_db()

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id")
        new_tier = session.get("metadata", {}).get("tier", Tier.pro)
        if user_id:
            try:
                db.table("profiles").update({
                    "tier": new_tier,
                    "stripe_subscription_id": session.get("subscription"),
                    "updated_at": __import__("datetime").datetime.utcnow().isoformat(),
                }).eq("id", user_id).execute()
            except Exception:
                pass

    elif event["type"] == "customer.subscription.updated":
        sub = event["data"]["object"]
        customer_id = sub.get("customer")
        price_id = sub["items"]["data"][0]["price"]["id"] if sub.get("items") else None
        new_tier = _tier_from_price().get(price_id) if price_id else None
        if customer_id and new_tier:
            try:
                db.table("profiles").update({
                    "tier": new_tier,
                    "updated_at": __import__("datetime").datetime.utcnow().isoformat(),
                }).eq("stripe_customer_id", customer_id).execute()
            except Exception:
                pass

    elif event["type"] == "customer.subscription.deleted":
        # Subscription cancelled — downgrade to free at period end
        sub = event["data"]["object"]
        customer_id = sub.get("customer")
        if customer_id:
            try:
                db.table("profiles").update({
                    "tier": Tier.free,
                    "stripe_subscription_id": None,
                    "updated_at": __import__("datetime").datetime.utcnow().isoformat(),
                }).eq("stripe_customer_id", customer_id).execute()
            except Exception:
                pass

    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        customer_id = invoice.get("customer")
        if customer_id:
            # Record the failure
            try:
                db.table("payment_failures").insert({
                    "stripe_customer_id": customer_id,
                    "invoice_id": invoice.get("id"),
                    "amount_due": invoice.get("amount_due"),
                }).execute()
            except Exception:
                pass

            # Send email notification
            try:
                profile = (
                    db.table("profiles")
                    .select("email")
                    .eq("stripe_customer_id", customer_id)
                    .maybe_single()
                    .execute()
                )
                if profile.data and profile.data.get("email"):
                    from src.web.email import _resend_send
                    amount_cents = invoice.get("amount_due", 0)
                    amount_dollars = amount_cents / 100
                    html = f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0f172a; color: #e2e8f0; padding: 32px; border-radius: 8px;">
                      <h2 style="color: #ef4444;">Payment Failed</h2>
                      <p>We couldn't process your ContractAuditor subscription payment of <strong>${amount_dollars:.2f}</strong>.</p>
                      <p>Your account will remain active during the grace period. Please update your payment method to avoid interruption.</p>
                      <a href="{settings.frontend_url}/dashboard"
                         style="display: inline-block; background: #16a34a; color: white; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: bold; margin-top: 16px;">
                        Update Payment Method →
                      </a>
                    </div>
                    """
                    _resend_send(
                        to=profile.data["email"],
                        subject="Action required: ContractAuditor payment failed",
                        html=html,
                    )
            except Exception:
                pass

    return WebhookResponse(received=True)
