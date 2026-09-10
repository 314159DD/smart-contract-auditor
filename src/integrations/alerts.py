"""
Alert webhook integration: emit signals for high-severity findings.

When an audit completes with CRITICAL or HIGH findings (confidence >= 0.8),
sends a webhook POST to a configured HTTP endpoint (Discord, Slack, custom).
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

# Confidence string → numeric mapping
_CONFIDENCE_MAP = {"high": 0.95, "medium": 0.7, "low": 0.4}

# Max retry attempts with exponential backoff
_MAX_RETRIES = 3
_BASE_DELAY = 1.0  # seconds


def _confidence_value(confidence: str | float) -> float:
    """Convert confidence string to float."""
    if isinstance(confidence, (int, float)):
        return float(confidence)
    return _CONFIDENCE_MAP.get(str(confidence).lower(), 0.5)


def build_signal(
    finding: dict,
    contract_address: Optional[str] = None,
    contract_name: Optional[str] = None,
) -> dict[str, Any]:
    """Build an alert payload from a finding dict."""
    severity = finding.get("severity", "UNKNOWN")
    title_prefix = f"{severity} {finding.get('detector', '').replace('_', ' ').title()}"
    addr_display = contract_address[:6] + "..." + contract_address[-4:] if contract_address and len(contract_address) >= 10 else (contract_address or "unknown")

    return {
        "source": "contract_audit",
        "title": f"{title_prefix} in {addr_display}",
        "summary": finding.get("description", finding.get("title", "")),
        "confidence": _confidence_value(finding.get("confidence", "medium")),
        "data": {
            "contract": contract_address or "",
            "contract_name": contract_name or "",
            "severity": severity,
            "detector": finding.get("detector", ""),
            "finding_title": finding.get("title", ""),
            "location": finding.get("location", ""),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def send_signal(signal: dict[str, Any], webhook_url: Optional[str] = None) -> bool:
    """POST a signal to the alert webhook with retry logic.

    Returns True if sent successfully, False otherwise.
    """
    url = webhook_url or settings.alert_webhook_url
    if not url:
        logger.debug("ALERT_WEBHOOK_URL not configured, skipping signal")
        return False

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, json=signal)
                resp.raise_for_status()
            logger.info("Alert sent: %s (attempt %d)", signal.get("title", ""), attempt)
            return True
        except Exception as exc:
            logger.warning(
                "Alert attempt %d/%d failed: %s", attempt, _MAX_RETRIES, exc
            )
            if attempt < _MAX_RETRIES:
                time.sleep(_BASE_DELAY * (2 ** (attempt - 1)))

    logger.error("Alert failed after %d attempts: %s", _MAX_RETRIES, signal.get("title", ""))
    return False


def emit_high_severity_signals(
    findings: list[dict],
    contract_address: Optional[str] = None,
    contract_name: Optional[str] = None,
    webhook_url: Optional[str] = None,
) -> list[dict]:
    """Filter CRITICAL/HIGH findings with confidence >= 0.8 and send signals.

    Returns list of signals that were successfully sent.
    """
    sent: list[dict] = []

    for finding in findings:
        severity = finding.get("severity", "").upper()
        if severity not in ("CRITICAL", "HIGH"):
            continue
        if _confidence_value(finding.get("confidence", "medium")) < 0.8:
            continue

        signal = build_signal(finding, contract_address, contract_name)
        if send_signal(signal, webhook_url=webhook_url):
            sent.append(signal)

    if sent:
        logger.info(
            "Emitted %d alert(s) for %s", len(sent), contract_name or contract_address or "unknown"
        )

    return sent
