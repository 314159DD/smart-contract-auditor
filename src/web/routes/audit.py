"""
Audit routes:
  POST   /api/audit              — submit new audit (returns audit_id immediately)
  GET    /api/audit/{id}         — get audit status / result
  GET    /api/audits             — list user's audits
  DELETE /api/audit/{id}         — delete an audit record
  POST   /api/audit/{id}/share   — generate shareable public URL
  GET    /api/public/audit/{slug} — view shared audit (no auth)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

import logging

from src.audit import run_scan, validate_contract_source, ContractTooLargeError, InvalidContractError
from src.config import settings

logger = logging.getLogger(__name__)
from src.etherscan.fetcher import EtherscanFetcher
from src.web.database import get_db
from src.web.middleware.auth import get_current_user
from src.web.middleware.rate_limit import (
    check_anonymous_rate_limit,
    check_line_limit,
    check_monthly_quota,
    check_tier_scan_type,
    get_client_ip,
)
from src.web.models.audit import (
    AuditCreateResponse,
    AuditListItem,
    AuditRequest,
    AuditResultResponse,
    AuditStatus,
    ContractInfoOut,
    FindingOut,
    SummaryOut,
)
from src.web.models.user import UserProfile

router = APIRouter(prefix="/api", tags=["audit"])

# In-memory job store for results before Supabase persistence
# Key: audit_id, Value: dict with status + result data
_jobs: dict[str, dict] = {}


def _record_to_response(record: dict) -> AuditResultResponse:
    """Convert a stored audit dict to AuditResultResponse."""
    summary = None
    if record.get("summary"):
        s = record["summary"]
        summary = SummaryOut(**s)

    findings = None
    if record.get("findings"):
        findings = [FindingOut(**f) for f in record["findings"]]

    contract_info = None
    if record.get("contract_info"):
        contract_info = ContractInfoOut(**record["contract_info"])

    return AuditResultResponse(
        audit_id=record["audit_id"],
        status=AuditStatus(record["status"]),
        scan_type=record.get("scan_type", "quick"),
        timestamp=record.get("timestamp"),
        contract_name=record.get("contract_name"),
        contract_address=record.get("contract_address"),
        chain=record.get("chain"),
        summary=summary,
        findings=findings,
        contract_info=contract_info,
        ai_cost_usd=record.get("ai_cost_usd", 0.0),
        scan_duration_seconds=record.get("scan_duration_seconds", 0.0),
        error=record.get("error"),
    )


async def _run_audit_background(
    audit_id: str,
    req: AuditRequest,
    user_id: Optional[str],
) -> None:
    """Background task: run the full audit pipeline and persist result."""
    logger.info("Background audit started: audit_id=%s, user_id=%s", audit_id, user_id)
    job = _jobs[audit_id]

    try:
        db = get_db()
    except RuntimeError:
        db = None

    try:
        job["status"] = AuditStatus.scanning
        _persist_status(db, audit_id, AuditStatus.scanning, user_id)

        # Fetch source if address provided
        source = req.source
        contract_name = req.contract_name or "Contract"
        if req.address:
            with EtherscanFetcher(api_key=settings.etherscan_api_key) as fetcher:
                fetched = fetcher.fetch_source(req.address, chain=req.chain)
            source = fetched["source"]
            contract_name = fetched["contract_name"]

        if not source:
            raise ValueError("No source code provided or fetched")

        if req.scan_type in ("standard", "deep"):
            job["status"] = AuditStatus.analyzing
            _persist_status(db, audit_id, AuditStatus.analyzing, user_id)

        report = run_scan(
            source=source,
            contract_name=contract_name,
            scan_type=req.scan_type,
            contract_address=req.address,
            chain=req.chain,
        )

        result_data = {
            "audit_id": audit_id,
            "status": AuditStatus.complete,
            "scan_type": report.scan_type,
            "timestamp": report.timestamp,
            "contract_name": report.contract_name,
            "contract_address": report.contract_address,
            "chain": report.chain,
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
            "findings": [
                {
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
                }
                for f in report.findings
            ],
            "contract_info": {
                "name": report.contract_info.name,
                "compiler_version": report.contract_info.compiler_version,
                "function_count": report.contract_info.function_count,
                "state_variable_count": report.contract_info.state_variable_count,
                "line_count": report.contract_info.line_count,
            },
            "ai_cost_usd": report.ai_cost_usd,
            "scan_duration_seconds": report.scan_duration_seconds,
        }

        job.update(result_data)
        _persist_result(db, audit_id, result_data, user_id)

        # Increment user scan count
        if user_id:
            db.rpc("increment_scan_count", {"user_id": user_id}).execute()

        # Send completion email notification
        if user_id and db:
            try:
                profile = db.table("profiles").select("email").eq("id", user_id).maybe_single().execute()
                if profile.data and profile.data.get("email"):
                    from src.web.email import send_audit_complete_email
                    s = result_data["summary"]
                    send_audit_complete_email(
                        to=profile.data["email"],
                        contract_name=result_data.get("contract_name", "Contract"),
                        audit_id=audit_id,
                        risk_score=s["risk_score"],
                        verdict=s["verdict"],
                        critical=s["critical"],
                        high=s["high"],
                    )
            except Exception:
                pass  # Non-fatal: don't fail the audit if email fails

        # Emit alert webhooks for high-severity findings
        try:
            from src.integrations.alerts import emit_high_severity_signals
            emit_high_severity_signals(
                findings=result_data.get("findings", []),
                contract_address=result_data.get("contract_address"),
                contract_name=result_data.get("contract_name"),
            )
        except Exception:
            pass  # Non-fatal: don't fail the audit if the alert webhook fails

    except Exception as exc:
        logger.error("Audit %s failed: %s", audit_id, exc, exc_info=True)
        job["status"] = AuditStatus.failed
        job["error"] = str(exc)
        _persist_status(db, audit_id, AuditStatus.failed, user_id, error=str(exc))


def _persist_status(db, audit_id: str, status: AuditStatus, user_id: Optional[str], error: str = "") -> None:
    if db is None:
        return
    try:
        db.table("audits").upsert({
            "id": audit_id,
            "user_id": user_id,
            "status": status,
            "error": error,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception:
        pass  # Non-fatal; in-memory store is source of truth


def _persist_result(db, audit_id: str, data: dict, user_id: Optional[str]) -> None:
    if db is None:
        return
    try:
        db.table("audits").upsert({
            "id": audit_id,
            "user_id": user_id,
            "status": AuditStatus.complete,
            "scan_type": data.get("scan_type"),
            "contract_name": data.get("contract_name"),
            "contract_address": data.get("contract_address"),
            "chain": data.get("chain"),
            "risk_score": data.get("summary", {}).get("risk_score"),
            "verdict": data.get("summary", {}).get("verdict"),
            "result_json": data,
            "ai_cost_usd": data.get("ai_cost_usd", 0.0),
            "scan_duration_seconds": data.get("scan_duration_seconds", 0.0),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception:
        pass


@router.post("/audit", response_model=AuditCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_audit(
    req: AuditRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    user: Optional[UserProfile] = Depends(get_current_user),
) -> AuditCreateResponse:
    """Submit a new audit. Returns audit_id immediately; processing is async."""
    # Validate input
    if not req.source and not req.address:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either 'source' (Solidity code) or 'address' (contract address)",
        )

    if user is None:
        # Anonymous: only quick scans allowed
        if req.scan_type != "quick":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anonymous users can only run quick scans. Sign up for standard/deep audits.",
            )
        ip = get_client_ip(request)
        check_anonymous_rate_limit(ip)
    else:
        check_tier_scan_type(user, req.scan_type)
        check_monthly_quota(user)
        if req.source:
            check_line_limit(user, req.source)

    # Validate and sanitize contract source before queuing
    if req.source:
        tier = user.tier.value if user else "free"
        try:
            req.source = validate_contract_source(req.source, tier=tier)
        except ContractTooLargeError as exc:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc))
        except InvalidContractError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    logger.info("Creating audit: scan_type=%s, address=%s, user=%s", req.scan_type, req.address, user.id if user else "anonymous")

    audit_id = str(uuid.uuid4())
    _jobs[audit_id] = {
        "audit_id": audit_id,
        "status": AuditStatus.pending,
        "scan_type": req.scan_type,
        "contract_address": req.address,
        "chain": req.chain,
        "user_id": user.id if user else None,
    }

    # Persist initial record
    try:
        db = get_db()
        db.table("audits").insert({
            "id": audit_id,
            "user_id": user.id if user else None,
            "status": AuditStatus.pending,
            "scan_type": req.scan_type,
            "contract_address": req.address,
            "chain": req.chain,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception:
        pass  # Non-fatal

    background_tasks.add_task(
        _run_audit_background,
        audit_id=audit_id,
        req=req,
        user_id=user.id if user else None,
    )

    return AuditCreateResponse(audit_id=audit_id)


@router.get("/audit/{audit_id}", response_model=AuditResultResponse)
async def get_audit(
    audit_id: str,
    user: Optional[UserProfile] = Depends(get_current_user),
) -> AuditResultResponse:
    """Get audit status or result. Returns 202 while still processing."""
    # Check in-memory store first
    if audit_id in _jobs:
        job = _jobs[audit_id]
        # Access control: only owner or anonymous owner (no user_id) can view
        if job.get("user_id") and user and job["user_id"] != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        response = _record_to_response(job)
        if response.status in (AuditStatus.pending, AuditStatus.scanning, AuditStatus.analyzing):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                content=response.model_dump(mode="json"),
                status_code=status.HTTP_202_ACCEPTED,
            )
        return response

    # Fallback to Supabase
    try:
        db = get_db()
        result = db.table("audits").select("*").eq("id", audit_id).maybe_single().execute()
        if result.data:
            row = result.data
            if row.get("user_id") and user and row["user_id"] != user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
            record = row.get("result_json") or {
                "audit_id": row["id"],
                "status": row["status"],
                "scan_type": row.get("scan_type", "quick"),
                "contract_name": row.get("contract_name"),
                "contract_address": row.get("contract_address"),
                "chain": row.get("chain"),
                "error": row.get("error"),
            }
            return _record_to_response(record)
    except HTTPException:
        raise
    except Exception:
        pass

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")


@router.get("/audits", response_model=list[AuditListItem])
async def list_audits(
    user: UserProfile = Depends(get_current_user),
) -> list[AuditListItem]:
    """List all audits for the authenticated user."""
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    try:
        db = get_db()
        result = (
            db.table("audits")
            .select("id, status, scan_type, contract_name, contract_address, created_at, risk_score, verdict")
            .eq("user_id", user.id)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
        return [
            AuditListItem(
                audit_id=row["id"],
                status=AuditStatus(row["status"]),
                scan_type=row.get("scan_type", "quick"),
                contract_name=row.get("contract_name"),
                contract_address=row.get("contract_address"),
                risk_score=row.get("risk_score"),
                verdict=row.get("verdict"),
                timestamp=row.get("created_at"),
            )
            for row in (result.data or [])
        ]
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.delete("/audit/{audit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audit(
    audit_id: str,
    user: UserProfile = Depends(get_current_user),
) -> None:
    """Delete an audit record (authenticated owner only)."""
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    # Remove from in-memory store
    job = _jobs.pop(audit_id, None)
    if job and job.get("user_id") and job["user_id"] != user.id:
        _jobs[audit_id] = job  # put it back
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    try:
        db = get_db()
        result = db.table("audits").select("user_id").eq("id", audit_id).maybe_single().execute()
        if result.data:
            if result.data.get("user_id") != user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
            db.table("audits").delete().eq("id", audit_id).execute()
    except HTTPException:
        raise
    except Exception:
        pass



# NOTE: Share management (POST /api/audit/{id}/share, DELETE, GET /api/report/{slug})
# lives in src/web/routes/report.py to avoid duplicate route registrations.
