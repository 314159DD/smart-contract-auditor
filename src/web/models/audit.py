"""Audit request/response Pydantic models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class AuditStatus(str, Enum):
    pending = "pending"
    scanning = "scanning"
    analyzing = "analyzing"
    complete = "complete"
    failed = "failed"


class ScanType(str, Enum):
    quick = "quick"
    standard = "standard"
    deep = "deep"


class AuditRequest(BaseModel):
    source: Optional[str] = None          # Solidity source code
    address: Optional[str] = None         # contract address
    chain: str = "ethereum"
    scan_type: ScanType = ScanType.quick
    contract_name: Optional[str] = None


class AuditCreateResponse(BaseModel):
    audit_id: str
    status: AuditStatus = AuditStatus.pending
    message: str = "Audit queued"


class FindingOut(BaseModel):
    severity: str
    title: str
    description: str
    location: str
    recommendation: str
    confidence: str
    source: str
    detector: str = ""
    attack_scenario: str = ""
    fix_before: str = ""
    fix_after: str = ""
    fix_explanation: str = ""
    cwe_id: str = ""


class SummaryOut(BaseModel):
    total_findings: int
    critical: int
    high: int
    medium: int
    low: int
    info: int
    risk_score: float
    verdict: str


class ContractInfoOut(BaseModel):
    name: str
    compiler_version: str
    function_count: int
    state_variable_count: int
    line_count: int


class AuditResultResponse(BaseModel):
    audit_id: str
    status: AuditStatus
    scan_type: str
    timestamp: Optional[datetime] = None
    contract_name: Optional[str] = None
    contract_address: Optional[str] = None
    chain: Optional[str] = None
    summary: Optional[SummaryOut] = None
    findings: Optional[list[FindingOut]] = None
    contract_info: Optional[ContractInfoOut] = None
    ai_cost_usd: float = 0.0
    scan_duration_seconds: float = 0.0
    error: Optional[str] = None


class AuditListItem(BaseModel):
    audit_id: str
    status: AuditStatus
    scan_type: str
    contract_name: Optional[str] = None
    contract_address: Optional[str] = None
    risk_score: Optional[float] = None
    verdict: Optional[str] = None
    timestamp: Optional[datetime] = None
