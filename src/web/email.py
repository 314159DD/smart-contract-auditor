"""
Email notifications via Resend API.
Fires on audit completion with risk summary and report link.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


def _resend_send(to: str, subject: str, html: str) -> bool:
    """Send an email via Resend. Returns True on success."""
    if not settings.resend_api_key:
        logger.debug("RESEND_API_KEY not set — skipping email to %s", to)
        return False

    try:
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.email_from,
                "to": [to],
                "subject": subject,
                "html": html,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("Email send failed: %s", exc)
        return False


def send_audit_complete_email(
    to: str,
    contract_name: str,
    audit_id: str,
    risk_score: float,
    verdict: str,
    critical: int,
    high: int,
    share_slug: Optional[str] = None,
) -> None:
    """Send audit completion notification with summary and report link."""
    risk_color = (
        "#ef4444" if risk_score >= 80
        else "#f97316" if risk_score >= 50
        else "#eab308" if risk_score >= 20
        else "#22c55e"
    )

    report_url = (
        f"{settings.frontend_url}/report/{share_slug}"
        if share_slug
        else f"{settings.frontend_url}/audit/{audit_id}"
    )

    subject = f"Audit complete: {contract_name} — Risk {int(risk_score)}/100 ({verdict})"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0f172a; color: #e2e8f0; padding: 32px; border-radius: 8px;">
      <div style="text-align: center; margin-bottom: 24px;">
        <span style="color: #22c55e; font-size: 13px; letter-spacing: 2px; text-transform: uppercase;">ContractAuditor</span>
        <h1 style="color: #f8fafc; font-size: 22px; margin: 8px 0;">Audit Complete</h1>
      </div>

      <div style="background: #1e293b; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
        <p style="margin: 0 0 4px; color: #94a3b8; font-size: 13px;">Contract</p>
        <p style="margin: 0; font-size: 18px; font-weight: bold;">{contract_name}</p>
      </div>

      <div style="background: #1e293b; border-radius: 8px; padding: 20px; margin-bottom: 20px; text-align: center;">
        <p style="margin: 0 0 4px; color: #94a3b8; font-size: 13px;">Risk Score</p>
        <p style="margin: 0; font-size: 48px; font-weight: bold; color: {risk_color};">{int(risk_score)}</p>
        <p style="margin: 4px 0 0; color: {risk_color}; font-weight: 600;">{verdict}</p>
      </div>

      <div style="display: flex; gap: 12px; margin-bottom: 20px;">
        <div style="flex: 1; background: #1e293b; border-radius: 8px; padding: 16px; text-align: center;">
          <p style="margin: 0; color: #ef4444; font-size: 28px; font-weight: bold;">{critical}</p>
          <p style="margin: 4px 0 0; color: #94a3b8; font-size: 12px;">Critical</p>
        </div>
        <div style="flex: 1; background: #1e293b; border-radius: 8px; padding: 16px; text-align: center;">
          <p style="margin: 0; color: #f97316; font-size: 28px; font-weight: bold;">{high}</p>
          <p style="margin: 4px 0 0; color: #94a3b8; font-size: 12px;">High</p>
        </div>
      </div>

      <a href="{report_url}"
         style="display: block; text-align: center; background: #16a34a; color: white; text-decoration: none; padding: 14px 24px; border-radius: 8px; font-weight: bold; font-size: 16px; margin-bottom: 20px;">
        View Full Report →
      </a>

      <p style="color: #475569; font-size: 11px; text-align: center;">
        Sent by ContractAuditor · <a href="{settings.frontend_url}" style="color: #22c55e;">contractauditor.app</a>
      </p>
    </div>
    """

    _resend_send(to=to, subject=subject, html=html)
