"""
API integration tests for the Contract Auditor FastAPI backend.

Tests cover:
  - POST /api/audit with valid Solidity returns 202 with audit_id
  - GET /api/audit/{id} returns proper status
  - GET /api/audits requires auth (401)
  - GET /health returns 200
  - Rate limiting behavior for anonymous users
  - Input validation (missing source, invalid scan type)
"""
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.web.app import create_app
from src.web.routes.audit import _jobs

# ── Constants ────────────────────────────────────────────────────────────────

CONTRACTS_DIR = Path(__file__).parent / "contracts"
REENTRANCY_SOURCE = (CONTRACTS_DIR / "vulnerable_reentrancy.sol").read_text(encoding="utf-8")

MINIMAL_CONTRACT = """
pragma solidity ^0.8.0;
contract Minimal {
    uint256 public x;
    function setX(uint256 _x) external { x = _x; }
}
"""


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def app():
    """Create a fresh FastAPI app for testing."""
    application = create_app()
    return application


@pytest.fixture
def client(app):
    """Create a TestClient that doesn't require a running server."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_jobs():
    """Clear in-memory job store between tests."""
    _jobs.clear()
    yield
    _jobs.clear()


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    """Reset rate limit stores between tests."""
    from src.web.middleware.rate_limit import _ip_store
    _ip_store.clear()
    yield
    _ip_store.clear()


@pytest.fixture
def mock_db():
    """Mock the database dependency so tests don't need Supabase."""
    mock_client = MagicMock()
    # Make DB calls return empty/no-ops
    mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=None)
    mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=None)
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=None)
    mock_client.auth.get_user.side_effect = Exception("No auth in tests")

    with patch("src.web.routes.audit.get_db", return_value=mock_client), \
         patch("src.web.middleware.auth.get_db", return_value=mock_client), \
         patch("src.web.database.get_db", return_value=mock_client):
        yield mock_client


# ── Health endpoint ──────────────────────────────────────────────────────────

@pytest.mark.api
class TestHealthEndpoint:

    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


# ── POST /api/audit ──────────────────────────────────────────────────────────

@pytest.mark.api
class TestCreateAudit:

    def test_submit_valid_solidity_returns_202(self, client, mock_db):
        """POST /api/audit with valid source returns 202 with audit_id."""
        resp = client.post("/api/audit", json={
            "source": MINIMAL_CONTRACT,
            "scan_type": "quick",
        })
        assert resp.status_code == 202, f"Expected 202, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "audit_id" in data
        assert len(data["audit_id"]) > 10  # UUID format

    def test_submit_reentrancy_contract(self, client, mock_db):
        """Submitting the reentrancy test contract should succeed."""
        resp = client.post("/api/audit", json={
            "source": REENTRANCY_SOURCE,
            "scan_type": "quick",
        })
        assert resp.status_code == 202
        data = resp.json()
        assert "audit_id" in data

    def test_submit_no_source_no_address_returns_422(self, client, mock_db):
        """Missing both source and address should return 422."""
        resp = client.post("/api/audit", json={
            "scan_type": "quick",
        })
        assert resp.status_code == 422

    def test_anonymous_standard_scan_forbidden(self, client, mock_db):
        """Anonymous users should not be able to run standard scans."""
        resp = client.post("/api/audit", json={
            "source": MINIMAL_CONTRACT,
            "scan_type": "standard",
        })
        assert resp.status_code == 403

    def test_anonymous_deep_scan_forbidden(self, client, mock_db):
        """Anonymous users should not be able to run deep scans."""
        resp = client.post("/api/audit", json={
            "source": MINIMAL_CONTRACT,
            "scan_type": "deep",
        })
        assert resp.status_code == 403

    def test_empty_source_returns_422(self, client, mock_db):
        """Empty source string and no address should be rejected."""
        resp = client.post("/api/audit", json={
            "source": "",
            "scan_type": "quick",
        })
        # Empty string + no address = 422
        assert resp.status_code == 422


# ── GET /api/audit/{id} ─────────────────────────────────────────────────────

@pytest.mark.api
class TestGetAudit:

    def test_get_nonexistent_audit_returns_404(self, client, mock_db):
        """Requesting a non-existent audit_id should return 404."""
        resp = client.get("/api/audit/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_get_pending_audit_returns_202(self, client, mock_db):
        """A just-submitted audit should return 202 (still processing)."""
        # Submit an audit
        post_resp = client.post("/api/audit", json={
            "source": MINIMAL_CONTRACT,
            "scan_type": "quick",
        })
        assert post_resp.status_code == 202
        audit_id = post_resp.json()["audit_id"]

        # Immediately GET it - should be 202 (pending/scanning)
        get_resp = client.get(f"/api/audit/{audit_id}")
        # Could be 200 or 202 depending on how fast background task ran
        assert get_resp.status_code in (200, 202)
        data = get_resp.json()
        assert data["audit_id"] == audit_id
        assert data["status"] in ("pending", "scanning", "analyzing", "complete", "failed")


# ── GET /api/audits ──────────────────────────────────────────────────────────

@pytest.mark.api
class TestListAudits:

    def test_list_audits_unauthenticated_returns_error(self, client, mock_db):
        """GET /api/audits without auth should return 401 or similar."""
        resp = client.get("/api/audits")
        # Without a valid bearer token, get_current_user returns None
        # The endpoint requires auth, so it should fail
        assert resp.status_code in (401, 500)


# ── Rate limiting ────────────────────────────────────────────────────────────

@pytest.mark.api
class TestRateLimiting:

    def test_anonymous_rate_limit_after_3_requests(self, client, mock_db):
        """After 3 anonymous quick scans, the 4th should be rate-limited (429)."""
        for i in range(3):
            resp = client.post("/api/audit", json={
                "source": MINIMAL_CONTRACT,
                "scan_type": "quick",
            })
            assert resp.status_code == 202, f"Request {i+1} failed: {resp.text}"

        # 4th request should be rate-limited
        resp = client.post("/api/audit", json={
            "source": MINIMAL_CONTRACT,
            "scan_type": "quick",
        })
        assert resp.status_code == 429, (
            f"Expected 429 after 3 anonymous scans, got {resp.status_code}"
        )


# ── Input validation ─────────────────────────────────────────────────────────

@pytest.mark.api
class TestInputValidation:

    def test_invalid_scan_type_returns_422(self, client, mock_db):
        """Invalid scan_type value should return 422 (Pydantic validation)."""
        resp = client.post("/api/audit", json={
            "source": MINIMAL_CONTRACT,
            "scan_type": "mega_deep_ultra",
        })
        assert resp.status_code == 422

    def test_malformed_json_returns_422(self, client, mock_db):
        """Non-JSON body should return 422."""
        resp = client.post(
            "/api/audit",
            content="this is not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_missing_body_returns_422(self, client, mock_db):
        """POST with no body should return 422."""
        resp = client.post("/api/audit")
        assert resp.status_code == 422


# ── CORS headers ─────────────────────────────────────────────────────────────

@pytest.mark.api
class TestCORS:

    def test_cors_allows_localhost(self, client):
        """CORS should allow http://localhost:3000."""
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_cors_allows_production_domain(self, client):
        """CORS should allow https://contractauditor.app."""
        resp = client.options(
            "/health",
            headers={
                "Origin": "https://contractauditor.app",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "https://contractauditor.app"

    def test_cors_allows_vercel_preview(self, client):
        """CORS should allow Vercel preview deployments."""
        resp = client.options(
            "/health",
            headers={
                "Origin": "https://smart-contract-auditor-abc123.vercel.app",
                "Access-Control-Request-Method": "GET",
            },
        )
        origin = resp.headers.get("access-control-allow-origin")
        assert origin == "https://smart-contract-auditor-abc123.vercel.app"

    def test_cors_rejects_unknown_origin(self, client):
        """CORS should NOT allow random origins."""
        resp = client.options(
            "/health",
            headers={
                "Origin": "https://evil-site.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        origin = resp.headers.get("access-control-allow-origin")
        assert origin != "https://evil-site.com", "CORS should reject unknown origins"
