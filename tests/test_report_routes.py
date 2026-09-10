"""Tests for report routes: PDF export and share endpoints."""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from src.web.app import create_app
from src.web.middleware.auth import get_current_user, require_auth
from src.web.models.user import UserProfile, Tier


# ── Fixtures ─────────────────────────────────────────────────────────────────

AUDIT_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

COMPLETE_RESULT_JSON = {
    "audit_id": AUDIT_ID,
    "status": "complete",
    "scan_type": "quick",
    "contract_name": "TestToken",
    "contract_address": "0x1234",
    "chain": "ethereum",
    "summary": {
        "total_findings": 2,
        "critical": 1,
        "high": 1,
        "medium": 0,
        "low": 0,
        "info": 0,
        "risk_score": 35.0,
        "verdict": "FAIL",
    },
    "findings": [
        {
            "severity": "CRITICAL",
            "title": "Reentrancy",
            "description": "Test finding",
            "location": "withdraw()",
            "recommendation": "Use ReentrancyGuard",
            "confidence": "high",
            "source": "static",
        }
    ],
    "contract_info": {
        "name": "TestToken",
        "compiler_version": "0.8.20",
        "function_count": 5,
        "state_variable_count": 3,
        "line_count": 100,
    },
}

COMPLETE_AUDIT_ROW = {
    "id": AUDIT_ID,
    "user_id": "user-1",
    "status": "complete",
    "scan_type": "quick",
    "contract_name": "TestToken",
    "contract_address": "0x1234",
    "chain": "ethereum",
    "share_slug": None,
    "sharing_enabled": False,
    "result_json": COMPLETE_RESULT_JSON,
}

TEST_USER = UserProfile(id="user-1", email="user@test.com", tier=Tier.pro)
OTHER_USER = UserProfile(id="user-2", email="other@test.com", tier=Tier.free)


def _mock_db(row=None):
    """Create a mock Supabase client that returns the given row."""
    db = MagicMock()
    result = MagicMock()
    result.data = row
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = result
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = result
    db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    return db


def _build_client(user=TEST_USER, db_row=None):
    """Build TestClient with dependency overrides for auth and DB."""
    db = _mock_db(db_row)
    app = create_app()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_auth] = lambda: user

    with patch("src.web.routes.report.get_db", return_value=db):
        client = TestClient(app)
    return client, db


# ── Share endpoints ──────────────────────────────────────────────────────────


def test_enable_sharing_returns_slug():
    """POST /api/audit/{id}/share should return a deterministic slug."""
    db = _mock_db(COMPLETE_AUDIT_ROW)
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    app.dependency_overrides[require_auth] = lambda: TEST_USER

    with patch("src.web.routes.report.get_db", return_value=db):
        client = TestClient(app)
        resp = client.post(f"/api/audit/{AUDIT_ID}/share")

    assert resp.status_code == 200
    data = resp.json()
    assert "slug" in data
    assert len(data["slug"]) == 12
    assert data["sharing_enabled"] is True
    assert data["slug"] in data["url"]


def test_enable_sharing_denied_for_non_owner():
    """Non-owner should get 403 when trying to share."""
    db = _mock_db(COMPLETE_AUDIT_ROW)
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: OTHER_USER
    app.dependency_overrides[require_auth] = lambda: OTHER_USER

    with patch("src.web.routes.report.get_db", return_value=db):
        client = TestClient(app)
        resp = client.post(f"/api/audit/{AUDIT_ID}/share")

    assert resp.status_code == 403


def test_disable_sharing():
    """DELETE /api/audit/{id}/share should return 204."""
    db = _mock_db(COMPLETE_AUDIT_ROW)
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    app.dependency_overrides[require_auth] = lambda: TEST_USER

    with patch("src.web.routes.report.get_db", return_value=db):
        client = TestClient(app)
        resp = client.delete(f"/api/audit/{AUDIT_ID}/share")

    assert resp.status_code == 204


def test_get_shared_report_success():
    """GET /api/report/{slug} should return audit data when sharing enabled."""
    shared_row = {**COMPLETE_AUDIT_ROW, "share_slug": "abcdef123456", "sharing_enabled": True}
    db = _mock_db(shared_row)
    app = create_app()

    with patch("src.web.routes.report.get_db", return_value=db):
        client = TestClient(app)
        resp = client.get("/api/report/abcdef123456")

    assert resp.status_code == 200
    data = resp.json()
    assert data["contract_name"] == "TestToken"


def test_get_shared_report_not_found():
    """GET /api/report/{slug} should 404 when slug doesn't exist."""
    db = _mock_db(None)
    app = create_app()

    with patch("src.web.routes.report.get_db", return_value=db):
        client = TestClient(app)
        resp = client.get("/api/report/nonexistent00")

    assert resp.status_code == 404


# ── PDF export ───────────────────────────────────────────────────────────────


def test_pdf_endpoint_returns_download():
    """GET /api/audit/{id}/pdf should return a downloadable file."""
    db = _mock_db(COMPLETE_AUDIT_ROW)
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: TEST_USER

    in_mem_jobs = {AUDIT_ID: {**COMPLETE_RESULT_JSON, "user_id": "user-1"}}

    with patch("src.web.routes.report.get_db", return_value=db), \
         patch("src.web.routes.audit._jobs", in_mem_jobs):
        client = TestClient(app)
        resp = client.get(f"/api/audit/{AUDIT_ID}/pdf")

    assert resp.status_code == 200
    content_type = resp.headers.get("content-type", "")
    assert "application/pdf" in content_type or "text/html" in content_type
    assert "content-disposition" in resp.headers


def test_pdf_endpoint_rejects_incomplete_audit():
    """GET /api/audit/{id}/pdf should 409 if audit not complete."""
    db = _mock_db(None)
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: TEST_USER

    incomplete_job = {"audit_id": AUDIT_ID, "status": "scanning", "user_id": "user-1"}

    with patch("src.web.routes.report.get_db", return_value=db), \
         patch("src.web.routes.audit._jobs", {AUDIT_ID: incomplete_job}):
        client = TestClient(app)
        resp = client.get(f"/api/audit/{AUDIT_ID}/pdf")

    assert resp.status_code == 409


def test_pdf_endpoint_denies_non_owner():
    """GET /api/audit/{id}/pdf should 403 for non-owner when not shared."""
    db = _mock_db(COMPLETE_AUDIT_ROW)
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: OTHER_USER

    in_mem_jobs = {AUDIT_ID: {**COMPLETE_RESULT_JSON, "user_id": "user-1"}}

    with patch("src.web.routes.report.get_db", return_value=db), \
         patch("src.web.routes.audit._jobs", in_mem_jobs):
        client = TestClient(app)
        resp = client.get(f"/api/audit/{AUDIT_ID}/pdf")

    assert resp.status_code == 403


# ── PDF HTML generation ──────────────────────────────────────────────────────


def test_pdf_html_contains_findings():
    """The generated PDF HTML should include finding titles and severity."""
    from src.web.routes.report import _build_pdf_html

    html = _build_pdf_html(COMPLETE_RESULT_JSON)
    assert "TestToken" in html
    assert "Reentrancy" in html
    assert "CRITICAL" in html
    assert "Disclaimer" in html


def test_pdf_html_handles_no_findings():
    """PDF should render cleanly with zero findings."""
    from src.web.routes.report import _build_pdf_html

    data = {
        "contract_name": "SafeToken",
        "scan_type": "quick",
        "status": "complete",
        "summary": {
            "total_findings": 0, "critical": 0, "high": 0,
            "medium": 0, "low": 0, "info": 0,
            "risk_score": 0, "verdict": "PASS",
        },
        "findings": [],
        "contract_info": {
            "name": "SafeToken", "compiler_version": "0.8.20",
            "function_count": 3, "state_variable_count": 1, "line_count": 50,
        },
    }
    html = _build_pdf_html(data)
    assert "SafeToken" in html
    assert "No vulnerabilities detected" in html
    assert "PASS" in html
