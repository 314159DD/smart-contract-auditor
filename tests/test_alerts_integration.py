"""Tests for the alert webhook integration."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from src.integrations.alerts import (
    _confidence_value,
    build_signal,
    emit_high_severity_signals,
    send_signal,
)


# --- Unit tests for confidence mapping ---

class TestConfidenceValue:
    def test_string_high(self):
        assert _confidence_value("high") == 0.95

    def test_string_medium(self):
        assert _confidence_value("medium") == 0.7

    def test_string_low(self):
        assert _confidence_value("low") == 0.4

    def test_numeric_passthrough(self):
        assert _confidence_value(0.85) == 0.85

    def test_unknown_string(self):
        assert _confidence_value("unknown") == 0.5


# --- Signal building ---

class TestBuildSignal:
    def test_basic_signal(self):
        finding = {
            "severity": "CRITICAL",
            "title": "Reentrancy in withdraw()",
            "description": "Unprotected withdrawal allows reentrancy",
            "detector": "reentrancy",
            "confidence": "high",
            "location": "Contract.sol:42",
        }
        signal = build_signal(finding, contract_address="0xABCDEF1234567890ABCDEF1234567890ABCDEF12", contract_name="Vault")

        assert signal["source"] == "contract_audit"
        assert "CRITICAL" in signal["title"]
        assert "0xABCD" in signal["title"]
        assert signal["confidence"] == 0.95
        assert signal["data"]["severity"] == "CRITICAL"
        assert signal["data"]["detector"] == "reentrancy"
        assert signal["data"]["contract_name"] == "Vault"
        assert "timestamp" in signal

    def test_no_address(self):
        finding = {"severity": "HIGH", "title": "Missing access control", "confidence": "high"}
        signal = build_signal(finding)
        assert "unknown" in signal["title"]
        assert signal["data"]["contract"] == ""


# --- Signal sending ---

class TestSendSignal:
    def test_no_webhook_url(self):
        signal = {"source": "contract_audit", "title": "test"}
        with patch("src.integrations.alerts.settings") as mock_settings:
            mock_settings.alert_webhook_url = None
            result = send_signal(signal)
        assert result is False

    def test_successful_send(self, httpx_mock):
        signal = {"source": "contract_audit", "title": "test"}
        httpx_mock.add_response(url="https://example.com/webhook", status_code=200)
        result = send_signal(signal, webhook_url="https://example.com/webhook")
        assert result is True

    def test_retry_on_failure_then_success(self, httpx_mock):
        signal = {"source": "contract_audit", "title": "test"}
        # First call fails, second succeeds
        httpx_mock.add_response(url="https://example.com/webhook", status_code=500)
        httpx_mock.add_response(url="https://example.com/webhook", status_code=200)
        with patch("src.integrations.alerts._BASE_DELAY", 0.01):
            result = send_signal(signal, webhook_url="https://example.com/webhook")
        assert result is True

    def test_all_retries_exhausted(self, httpx_mock):
        signal = {"source": "contract_audit", "title": "test"}
        for _ in range(3):
            httpx_mock.add_response(url="https://example.com/webhook", status_code=500)
        with patch("src.integrations.alerts._BASE_DELAY", 0.01):
            result = send_signal(signal, webhook_url="https://example.com/webhook")
        assert result is False


# --- Filtering and emission ---

class TestEmitHighSeveritySignals:
    def test_filters_low_severity(self, httpx_mock):
        findings = [
            {"severity": "LOW", "title": "Minor issue", "confidence": "high", "detector": "timestamp"},
            {"severity": "INFO", "title": "Informational", "confidence": "high", "detector": "info"},
        ]
        httpx_mock.add_response(url="https://example.com/webhook", status_code=200)
        sent = emit_high_severity_signals(findings, webhook_url="https://example.com/webhook")
        assert len(sent) == 0

    def test_filters_low_confidence(self, httpx_mock):
        findings = [
            {"severity": "CRITICAL", "title": "Maybe reentrancy", "confidence": "low", "detector": "reentrancy"},
        ]
        httpx_mock.add_response(url="https://example.com/webhook", status_code=200)
        sent = emit_high_severity_signals(findings, webhook_url="https://example.com/webhook")
        assert len(sent) == 0

    def test_sends_critical_high_confidence(self, httpx_mock):
        findings = [
            {"severity": "CRITICAL", "title": "Reentrancy", "confidence": "high", "detector": "reentrancy", "description": "Bad"},
            {"severity": "HIGH", "title": "Access control", "confidence": 0.9, "detector": "access_control", "description": "Missing"},
            {"severity": "MEDIUM", "title": "Timestamp", "confidence": "high", "detector": "timestamp", "description": "Minor"},
        ]
        httpx_mock.add_response(url="https://example.com/webhook", status_code=200)
        httpx_mock.add_response(url="https://example.com/webhook", status_code=200)
        sent = emit_high_severity_signals(
            findings,
            contract_address="0x1234567890123456789012345678901234567890",
            contract_name="TestVault",
            webhook_url="https://example.com/webhook",
        )
        assert len(sent) == 2
        assert all(s["source"] == "contract_audit" for s in sent)

    def test_empty_findings(self):
        sent = emit_high_severity_signals([], webhook_url="https://example.com/webhook")
        assert sent == []


# --- pytest-httpx fixture ---

@pytest.fixture
def httpx_mock():
    """Simple httpx mock using responses list."""
    from unittest.mock import MagicMock

    responses = []

    class MockTransport:
        def handle_request(self, request):
            import httpx as _httpx
            if responses:
                resp_config = responses.pop(0)
                return _httpx.Response(
                    status_code=resp_config["status_code"],
                    request=request,
                    content=b"",
                )
            return _httpx.Response(status_code=500, request=request, content=b"no mock")

    class MockHelper:
        def add_response(self, url: str, status_code: int = 200):
            responses.append({"url": url, "status_code": status_code})

    mock = MockHelper()

    with patch("src.integrations.alerts.httpx.Client") as mock_client_cls:
        transport = MockTransport()
        client_instance = MagicMock()

        def mock_post(url, json=None):
            import httpx as _httpx
            request = _httpx.Request("POST", url)
            resp = transport.handle_request(request)
            if resp.status_code >= 400:
                resp.raise_for_status()
            return resp

        client_instance.post = mock_post
        client_instance.__enter__ = lambda self: client_instance
        client_instance.__exit__ = lambda self, *args: None
        mock_client_cls.return_value = client_instance

        yield mock
