"""Tests for email notification service."""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.web.email import send_audit_complete_email, _resend_send


# ── _resend_send ─────────────────────────────────────────────────────────────


def test_resend_send_skips_when_no_api_key():
    """Should return False and not call httpx when RESEND_API_KEY is unset."""
    with patch("src.web.email.settings") as mock_settings:
        mock_settings.resend_api_key = None
        result = _resend_send("user@example.com", "Test", "<p>hi</p>")
        assert result is False


def test_resend_send_posts_to_resend_api():
    """Should POST to Resend API and return True on success."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()

    with patch("src.web.email.settings") as mock_settings, \
         patch("src.web.email.httpx.post", return_value=mock_resp) as mock_post:
        mock_settings.resend_api_key = "re_test123"
        mock_settings.email_from = "noreply@test.com"

        result = _resend_send("user@example.com", "Subject", "<p>body</p>")

        assert result is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["json"]["to"] == ["user@example.com"]
        assert call_kwargs.kwargs["json"]["subject"] == "Subject"
        assert call_kwargs.kwargs["json"]["from"] == "noreply@test.com"


def test_resend_send_returns_false_on_http_error():
    """Should return False when Resend returns an error."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("503 Service Unavailable")

    with patch("src.web.email.settings") as mock_settings, \
         patch("src.web.email.httpx.post", return_value=mock_resp):
        mock_settings.resend_api_key = "re_test123"
        mock_settings.email_from = "noreply@test.com"

        result = _resend_send("user@example.com", "Subject", "<p>body</p>")
        assert result is False


# ── send_audit_complete_email ────────────────────────────────────────────────


def test_audit_complete_email_includes_risk_score():
    """Email should include contract name, risk score, and verdict."""
    with patch("src.web.email._resend_send") as mock_send, \
         patch("src.web.email.settings") as mock_settings:
        mock_settings.frontend_url = "https://app.test"
        mock_send.return_value = True

        send_audit_complete_email(
            to="user@example.com",
            contract_name="VaultToken",
            audit_id="abc-123",
            risk_score=75.0,
            verdict="FAIL",
            critical=2,
            high=3,
        )

        mock_send.assert_called_once()
        _, kwargs = mock_send.call_args
        assert "VaultToken" in kwargs["subject"]
        assert "75" in kwargs["subject"]
        assert "FAIL" in kwargs["subject"]
        assert "VaultToken" in kwargs["html"]
        assert "75" in kwargs["html"]


def test_audit_complete_email_uses_share_slug_url():
    """When share_slug is provided, email link should use /report/{slug}."""
    with patch("src.web.email._resend_send") as mock_send, \
         patch("src.web.email.settings") as mock_settings:
        mock_settings.frontend_url = "https://app.test"
        mock_send.return_value = True

        send_audit_complete_email(
            to="user@example.com",
            contract_name="Token",
            audit_id="abc-123",
            risk_score=10.0,
            verdict="PASS",
            critical=0,
            high=0,
            share_slug="abcdef123456",
        )

        _, kwargs = mock_send.call_args
        assert "https://app.test/report/abcdef123456" in kwargs["html"]


def test_audit_complete_email_uses_audit_url_without_slug():
    """Without share_slug, email link should use /audit/{id}."""
    with patch("src.web.email._resend_send") as mock_send, \
         patch("src.web.email.settings") as mock_settings:
        mock_settings.frontend_url = "https://app.test"
        mock_send.return_value = True

        send_audit_complete_email(
            to="user@example.com",
            contract_name="Token",
            audit_id="abc-123",
            risk_score=10.0,
            verdict="PASS",
            critical=0,
            high=0,
        )

        _, kwargs = mock_send.call_args
        assert "https://app.test/audit/abc-123" in kwargs["html"]
