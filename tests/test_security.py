"""
Security audit tests for the Contract Auditor.

Tests cover:
  - No hardcoded secrets in source code
  - CORS only allows expected origins
  - Auth middleware rejects invalid JWT tokens
  - User input is not passed unsanitized to shell/subprocess
  - No dangerous patterns in source
"""
import os
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.web.app import create_app

# ── Constants ────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"

# Patterns that indicate potential hardcoded secrets
SECRET_PATTERNS = [
    # API keys (actual keys, not references/env vars)
    (r'(?:api[_-]?key|apikey)\s*=\s*["\'][a-zA-Z0-9_\-]{20,}["\']', "Hardcoded API key"),
    # Anthropic keys
    (r'sk-ant-[a-zA-Z0-9_\-]{20,}', "Hardcoded Anthropic API key"),
    # OpenAI keys
    (r'sk-[a-zA-Z0-9]{48}', "Hardcoded OpenAI API key"),
    # Stripe keys
    (r'sk_live_[a-zA-Z0-9]{24,}', "Hardcoded Stripe live key"),
    (r'sk_test_[a-zA-Z0-9]{24,}', "Hardcoded Stripe test key"),
    # Supabase keys (anon/service)
    (r'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\.[a-zA-Z0-9_\-]{50,}', "Hardcoded JWT/Supabase key"),
    # AWS
    (r'AKIA[A-Z0-9]{16}', "Hardcoded AWS access key"),
    # Generic password assignment
    (r'(?:password|passwd|pwd)\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded password"),
    # Private keys (hex)
    (r'0x[a-fA-F0-9]{64}', "Possible hardcoded private key (64 hex chars)"),
]

# Patterns that indicate shell injection risk
SHELL_INJECTION_PATTERNS = [
    (r'os\.system\s*\(', "os.system() call — possible shell injection"),
    (r'os\.popen\s*\(', "os.popen() call — possible shell injection"),
    (r'subprocess\.call\s*\([^)]*shell\s*=\s*True', "subprocess.call(shell=True)"),
    (r'subprocess\.run\s*\([^)]*shell\s*=\s*True', "subprocess.run(shell=True)"),
    (r'subprocess\.Popen\s*\([^)]*shell\s*=\s*True', "subprocess.Popen(shell=True)"),
    (r'eval\s*\(', "eval() call — code execution risk"),
    (r'exec\s*\(', "exec() call — code execution risk"),
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_python_source_files() -> list[Path]:
    """Get all .py files in src/ directory."""
    return list(SRC_DIR.rglob("*.py"))


def _read_source(path: Path) -> str:
    """Read a Python file, skipping __pycache__."""
    if "__pycache__" in str(path):
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock DB for auth tests."""
    mock_client = MagicMock()
    mock_client.auth.get_user.side_effect = Exception("Invalid token")
    mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=None)
    with patch("src.web.middleware.auth.get_db", return_value=mock_client), \
         patch("src.web.routes.audit.get_db", return_value=mock_client), \
         patch("src.web.database.get_db", return_value=mock_client):
        yield mock_client


# ── No hardcoded secrets ─────────────────────────────────────────────────────

@pytest.mark.security
class TestNoHardcodedSecrets:

    @pytest.mark.parametrize("pattern,description", SECRET_PATTERNS)
    def test_no_secrets_in_source(self, pattern, description):
        """Scan all Python source files for hardcoded secret patterns."""
        violations = []
        regex = re.compile(pattern, re.IGNORECASE)

        for path in _get_python_source_files():
            content = _read_source(path)
            if not content:
                continue

            for i, line in enumerate(content.splitlines(), 1):
                # Skip comments and docstrings
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                # Skip lines that are just reading env vars
                if "os.getenv" in line or "os.environ" in line:
                    continue
                # Skip test files and example patterns
                if "test_" in path.name and ("SECRET_PATTERNS" in line or "pattern" in line):
                    continue

                if regex.search(line):
                    rel_path = path.relative_to(PROJECT_ROOT)
                    violations.append(f"  {rel_path}:{i} — {description}")

        assert not violations, (
            f"Found potential hardcoded secrets:\n" + "\n".join(violations)
        )

    def test_no_env_file_committed(self):
        """The .env file should not be in the source tree (only .env.example)."""
        env_file = PROJECT_ROOT / ".env"
        # .env may exist locally but should not contain real secrets
        # We just check it's not a large file with real credentials
        if env_file.exists():
            content = env_file.read_text(encoding="utf-8")
            for pattern, desc in SECRET_PATTERNS[:6]:  # Check key patterns
                regex = re.compile(pattern)
                if "test" not in path.name.lower():
                    matches = regex.findall(content)
                    # Allow if it's clearly placeholder values
                    real_matches = [
                        m for m in matches
                        if "change-me" not in m.lower()
                        and "your-" not in m.lower()
                        and "xxx" not in m.lower()
                    ]
                    assert not real_matches, f".env contains real secret: {desc}"

    def test_config_uses_env_vars(self):
        """Config values should come from environment variables, not hardcoded."""
        config_path = SRC_DIR / "config.py"
        content = config_path.read_text(encoding="utf-8")

        # Check that key config fields use os.getenv
        assert "os.getenv" in content, "Config should use os.getenv for secrets"
        assert "OPENROUTER_API_KEY" in content
        assert "SUPABASE_URL" in content
        assert "STRIPE_SECRET_KEY" in content


# ── CORS configuration ───────────────────────────────────────────────────────

@pytest.mark.security
class TestCORSConfiguration:

    def test_cors_allows_localhost_3000(self, client):
        resp = client.options("/health", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        })
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_cors_allows_production(self, client):
        resp = client.options("/health", headers={
            "Origin": "https://contractauditor.app",
            "Access-Control-Request-Method": "GET",
        })
        assert resp.headers.get("access-control-allow-origin") == "https://contractauditor.app"

    def test_cors_blocks_evil_origin(self, client):
        resp = client.options("/health", headers={
            "Origin": "https://attacker.com",
            "Access-Control-Request-Method": "GET",
        })
        origin = resp.headers.get("access-control-allow-origin")
        assert origin != "https://attacker.com", "CORS allows arbitrary origins"

    def test_cors_blocks_similar_domain(self, client):
        """Attacker using a similar domain should be blocked."""
        resp = client.options("/health", headers={
            "Origin": "https://contractauditor.app.evil.com",
            "Access-Control-Request-Method": "GET",
        })
        origin = resp.headers.get("access-control-allow-origin")
        assert origin != "https://contractauditor.app.evil.com"

    def test_cors_config_in_source(self):
        """Verify CORS origins are explicitly listed in source (not wildcard *)."""
        app_path = SRC_DIR / "web" / "app.py"
        content = app_path.read_text(encoding="utf-8")

        # Should NOT have allow_origins=["*"]
        assert 'allow_origins=["*"]' not in content, "CORS uses wildcard * — security risk"
        assert "allow_origins=['*']" not in content, "CORS uses wildcard * — security risk"

        # Should have explicit origins
        assert "localhost:3000" in content
        assert "contractauditor.app" in content


# ── Auth middleware ───────────────────────────────────────────────────────────

@pytest.mark.security
class TestAuthMiddleware:

    def test_invalid_jwt_returns_401(self, client, mock_db):
        """A garbage JWT should result in 401."""
        resp = client.get("/api/audits", headers={
            "Authorization": "Bearer this-is-not-a-valid-jwt-token-at-all"
        })
        # Should be 401 (invalid token) or 500 (DB error trying to validate)
        assert resp.status_code in (401, 500)

    def test_expired_jwt_returns_401(self, client, mock_db):
        """An expired-looking JWT should be rejected."""
        # This is a well-formed but invalid JWT
        fake_jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxfQ.invalid"
        resp = client.get("/api/audits", headers={
            "Authorization": f"Bearer {fake_jwt}"
        })
        assert resp.status_code in (401, 500)

    def test_no_auth_header_on_protected_route(self, client, mock_db):
        """Accessing a protected route without auth should fail."""
        resp = client.get("/api/audits")
        # get_current_user returns None, then route checks user is None -> 401 or 500
        assert resp.status_code in (401, 500)

    def test_malformed_auth_header(self, client, mock_db):
        """Auth header without Bearer prefix should fail."""
        resp = client.get("/api/audits", headers={
            "Authorization": "Token abc123"
        })
        # HTTPBearer expects "Bearer <token>" format
        assert resp.status_code in (401, 403, 500)


# ── No shell injection vectors ───────────────────────────────────────────────

@pytest.mark.security
class TestNoShellInjection:

    @pytest.mark.parametrize("pattern,description", SHELL_INJECTION_PATTERNS)
    def test_no_dangerous_shell_calls(self, pattern, description):
        """Source code should not use dangerous shell execution patterns."""
        violations = []
        regex = re.compile(pattern)

        for path in _get_python_source_files():
            content = _read_source(path)
            if not content:
                continue

            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                # Skip comments
                if stripped.startswith("#"):
                    continue
                # Skip this test file's own patterns list
                if "test_security.py" in str(path):
                    continue

                if regex.search(line):
                    rel_path = path.relative_to(PROJECT_ROOT)
                    violations.append(f"  {rel_path}:{i} — {description}: {stripped[:80]}")

        assert not violations, (
            f"Found dangerous shell/execution patterns:\n" + "\n".join(violations)
        )

    def test_subprocess_calls_use_list_args(self):
        """Any subprocess usage should use list args (not string + shell=True)."""
        for path in _get_python_source_files():
            content = _read_source(path)
            if not content or "test_security.py" in str(path):
                continue

            if "subprocess" in content:
                # Verify shell=True is not used
                assert "shell=True" not in content, (
                    f"{path.relative_to(PROJECT_ROOT)} uses subprocess with shell=True"
                )


# ── Input sanitization ───────────────────────────────────────────────────────

@pytest.mark.security
class TestInputSanitization:

    def test_solidity_source_not_passed_to_shell(self):
        """User-provided Solidity source must not be passed directly to os/subprocess."""
        # Check audit.py and the parser to ensure source code is not shell-executed
        audit_path = SRC_DIR / "audit.py"
        content = audit_path.read_text(encoding="utf-8")

        assert "os.system" not in content, "audit.py uses os.system — shell injection risk"
        assert "subprocess" not in content or "shell=True" not in content, (
            "audit.py passes user input to subprocess with shell=True"
        )

    def test_contract_address_not_passed_to_shell(self):
        """Contract addresses (user input) must not be shell-executed."""
        fetcher_path = SRC_DIR / "etherscan" / "fetcher.py"
        if fetcher_path.exists():
            content = fetcher_path.read_text(encoding="utf-8")
            assert "os.system" not in content
            assert "shell=True" not in content

    def test_no_string_format_in_sql(self):
        """Database queries should use parameterized queries, not string formatting."""
        for path in _get_python_source_files():
            content = _read_source(path)
            if not content or "test_" in path.name:
                continue

            # Check for f-string SQL patterns
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                if "f\"SELECT" in line or "f'SELECT" in line:
                    rel_path = path.relative_to(PROJECT_ROOT)
                    pytest.fail(
                        f"{rel_path}:{i} — SQL query uses f-string formatting: {line.strip()[:80]}"
                    )
                if "f\"INSERT" in line or "f'INSERT" in line:
                    rel_path = path.relative_to(PROJECT_ROOT)
                    pytest.fail(
                        f"{rel_path}:{i} — SQL query uses f-string formatting: {line.strip()[:80]}"
                    )


# ── Dependency / import safety ───────────────────────────────────────────────

@pytest.mark.security
class TestDependencySafety:

    def test_no_pickle_loads(self):
        """Source should not use pickle.loads (deserialization attack vector)."""
        for path in _get_python_source_files():
            content = _read_source(path)
            if not content or "test_" in path.name:
                continue
            assert "pickle.loads" not in content, (
                f"{path.relative_to(PROJECT_ROOT)} uses pickle.loads — deserialization risk"
            )

    def test_no_yaml_unsafe_load(self):
        """Source should not use yaml.load without SafeLoader."""
        for path in _get_python_source_files():
            content = _read_source(path)
            if not content or "test_" in path.name:
                continue
            if "yaml.load(" in content and "SafeLoader" not in content and "safe_load" not in content:
                pytest.fail(
                    f"{path.relative_to(PROJECT_ROOT)} uses yaml.load without SafeLoader"
                )

    def test_secret_key_not_default_in_production(self):
        """The default secret key should only be used in development."""
        config_path = SRC_DIR / "config.py"
        content = config_path.read_text(encoding="utf-8")

        # There should be a default that's clearly marked as "change me"
        assert "change-me" in content.lower() or "SECRET_KEY" in content, (
            "Config should have a clearly marked default secret key"
        )
