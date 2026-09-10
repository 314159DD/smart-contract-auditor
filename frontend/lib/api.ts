/**
 * API client — thin wrapper around fetch pointing to the FastAPI backend.
 * All paths go through Next.js rewrites → /api/* → http://localhost:8000/api/*
 */

const BASE = "";

export type ScanType = "quick" | "standard" | "deep";

export interface AuditRequest {
  source?: string;
  address?: string;
  chain?: string;
  scan_type: ScanType;
  contract_name?: string;
}

export interface AuditCreateResponse {
  audit_id: string;
  status: string;
  message: string;
}

export interface Finding {
  severity: string;
  title: string;
  description: string;
  location: string;
  recommendation: string;
  confidence: string;
  source: string;
  detector: string;
  attack_scenario: string;
  fix_before: string;
  fix_after: string;
  fix_explanation: string;
  cwe_id: string;
}

export interface Summary {
  total_findings: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
  risk_score: number;
  verdict: string;
}

export interface ContractInfo {
  name: string;
  compiler_version: string;
  function_count: number;
  state_variable_count: number;
  line_count: number;
}

export interface AuditResult {
  audit_id: string;
  status: "pending" | "scanning" | "analyzing" | "complete" | "failed";
  scan_type: string;
  timestamp?: string;
  contract_name?: string;
  contract_address?: string;
  chain?: string;
  summary?: Summary;
  findings?: Finding[];
  contract_info?: ContractInfo;
  ai_cost_usd: number;
  scan_duration_seconds: number;
  error?: string;
}

export interface AuditListItem {
  audit_id: string;
  status: string;
  scan_type: string;
  contract_name?: string;
  contract_address?: string;
  risk_score?: number;
  verdict?: string;
  timestamp?: string;
}

function authHeader(token?: string): HeadersInit {
  if (!token) return { "Content-Type": "application/json" };
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
}

export async function submitAudit(
  req: AuditRequest,
  token?: string
): Promise<AuditCreateResponse> {
  const res = await fetch(`${BASE}/api/audit`, {
    method: "POST",
    headers: authHeader(token),
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to submit audit");
  }
  return res.json();
}

export async function getAudit(
  auditId: string,
  token?: string
): Promise<AuditResult> {
  const res = await fetch(`${BASE}/api/audit/${auditId}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Audit not found");
  }
  return res.json();
}

export async function listAudits(token: string): Promise<AuditListItem[]> {
  const res = await fetch(`${BASE}/api/audits`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error("Failed to load audit history");
  }
  return res.json();
}

export async function deleteAudit(
  auditId: string,
  token: string
): Promise<void> {
  const res = await fetch(`${BASE}/api/audit/${auditId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error("Failed to delete audit");
  }
}

export interface ShareResponse {
  slug: string;
  url: string;
}

export async function shareAudit(
  auditId: string,
  token: string
): Promise<ShareResponse> {
  const res = await fetch(`${BASE}/api/audit/${auditId}/share`, {
    method: "POST",
    headers: authHeader(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to share audit");
  }
  return res.json();
}

export async function getPublicAudit(slug: string): Promise<AuditResult> {
  const res = await fetch(`${BASE}/api/public/audit/${slug}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Report not found");
  }
  return res.json();
}

export async function getUsage(token: string) {
  const res = await fetch(`${BASE}/api/billing/usage`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to load usage");
  return res.json();
}

export async function createCheckout(
  tier: string,
  token: string,
  successUrl: string,
  cancelUrl: string
) {
  const res = await fetch(`${BASE}/api/billing/upgrade`, {
    method: "POST",
    headers: authHeader(token),
    body: JSON.stringify({
      tier,
      success_url: successUrl,
      cancel_url: cancelUrl,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Checkout failed");
  }
  return res.json();
}

export async function login(
  email: string,
  password: string
): Promise<{ access_token: string; user_id: string; email: string; tier: string }> {
  const res = await fetch(`${BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Login failed");
  }
  return res.json();
}

export async function register(
  email: string,
  password: string
): Promise<{ access_token: string; user_id: string; email: string; tier: string }> {
  const res = await fetch(`${BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Registration failed");
  }
  return res.json();
}
