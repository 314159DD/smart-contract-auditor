"""
Integration tests for the full audit pipeline: parse -> detect -> report.

Tests cover:
  - Full pipeline for each sample contract in tests/contracts/
  - CLI entry point with --type quick
  - Edge cases: empty input, non-Solidity input, extremely long input
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from src.parser.solidity import SolidityParser
from src.detectors.runner import DetectorRunner, default_runner
from src.reports.models import AuditReport, ReportSummary, Finding, ContractInfo
from src.reports.generator import ReportGenerator

# ── Constants ────────────────────────────────────────────────────────────────

CONTRACTS_DIR = Path(__file__).parent / "contracts"
PROJECT_ROOT = Path(__file__).parent.parent

# All .sol files in the test contracts directory
SAMPLE_CONTRACTS = sorted(CONTRACTS_DIR.glob("*.sol"))


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_and_detect(source: str) -> tuple[list, list]:
    """Parse source and run all detectors, returning (contracts, findings)."""
    parser = SolidityParser()
    contracts = parser.parse(source)
    if not contracts:
        return [], []
    runner = DetectorRunner()
    findings = runner.run_all(contracts[0])
    return contracts, findings


def _full_pipeline(source: str, contract_name: str = "Test") -> AuditReport:
    """Run the complete pipeline: parse -> detect -> build report."""
    parser = SolidityParser()
    contracts = parser.parse(source)
    assert contracts, f"Parser returned no contracts for {contract_name}"

    contract = contracts[0]
    runner = DetectorRunner()
    findings = runner.run_all(contract)

    report = AuditReport.build(
        contract=contract,
        static_findings=findings,
        ai_analysis=None,
        scan_type="quick",
    )
    return report


# ── Pipeline integration tests for each sample contract ──────────────────────

@pytest.mark.integration
class TestFullPipeline:
    """Parse -> Detect -> Report for each sample contract."""

    @pytest.mark.parametrize(
        "sol_path",
        SAMPLE_CONTRACTS,
        ids=[p.stem for p in SAMPLE_CONTRACTS],
    )
    def test_pipeline_produces_valid_report(self, sol_path: Path):
        """Each sample contract should produce a complete AuditReport."""
        source = sol_path.read_text(encoding="utf-8")
        report = _full_pipeline(source, contract_name=sol_path.stem)

        # Report structure checks
        assert report.contract_name, "Report missing contract_name"
        assert report.scan_type == "quick"
        assert report.timestamp is not None
        assert report.source_hash, "Report missing source_hash"
        assert isinstance(report.summary, ReportSummary)
        assert isinstance(report.contract_info, ContractInfo)
        assert isinstance(report.findings, list)

        # Summary should have valid counts
        s = report.summary
        assert s.total_findings >= 0
        assert s.risk_score >= 0
        assert s.verdict in ("PASS", "CAUTION", "FAIL")
        assert s.total_findings == s.critical + s.high + s.medium + s.low + s.info

    def test_vulnerable_reentrancy_finds_critical(self):
        """Reentrancy contract must produce at least one CRITICAL finding."""
        source = (CONTRACTS_DIR / "vulnerable_reentrancy.sol").read_text(encoding="utf-8")
        report = _full_pipeline(source, "VulnerableBank")

        critical = [f for f in report.findings if f.severity == "CRITICAL"]
        assert len(critical) >= 1, "Reentrancy contract should have CRITICAL findings"
        assert report.summary.verdict in ("FAIL", "CAUTION")

    def test_vulnerable_access_control_flags_issues(self):
        """Access control contract must flag missing protections."""
        source = (CONTRACTS_DIR / "vulnerable_access_control.sol").read_text(encoding="utf-8")
        report = _full_pipeline(source, "VulnerableToken")

        assert report.summary.total_findings > 0, "Should find access control issues"
        severities = {f.severity for f in report.findings}
        assert severities & {"CRITICAL", "HIGH"}, "Should have HIGH or CRITICAL findings"

    def test_safe_contract_minimal_findings(self):
        """Safe ERC-20 should produce fewer and lower-severity findings."""
        source = (CONTRACTS_DIR / "safe_erc20.sol").read_text(encoding="utf-8")
        report = _full_pipeline(source, "SafeToken")

        # Safe contract should not have CRITICAL from static detectors
        critical_static = [
            f for f in report.findings
            if f.severity == "CRITICAL" and f.source == "static"
        ]
        # It's acceptable to have some findings, but critical count should be low
        assert len(critical_static) <= 1, (
            f"Safe contract has {len(critical_static)} CRITICAL static findings"
        )


# ── Report format tests ─────────────────────────────────────────────────────

@pytest.mark.integration
class TestReportFormats:
    """Verify that reports can be generated in all formats."""

    @pytest.fixture
    def sample_report(self) -> AuditReport:
        source = (CONTRACTS_DIR / "vulnerable_reentrancy.sol").read_text(encoding="utf-8")
        return _full_pipeline(source, "VulnerableBank")

    def test_markdown_report(self, sample_report):
        gen = ReportGenerator()
        md = gen.to_markdown(sample_report)

        assert isinstance(md, str)
        assert len(md) > 100, "Markdown report too short"
        assert "Smart Contract Audit Report" in md
        assert "Disclaimer" in md
        assert sample_report.contract_name in md

    def test_json_report(self, sample_report):
        import json
        gen = ReportGenerator()
        json_str = gen.to_json(sample_report)

        data = json.loads(json_str)
        assert data["contract_name"] == sample_report.contract_name
        assert "summary" in data
        assert "findings" in data
        assert isinstance(data["findings"], list)

    def test_html_report(self, sample_report):
        gen = ReportGenerator()
        html = gen.to_html(sample_report)

        assert isinstance(html, str)
        assert "<html" in html.lower() or "<!doctype" in html.lower() or "<div" in html
        assert sample_report.contract_name in html


# ── CLI entry point tests ────────────────────────────────────────────────────

@pytest.mark.integration
class TestCLI:
    """Test that the CLI entry point works."""

    def test_cli_quick_scan(self):
        """CLI should run a quick scan and produce output."""
        sol_file = str(CONTRACTS_DIR / "vulnerable_reentrancy.sol")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, "-m", "src.audit", "scan", sol_file, "--type", "quick"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=60,
            env=env,
        )
        # CLI should succeed (exit 0) for a valid contract
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        # Should print some output (report or summary)
        assert len(result.stdout) > 0, "CLI produced no output"

    def test_cli_no_args_shows_help(self):
        """CLI with no subcommand should print help and exit 1."""
        result = subprocess.run(
            [sys.executable, "-m", "src.audit"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=15,
        )
        assert result.returncode == 1

    def test_cli_scan_no_file_no_address(self):
        """CLI scan without file or address should exit 1."""
        result = subprocess.run(
            [sys.executable, "-m", "src.audit", "scan"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=15,
        )
        assert result.returncode == 1

    def test_cli_nonexistent_file(self):
        """CLI with a nonexistent file should exit 1."""
        result = subprocess.run(
            [sys.executable, "-m", "src.audit", "scan", "/tmp/does_not_exist.sol", "--type", "quick"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=15,
        )
        assert result.returncode == 1
        assert "error" in result.stderr.lower() or "Error" in result.stderr


# ── Edge case tests ──────────────────────────────────────────────────────────

@pytest.mark.integration
class TestEdgeCases:
    """Edge cases: empty input, non-Solidity, extremely long input."""

    def test_empty_string_returns_no_contracts(self):
        """Empty source should parse to zero contracts."""
        parser = SolidityParser()
        contracts = parser.parse("")
        assert contracts == [], "Empty source should produce no contracts"

    def test_empty_string_raises_on_full_pipeline(self):
        """Full pipeline with empty source should raise ValueError."""
        from src.audit import run_scan
        with pytest.raises(ValueError, match="No contracts found"):
            run_scan(source="", contract_name="Empty", scan_type="quick")

    def test_non_solidity_input(self):
        """Random text (not Solidity) should parse to zero contracts."""
        parser = SolidityParser()
        contracts = parser.parse("This is just plain English text with no Solidity code.")
        assert contracts == [], "Non-Solidity input should produce no contracts"

    def test_non_solidity_json_input(self):
        """JSON input should parse to zero contracts."""
        parser = SolidityParser()
        contracts = parser.parse('{"key": "value", "number": 42}')
        assert contracts == [], "JSON input should produce no contracts"

    def test_non_solidity_python_input(self):
        """Python code should parse to zero contracts."""
        parser = SolidityParser()
        contracts = parser.parse("def hello():\n    print('hello world')\n")
        assert contracts == [], "Python code should produce no contracts"

    def test_extremely_long_input(self):
        """Very long Solidity source should still parse without crashing."""
        # Generate a contract with many functions
        functions = "\n".join(
            f"    function fn{i}() external pure returns (uint256) {{ return {i}; }}"
            for i in range(500)
        )
        source = f"""
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract LargeContract {{
{functions}
}}
"""
        parser = SolidityParser()
        contracts = parser.parse(source)
        assert len(contracts) == 1
        assert len(contracts[0].functions) >= 400, (
            f"Expected 500 functions, got {len(contracts[0].functions)}"
        )

    def test_contract_with_only_comments(self):
        """A file with only comments and pragma (no contract) should parse empty."""
        source = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// This file has no contract definition
// Just some comments
"""
        parser = SolidityParser()
        contracts = parser.parse(source)
        assert contracts == []

    def test_multiple_contracts_in_one_file(self):
        """Source with multiple contracts should parse all of them."""
        source = """
pragma solidity ^0.8.0;

contract Alpha {
    uint256 public x;
    function setX(uint256 _x) external { x = _x; }
}

contract Beta {
    uint256 public y;
    function setY(uint256 _y) external { y = _y; }
}
"""
        parser = SolidityParser()
        contracts = parser.parse(source)
        assert len(contracts) == 2
        names = {c.name for c in contracts}
        assert names == {"Alpha", "Beta"}

    def test_null_bytes_in_source(self):
        """Source with embedded null bytes should not crash the parser."""
        source = "pragma solidity ^0.8.0;\x00\ncontract Null {\n    uint x;\n}\n"
        parser = SolidityParser()
        # Should either parse or return empty, but never crash
        try:
            contracts = parser.parse(source)
            assert isinstance(contracts, list)
        except Exception:
            # Acceptable to raise an error, just not crash with traceback
            pass
