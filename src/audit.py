"""
Contract Auditor CLI

Usage:
  python -m src.audit scan contract.sol --type quick
  python -m src.audit scan contract.sol --type standard --output report.md
  python -m src.audit scan contract.sol --type deep --output report.json --format json
  python -m src.audit scan --address 0x... --chain ethereum --type standard
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Optional

from src.parser.solidity import SolidityParser
from src.detectors.base import Vulnerability
from src.detectors.runner import DetectorRunner, default_runner
from src.ai.analyzer import AIAnalyzer
from src.reports.models import AuditReport
from src.reports.generator import ReportGenerator
from src.config import settings

logger = logging.getLogger(__name__)

# ── Input validation constants ────────────────────────────────────────────
MAX_LINES_FREE = 10_000
MAX_LINES_ABSOLUTE = 50_000


class ContractTooLargeError(ValueError):
    """Raised when the submitted contract exceeds the line-count limit."""


class InvalidContractError(ValueError):
    """Raised when the submitted source fails sanitization checks."""


def validate_contract_source(source: str, *, tier: str = "free") -> str:
    """
    Validate and sanitize Solidity source input.

    Raises:
        InvalidContractError: if binary data or null bytes detected.
        ContractTooLargeError: if line count exceeds the tier limit.
    Returns:
        The sanitized source string.
    """
    # Strip null bytes
    if "\x00" in source:
        source = source.replace("\x00", "")
        logger.warning("Null bytes stripped from contract source")

    # Reject binary content (high ratio of non-text characters)
    non_text = sum(1 for ch in source if ord(ch) < 9 or (13 < ord(ch) < 32))
    if len(source) > 0 and non_text / len(source) > 0.05:
        raise InvalidContractError(
            "Input appears to be binary data, not Solidity source code."
        )

    # Line-count limits
    line_count = source.count("\n") + 1
    limit = MAX_LINES_FREE if tier == "free" else MAX_LINES_ABSOLUTE
    if line_count > limit:
        raise ContractTooLargeError(
            f"Contract has {line_count:,} lines, exceeding the {limit:,}-line limit "
            f"for the {tier} tier."
        )

    logger.info("Contract source validated: %d lines, tier=%s", line_count, tier)
    return source


def run_scan(
    source: str,
    contract_name: str,
    scan_type: str = "quick",
    contract_address: Optional[str] = None,
    chain: Optional[str] = None,
    tier: str = "free",
) -> AuditReport:
    """
    Orchestrate a full audit scan.

    Returns an AuditReport with all findings.
    """
    logger.info(
        "Starting %s scan for contract=%s address=%s chain=%s",
        scan_type, contract_name, contract_address, chain,
    )
    start = time.monotonic()

    # Validate and sanitize input
    source = validate_contract_source(source, tier=tier)

    parser = SolidityParser()
    contracts = parser.parse(source)

    if not contracts:
        raise ValueError(f"No contracts found in provided source.")

    # Use the first (or matching) contract
    contract = contracts[0]
    if contract_name:
        for c in contracts:
            if c.name == contract_name:
                contract = c
                break

    # Static analysis
    logger.info("Running static detectors on %s", contract.name)
    runner = DetectorRunner()  # uses all built-in detectors by default
    static_findings: list[Vulnerability] = runner.run_all(contract)
    logger.info("Static analysis found %d findings", len(static_findings))

    # AI analysis (skipped for quick scan)
    ai_analysis = None
    if scan_type in ("standard", "deep"):
        logger.info("Starting AI analysis (scan_type=%s)", scan_type)
        analyzer = AIAnalyzer(api_key=settings.openrouter_api_key, model=settings.ai_model)
        ai_analysis = analyzer.analyze(contract, static_findings, scan_type=scan_type)
        logger.info("AI analysis complete (cost=$%.4f)", ai_analysis.cost_usd if ai_analysis else 0)

    scan_duration = time.monotonic() - start
    logger.info("Scan complete in %.1fs", scan_duration)

    report = AuditReport.build(
        contract=contract,
        static_findings=static_findings,
        ai_analysis=ai_analysis,
        scan_type=scan_type,
        contract_address=contract_address,
        chain=chain,
        scan_duration=scan_duration,
    )
    return report


def scan_file(
    file_path: str,
    scan_type: str = "quick",
    output: Optional[str] = None,
    fmt: str = "markdown",
) -> AuditReport:
    """Scan a local .sol file."""
    source = Path(file_path).read_text(encoding="utf-8")
    contract_name = Path(file_path).stem
    report = run_scan(source, contract_name, scan_type=scan_type)
    _output_report(report, output, fmt)
    return report


def scan_address(
    address: str,
    chain: str = "ethereum",
    scan_type: str = "standard",
    output: Optional[str] = None,
    fmt: str = "markdown",
) -> AuditReport:
    """Fetch from Etherscan and scan a deployed contract."""
    from src.etherscan.fetcher import EtherscanFetcher
    with EtherscanFetcher(api_key=settings.etherscan_api_key) as fetcher:
        result = fetcher.fetch_source(address, chain=chain)

    source = result["source"]
    contract_name = result["contract_name"]
    report = run_scan(source, contract_name, scan_type=scan_type,
                      contract_address=address, chain=chain)
    _output_report(report, output, fmt)
    return report


def _output_report(report: AuditReport, output: Optional[str], fmt: str) -> None:
    gen = ReportGenerator()
    if output:
        gen.save(report, output, fmt=fmt)
        print(f"Report written to {output}")
    else:
        if fmt == "json":
            print(gen.to_json(report))
        elif fmt == "pdf":
            print("PDF output requires --output/-o to specify a file path.")
        else:
            print(gen.to_markdown(report))


def _print_summary(report: AuditReport) -> None:
    s = report.summary
    verdict_icon = {"PASS": "[PASS]", "CAUTION": "[WARN]", "FAIL": "[FAIL]"}.get(s.verdict, "[??]")
    print(f"\n{verdict_icon} {s.verdict}  |  Risk Score: {s.risk_score}/100")
    print(f"  Critical: {s.critical}  High: {s.high}  Medium: {s.medium}  Low: {s.low}  Info: {s.info}")
    print(f"  Scan type: {report.scan_type}  |  Duration: {report.scan_duration_seconds:.1f}s")


def main():
    parser = argparse.ArgumentParser(
        description="Smart Contract Auditor CLI",
        prog="python -m src.audit",
    )
    sub = parser.add_subparsers(dest="command")

    scan = sub.add_parser("scan", help="Audit a contract")
    scan.add_argument("file", nargs="?", help="Path to .sol file")
    scan.add_argument("--address", help="Contract address (fetch from Etherscan)")
    scan.add_argument("--chain", default="ethereum", help="Chain name (default: ethereum)")
    scan.add_argument(
        "--type",
        dest="scan_type",
        choices=["quick", "standard", "deep"],
        default="quick",
        help="Scan type (default: quick)",
    )
    scan.add_argument("--output", "-o", help="Output file path")
    scan.add_argument(
        "--format", "-f",
        dest="fmt",
        choices=["markdown", "json", "pdf"],
        default="markdown",
        help="Output format (default: markdown)",
    )

    args = parser.parse_args()

    if args.command != "scan":
        parser.print_help()
        sys.exit(1)

    try:
        if args.address:
            report = scan_address(
                address=args.address,
                chain=args.chain,
                scan_type=args.scan_type,
                output=args.output,
                fmt=args.fmt,
            )
        elif args.file:
            report = scan_file(
                file_path=args.file,
                scan_type=args.scan_type,
                output=args.output,
                fmt=args.fmt,
            )
        else:
            print("Error: provide either a file path or --address")
            sys.exit(1)

        _print_summary(report)

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
