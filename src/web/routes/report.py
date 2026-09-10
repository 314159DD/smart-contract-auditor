"""
Report sharing and PDF export routes:
  POST  /api/audit/{id}/share         — generate/get public share slug
  DELETE /api/audit/{id}/share        — disable sharing
  GET   /api/report/{slug}            — fetch shared audit by slug (public)
  GET   /api/audit/{id}/pdf           — download PDF report
"""
from __future__ import annotations

import hashlib
import io
import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.web.database import get_db
from src.web.middleware.auth import get_current_user, require_auth
from src.web.models.user import UserProfile

router = APIRouter(prefix="/api", tags=["report"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ShareResponse(BaseModel):
    slug: str
    url: str
    sharing_enabled: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_slug(audit_id: str) -> str:
    """Deterministic 12-char slug derived from audit ID."""
    return hashlib.sha256(audit_id.encode()).hexdigest()[:12]


def _get_audit_record(db, audit_id: str) -> dict:
    """Fetch audit from Supabase; raise 404 if missing."""
    result = (
        db.table("audits")
        .select("*")
        .eq("id", audit_id)
        .maybe_single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
    return result.data


# ---------------------------------------------------------------------------
# Share management
# ---------------------------------------------------------------------------

@router.post("/audit/{audit_id}/share", response_model=ShareResponse)
async def enable_sharing(
    audit_id: str,
    user: UserProfile = Depends(require_auth),
) -> ShareResponse:
    """Enable sharing for an audit, returning the public slug."""
    db = get_db()
    row = _get_audit_record(db, audit_id)

    if row.get("user_id") != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    slug = _make_slug(audit_id)
    try:
        db.table("audits").update({
            "share_slug": slug,
            "sharing_enabled": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", audit_id).execute()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    frontend_origin = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    return ShareResponse(
        slug=slug,
        url=f"{frontend_origin}/report/{slug}",
        sharing_enabled=True,
    )


@router.delete("/audit/{audit_id}/share", status_code=status.HTTP_204_NO_CONTENT)
async def disable_sharing(
    audit_id: str,
    user: UserProfile = Depends(require_auth),
) -> None:
    """Disable public sharing for an audit."""
    db = get_db()
    row = _get_audit_record(db, audit_id)

    if row.get("user_id") != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    try:
        db.table("audits").update({
            "sharing_enabled": False,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", audit_id).execute()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/report/{slug}")
async def get_shared_report(slug: str) -> dict:
    """Public endpoint — fetch a shared audit by slug."""
    db = get_db()
    try:
        result = (
            db.table("audits")
            .select("*")
            .eq("share_slug", slug)
            .eq("sharing_enabled", True)
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found or sharing disabled")

    row = result.data
    data = row.get("result_json") or {
        "audit_id": row["id"],
        "status": row["status"],
        "scan_type": row.get("scan_type", "quick"),
        "contract_name": row.get("contract_name"),
        "contract_address": row.get("contract_address"),
        "chain": row.get("chain"),
    }
    return data


# ---------------------------------------------------------------------------
# PDF export
# ---------------------------------------------------------------------------

def _build_pdf_html(audit_data: dict) -> str:
    """Build a professional HTML report for weasyprint to render as PDF."""
    summary = audit_data.get("summary") or {}
    findings = audit_data.get("findings") or []
    contract_info = audit_data.get("contract_info") or {}

    risk_score = summary.get("risk_score", 0)
    verdict = summary.get("verdict", "UNKNOWN")

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

    findings_html = ""
    for i, f in enumerate(findings, 1):
        sev = f.get("severity", "INFO").upper()
        bg, text = severity_colors.get(sev, ("#1f2937", "#d1d5db"))
        fix_before = f.get("fix_before", "")
        fix_after = f.get("fix_after", "")
        fix_blocks = ""
        if fix_before:
            fix_blocks += f"""
            <div class="code-block vulnerable">
              <div class="code-label">Vulnerable Code</div>
              <pre>{fix_before}</pre>
            </div>"""
        if fix_after:
            fix_blocks += f"""
            <div class="code-block fixed">
              <div class="code-label">Fixed Code</div>
              <pre>{fix_after}</pre>
            </div>"""

        findings_html += f"""
        <div class="finding" style="border-left: 4px solid {bg};">
          <div class="finding-header">
            <span class="severity-badge" style="background:{bg}; color:{text};">{sev}</span>
            <span class="finding-title">{f.get('title', '')}</span>
          </div>
          <p class="finding-meta">Location: <code>{f.get('location', '—')}</code></p>
          <p>{f.get('description', '')}</p>
          {fix_blocks}
          <div class="recommendation">
            <strong>Recommendation:</strong> {f.get('recommendation', '')}
          </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page {{ margin: 2cm; size: A4; }}
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #1a202c; line-height: 1.6; }}
  .cover {{ text-align: center; padding: 4cm 0; border-bottom: 2px solid #e2e8f0; margin-bottom: 2em; }}
  .cover h1 {{ font-size: 28px; color: #1a202c; margin-bottom: 0.5em; }}
  .cover .meta {{ color: #718096; font-size: 14px; }}
  .risk-score {{ display: inline-block; font-size: 48px; font-weight: bold; color: {risk_color}; }}
  .verdict {{ display: inline-block; font-size: 20px; margin-left: 12px; color: {risk_color}; }}
  h2 {{ font-size: 18px; color: #2d3748; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; margin-top: 2em; }}
  .summary-table {{ width: 100%; border-collapse: collapse; margin: 1em 0; }}
  .summary-table th, .summary-table td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
  .summary-table th {{ background: #f7fafc; font-size: 13px; }}
  .finding {{ background: #f8fafc; padding: 16px; margin: 12px 0; border-radius: 4px; page-break-inside: avoid; }}
  .finding-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }}
  .severity-badge {{ padding: 2px 10px; border-radius: 4px; font-size: 11px; font-weight: bold; letter-spacing: 1px; }}
  .finding-title {{ font-size: 15px; font-weight: 600; }}
  .finding-meta {{ font-size: 12px; color: #718096; margin: 4px 0; }}
  .code-block {{ margin: 8px 0; }}
  .code-label {{ font-size: 11px; color: #718096; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
  pre {{ background: #1a202c; color: #e2e8f0; padding: 12px; border-radius: 4px; font-size: 11px; overflow: hidden; white-space: pre-wrap; word-break: break-all; }}
  .code-block.fixed pre {{ background: #1a3a2a; }}
  .code-block.vulnerable pre {{ background: #3a1a1a; }}
  .recommendation {{ background: #ebf8ff; border-left: 3px solid #63b3ed; padding: 8px 12px; margin-top: 8px; font-size: 13px; }}
  .disclaimer {{ background: #fffbeb; border: 1px solid #fbbf24; padding: 12px; border-radius: 4px; font-size: 11px; color: #92400e; margin-top: 3em; }}
  .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1em; }}
  .info-item {{ background: #f7fafc; padding: 12px; border-radius: 4px; }}
  .info-item label {{ font-size: 11px; color: #718096; text-transform: uppercase; letter-spacing: 0.5px; }}
  .info-item value {{ font-size: 16px; font-weight: 600; display: block; margin-top: 4px; }}
</style>
</head>
<body>
  <div class="cover">
    <div style="font-size:13px; color:#48bb78; letter-spacing:2px; text-transform:uppercase; margin-bottom:12px;">ContractAuditor Security Report</div>
    <h1>{audit_data.get('contract_name', 'Smart Contract Audit')}</h1>
    <div class="meta">
      {f'Contract: {audit_data.get("contract_address", "")} &nbsp;|&nbsp;' if audit_data.get('contract_address') else ''}
      {f'Chain: {audit_data.get("chain", "").capitalize()} &nbsp;|&nbsp;' if audit_data.get('chain') else ''}
      Scan type: {audit_data.get('scan_type', 'quick').upper()}
    </div>
    <div style="margin-top: 2em;">
      <span class="risk-score">{int(risk_score)}</span>
      <span class="verdict">/ 100 — {verdict}</span>
    </div>
  </div>

  <h2>Executive Summary</h2>
  <table class="summary-table">
    <tr><th>Severity</th><th>Count</th></tr>
    <tr><td>Critical</td><td>{summary.get('critical', 0)}</td></tr>
    <tr><td>High</td><td>{summary.get('high', 0)}</td></tr>
    <tr><td>Medium</td><td>{summary.get('medium', 0)}</td></tr>
    <tr><td>Low</td><td>{summary.get('low', 0)}</td></tr>
    <tr><td>Info</td><td>{summary.get('info', 0)}</td></tr>
    <tr><th>Total</th><th>{summary.get('total_findings', 0)}</th></tr>
  </table>

  {f'''<h2>Contract Information</h2>
  <div class="info-grid">
    <div class="info-item"><label>Compiler</label><value>{contract_info.get('compiler_version', '—')}</value></div>
    <div class="info-item"><label>Functions</label><value>{contract_info.get('function_count', 0)}</value></div>
    <div class="info-item"><label>State Variables</label><value>{contract_info.get('state_variable_count', 0)}</value></div>
    <div class="info-item"><label>Lines of Code</label><value>{contract_info.get('line_count', 0)}</value></div>
  </div>''' if contract_info else ''}

  <h2>Findings ({len(findings)})</h2>
  {findings_html if findings_html else '<p>No vulnerabilities detected.</p>'}

  <h2>Methodology</h2>
  <p>This audit was performed using a combination of automated static analysis (Slither) and AI-powered deep analysis (Claude). Static analysis detects common vulnerability patterns including reentrancy, access control issues, integer overflow, unchecked calls, and more. AI analysis examines business logic, economic attack vectors, and generates tailored fix suggestions.</p>

  <div class="disclaimer">
    <strong>Disclaimer:</strong> This report is provided for informational purposes only and does not constitute legal or financial advice. Smart contract audits cannot guarantee the absence of all vulnerabilities. No liability is assumed for losses arising from use of this report. Always consult multiple security experts before deploying contracts to production.
  </div>
</body>
</html>"""


@router.get("/audit/{audit_id}/pdf")
async def download_pdf(
    audit_id: str,
    user: Optional[UserProfile] = Depends(get_current_user),
) -> StreamingResponse:
    """Generate and return a PDF audit report."""
    from src.web.routes.audit import _jobs

    # Try in-memory store first
    audit_data: Optional[dict] = None
    if audit_id in _jobs:
        job = _jobs[audit_id]
        if job.get("user_id") and user and job["user_id"] != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        audit_data = job
    else:
        db = get_db()
        row = _get_audit_record(db, audit_id)

        # Check access: owner, or sharing enabled
        is_owner = user and row.get("user_id") == user.id
        is_shared = row.get("sharing_enabled", False)
        if not is_owner and not is_shared:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        audit_data = row.get("result_json") or {
            "audit_id": row["id"],
            "status": row["status"],
            "scan_type": row.get("scan_type", "quick"),
            "contract_name": row.get("contract_name"),
            "contract_address": row.get("contract_address"),
            "chain": row.get("chain"),
        }

    if audit_data.get("status") != "complete":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Audit is not complete yet",
        )

    # Build HTML from audit data (use inline builder for dict-based data from DB/memory)
    html_content = _build_pdf_html(audit_data)
    contract_name = (audit_data.get("contract_name") or "audit").replace(" ", "_")

    # Try weasyprint; fall back to HTML response if not installed
    try:
        import weasyprint
        pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
        filename = f"{contract_name}_audit_{audit_id[:8]}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ImportError:
        # weasyprint not installed — return HTML for download as fallback
        return Response(
            content=html_content,
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="{contract_name}_audit_{audit_id[:8]}.html"'},
        )
