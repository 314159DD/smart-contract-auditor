"""
Report dataclasses: AuditReport, Finding, ReportSummary, ContractInfo.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Finding:
    """A single vulnerability finding (merged from static + AI sources)."""
    severity: str                    # CRITICAL / HIGH / MEDIUM / LOW / INFO
    title: str
    description: str
    location: str
    recommendation: str
    confidence: str                  # high / medium / low
    source: str                      # "static" | "ai" | "both"
    detector: str = ""               # Detector name(s)
    attack_scenario: str = ""
    fix_before: str = ""
    fix_after: str = ""
    fix_explanation: str = ""
    cwe_id: str = ""
    references: list = field(default_factory=list)
    confirmed_by_static: bool = False

    # Display helpers
    SEVERITY_EMOJI = {
        "CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡",
        "LOW": "🔵", "INFO": "⚪",
    }

    def severity_icon(self) -> str:
        return self.SEVERITY_EMOJI.get(self.severity, "•")


@dataclass
class ReportSummary:
    total_findings: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0
    risk_score: float = 0.0          # 0-100 (0=safe, 100=extremely risky)
    verdict: str = "PASS"            # "PASS" / "CAUTION" / "FAIL"

    @classmethod
    def from_findings(cls, findings: list) -> "ReportSummary":
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for f in findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1

        # Weighted risk score
        score = min(100.0, (
            counts["CRITICAL"] * 25 +
            counts["HIGH"] * 10 +
            counts["MEDIUM"] * 4 +
            counts["LOW"] * 1 +
            counts["INFO"] * 0.2
        ))

        if counts["CRITICAL"] > 0 or score >= 50:
            verdict = "FAIL"
        elif counts["HIGH"] > 0 or score >= 20:
            verdict = "CAUTION"
        else:
            verdict = "PASS"

        return cls(
            total_findings=len(findings),
            critical=counts["CRITICAL"],
            high=counts["HIGH"],
            medium=counts["MEDIUM"],
            low=counts["LOW"],
            info=counts["INFO"],
            risk_score=round(score, 1),
            verdict=verdict,
        )


@dataclass
class ContractInfo:
    name: str
    compiler_version: str
    function_count: int = 0
    state_variable_count: int = 0
    inheritance: list = field(default_factory=list)
    imports: list = field(default_factory=list)
    line_count: int = 0


@dataclass
class AuditReport:
    contract_name: str
    scan_type: str                   # quick / standard / deep
    timestamp: datetime
    summary: ReportSummary
    findings: list                   # list[Finding]
    contract_info: ContractInfo
    source_hash: str = ""            # SHA-256 of source
    contract_address: Optional[str] = None
    chain: Optional[str] = None
    ai_model_used: str = ""
    ai_cost_usd: float = 0.0
    ai_tokens_used: int = 0
    scan_duration_seconds: float = 0.0

    @classmethod
    def build(
        cls,
        contract,                    # Contract
        static_findings: list,       # list[Vulnerability]
        ai_analysis=None,            # AIAnalysis | None
        scan_type: str = "quick",
        contract_address: Optional[str] = None,
        chain: Optional[str] = None,
        scan_duration: float = 0.0,
    ) -> "AuditReport":
        from src.reports.merger import merge_findings
        all_findings = merge_findings(static_findings, ai_analysis)
        summary = ReportSummary.from_findings(all_findings)
        info = ContractInfo(
            name=contract.name,
            compiler_version=contract.compiler_version,
            function_count=len(contract.functions),
            state_variable_count=len(contract.state_variables),
            inheritance=contract.inheritance,
            imports=contract.imports,
            line_count=contract.source.count("\n") + 1,
        )
        source_hash = hashlib.sha256(contract.source.encode()).hexdigest()
        return cls(
            contract_name=contract.name,
            scan_type=scan_type,
            timestamp=datetime.utcnow(),
            summary=summary,
            findings=all_findings,
            contract_info=info,
            source_hash=source_hash,
            contract_address=contract_address,
            chain=chain,
            ai_model_used=ai_analysis.model_used if ai_analysis else "",
            ai_cost_usd=ai_analysis.cost_usd if ai_analysis else 0.0,
            ai_tokens_used=ai_analysis.tokens_used if ai_analysis else 0,
            scan_duration_seconds=scan_duration,
        )
