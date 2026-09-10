"""
Report generator: produces Markdown, JSON, and PDF audit reports.
"""
from __future__ import annotations

import html as html_mod
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.reports.models import AuditReport, Finding, ReportSummary

_TEMPLATE_DIR = Path(__file__).parent / "templates"

_DISCLAIMER = """\
---
**Disclaimer:** This audit report is provided for informational purposes only.
It does not constitute legal, financial, or investment advice. Smart contract
audits cannot guarantee the absence of all vulnerabilities. The auditor assumes
no liability for losses arising from the use of this report or the audited code.
Always consult multiple security experts before deploying contracts to production.
"""


class ReportGenerator:
    """Generates audit reports in Markdown and JSON formats."""

    def to_markdown(self, report: AuditReport) -> str:
        """Render a full Markdown audit report."""
        lines = []
        lines.append(f"# Smart Contract Audit Report: {report.contract_name}")
        lines.append("")
        lines.append(f"**Scan Type:** {report.scan_type.upper()}")
        lines.append(f"**Date:** {report.timestamp.strftime('%Y-%m-%d %H:%M UTC')}")
        if report.contract_address:
            lines.append(f"**Contract Address:** `{report.contract_address}` ({report.chain or 'unknown chain'})")
        lines.append(f"**Source Hash (SHA-256):** `{report.source_hash}`")
        lines.append("")

        # Executive Summary
        s = report.summary
        lines.append("## Executive Summary")
        lines.append("")
        verdict_icon = {"PASS": "[PASS]", "CAUTION": "[WARN]", "FAIL": "[FAIL]"}.get(s.verdict, "[??]")
        lines.append(f"**Verdict:** {verdict_icon} {s.verdict}")
        lines.append(f"**Risk Score:** {s.risk_score}/100")
        lines.append("")
        lines.append("| Severity | Count |")
        lines.append("|----------|-------|")
        lines.append(f"| Critical | {s.critical} |")
        lines.append(f"| High | {s.high} |")
        lines.append(f"| Medium | {s.medium} |")
        lines.append(f"| Low | {s.low} |")
        lines.append(f"| Info | {s.info} |")
        lines.append(f"| **Total** | **{s.total_findings}** |")
        lines.append("")

        # Contract Overview
        ci = report.contract_info
        lines.append("## Contract Overview")
        lines.append("")
        lines.append(f"- **Compiler Version:** `{ci.compiler_version}`")
        lines.append(f"- **Functions:** {ci.function_count}")
        lines.append(f"- **State Variables:** {ci.state_variable_count}")
        lines.append(f"- **Lines of Code:** {ci.line_count}")
        if ci.inheritance:
            lines.append(f"- **Inherits from:** {', '.join(ci.inheritance)}")
        lines.append("")

        # Findings
        lines.append("## Findings")
        lines.append("")
        if not report.findings:
            lines.append("No vulnerabilities detected.")
        else:
            # Findings index table
            lines.append("| # | Severity | Title | Location | Source |")
            lines.append("|---|----------|-------|----------|--------|")
            for i, f in enumerate(report.findings, 1):
                icon = f.severity_icon()
                lines.append(
                    f"| {i} | {icon} {f.severity} | {f.title} | `{f.location}` | {f.source} |"
                )
            lines.append("")

            # Detailed finding sections
            for i, f in enumerate(report.findings, 1):
                lines.append(f"### Finding {i}: {f.severity_icon()} {f.title}")
                lines.append("")
                lines.append(f"**Severity:** {f.severity}")
                lines.append(f"**Confidence:** {f.confidence}")
                lines.append(f"**Location:** `{f.location}`")
                lines.append(f"**Source:** {f.source}")
                if f.cwe_id:
                    lines.append(f"**CWE:** {f.cwe_id}")
                lines.append("")
                lines.append("**Description:**")
                lines.append(f.description)
                lines.append("")
                if f.attack_scenario:
                    lines.append("**Attack Scenario:**")
                    lines.append(f.attack_scenario)
                    lines.append("")
                if f.fix_before:
                    lines.append("**Vulnerable Code:**")
                    lines.append("```solidity")
                    lines.append(f.fix_before)
                    lines.append("```")
                    lines.append("")
                if f.fix_after:
                    lines.append("**Recommended Fix:**")
                    lines.append("```solidity")
                    lines.append(f.fix_after)
                    lines.append("```")
                    lines.append("")
                if f.fix_explanation:
                    lines.append("**Why this fix works:**")
                    lines.append(f.fix_explanation)
                    lines.append("")
                else:
                    lines.append("**Recommendation:**")
                    lines.append(f.recommendation)
                    lines.append("")
                if f.references:
                    lines.append("**References:**")
                    for ref in f.references:
                        lines.append(f"- {ref}")
                    lines.append("")
                lines.append("---")
                lines.append("")

        # Methodology
        lines.append("## Methodology")
        lines.append("")
        lines.append("This audit was performed using:")
        lines.append("- **Static Analysis:** 10 built-in vulnerability detectors")
        lines.append(f"  covering reentrancy, access control, integer overflow,")
        lines.append(f"  unchecked calls, tx.origin, selfdestruct, delegatecall,")
        lines.append(f"  timestamp dependence, gas limits, and front-running.")
        if report.ai_model_used and report.ai_model_used != "none (static-only)":
            lines.append(f"- **AI Analysis:** {report.ai_model_used}")
            lines.append(f"  - Tokens used: {report.ai_tokens_used:,}")
            lines.append(f"  - Estimated cost: ${report.ai_cost_usd:.4f}")
        lines.append(f"- **Scan Duration:** {report.scan_duration_seconds:.1f}s")
        lines.append("")

        lines.append(_DISCLAIMER)
        return "\n".join(lines)

    def to_json(self, report: AuditReport) -> str:
        """Render a JSON audit report."""
        data = {
            "contract_name": report.contract_name,
            "contract_address": report.contract_address,
            "chain": report.chain,
            "source_hash": report.source_hash,
            "scan_type": report.scan_type,
            "timestamp": report.timestamp.isoformat(),
            "scan_duration_seconds": report.scan_duration_seconds,
            "summary": {
                "total_findings": report.summary.total_findings,
                "critical": report.summary.critical,
                "high": report.summary.high,
                "medium": report.summary.medium,
                "low": report.summary.low,
                "info": report.summary.info,
                "risk_score": report.summary.risk_score,
                "verdict": report.summary.verdict,
            },
            "findings": [self._finding_to_dict(f) for f in report.findings],
            "contract_info": {
                "name": report.contract_info.name,
                "compiler_version": report.contract_info.compiler_version,
                "function_count": report.contract_info.function_count,
                "state_variable_count": report.contract_info.state_variable_count,
                "inheritance": report.contract_info.inheritance,
                "line_count": report.contract_info.line_count,
            },
            "ai_model_used": report.ai_model_used,
            "ai_cost_usd": report.ai_cost_usd,
            "ai_tokens_used": report.ai_tokens_used,
        }
        return json.dumps(data, indent=2)

    def _finding_to_dict(self, f: Finding) -> dict:
        return {
            "severity": f.severity,
            "title": f.title,
            "description": f.description,
            "location": f.location,
            "recommendation": f.recommendation,
            "confidence": f.confidence,
            "source": f.source,
            "detector": f.detector,
            "attack_scenario": f.attack_scenario,
            "fix_before": f.fix_before,
            "fix_after": f.fix_after,
            "fix_explanation": f.fix_explanation,
            "cwe_id": f.cwe_id,
            "references": f.references,
            "confirmed_by_static": f.confirmed_by_static,
        }

    def to_html(self, report: AuditReport) -> str:
        """Render an HTML audit report suitable for PDF conversion."""
        s = report.summary
        risk_score = int(s.risk_score)
        risk_color = (
            "#ef4444" if risk_score >= 80
            else "#f97316" if risk_score >= 50
            else "#eab308" if risk_score >= 20
            else "#22c55e"
        )

        severity_colors = {
            "CRITICAL": ("#7f1d1d", "#fca5a5"),
            "HIGH": ("#7c2d12", "#fdba74"),
            "MEDIUM": ("#713f12", "#fde047"),
            "LOW": ("#1e3a5f", "#93c5fd"),
            "INFO": ("#1f2937", "#d1d5db"),
        }

        # Build findings HTML
        findings_html = ""
        if not report.findings:
            findings_html = "<p>No vulnerabilities detected.</p>"
        else:
            for i, f in enumerate(report.findings, 1):
                sev = f.severity.upper()
                bg, text = severity_colors.get(sev, ("#1f2937", "#d1d5db"))
                fix_blocks = ""
                if f.fix_before:
                    fix_blocks += (
                        '<div class="code-block vulnerable">'
                        '<div class="code-label">Vulnerable Code</div>'
                        f"<pre>{html_mod.escape(f.fix_before)}</pre></div>"
                    )
                if f.fix_after:
                    fix_blocks += (
                        '<div class="code-block fixed">'
                        '<div class="code-label">Fixed Code</div>'
                        f"<pre>{html_mod.escape(f.fix_after)}</pre></div>"
                    )
                findings_html += (
                    f'<div class="finding" style="border-left: 4px solid {bg};">'
                    f'<div class="finding-header">'
                    f'<span class="severity-badge" style="background:{bg}; color:{text};">{sev}</span>'
                    f'<span class="finding-title">{html_mod.escape(f.title)}</span>'
                    f'</div>'
                    f'<p class="finding-meta">Location: <code>{html_mod.escape(f.location)}</code></p>'
                    f'<p>{html_mod.escape(f.description)}</p>'
                    f'{fix_blocks}'
                    f'<div class="recommendation"><strong>Recommendation:</strong> {html_mod.escape(f.recommendation)}</div>'
                    f'</div>'
                )

        # Build contract info
        ci = report.contract_info
        contract_info_html = (
            '<h2>Contract Information</h2>'
            '<div class="info-grid">'
            f'<div class="info-item"><label>Compiler</label><value>{html_mod.escape(ci.compiler_version)}</value></div>'
            f'<div class="info-item"><label>Functions</label><value>{ci.function_count}</value></div>'
            f'<div class="info-item"><label>State Variables</label><value>{ci.state_variable_count}</value></div>'
            f'<div class="info-item"><label>Lines of Code</label><value>{ci.line_count}</value></div>'
            '</div>'
        )

        # Build meta line
        meta_parts = []
        if report.contract_address:
            meta_parts.append(f"Contract: {report.contract_address}")
        if report.chain:
            meta_parts.append(f"Chain: {report.chain.capitalize()}")
        meta_line = " | ".join(meta_parts)
        if meta_line:
            meta_line += " | "

        # Read template and fill placeholders
        template = (_TEMPLATE_DIR / "report.html").read_text(encoding="utf-8")
        replacements = {
            "{{contract_name}}": html_mod.escape(report.contract_name),
            "{{meta_line}}": meta_line,
            "{{scan_type}}": report.scan_type.upper(),
            "{{risk_color}}": risk_color,
            "{{risk_score}}": str(risk_score),
            "{{verdict}}": s.verdict,
            "{{critical}}": str(s.critical),
            "{{high}}": str(s.high),
            "{{medium}}": str(s.medium),
            "{{low}}": str(s.low),
            "{{info}}": str(s.info),
            "{{total_findings}}": str(s.total_findings),
            "{{contract_info_html}}": contract_info_html,
            "{{findings_count}}": str(len(report.findings)),
            "{{findings_html}}": findings_html,
        }
        for key, value in replacements.items():
            template = template.replace(key, value)
        return template

    def to_pdf(self, report: AuditReport) -> bytes:
        """Render a PDF audit report using weasyprint."""
        html_content = self.to_html(report)
        import weasyprint
        return weasyprint.HTML(string=html_content).write_pdf()

    def save(self, report: AuditReport, output_path: str, fmt: str = "markdown") -> None:
        """Write report to file. fmt: 'markdown', 'json', or 'pdf'."""
        if fmt == "json":
            content = self.to_json(report)
            Path(output_path).write_text(content, encoding="utf-8")
        elif fmt == "pdf":
            pdf_bytes = self.to_pdf(report)
            Path(output_path).write_bytes(pdf_bytes)
        else:
            content = self.to_markdown(report)
            Path(output_path).write_text(content, encoding="utf-8")
