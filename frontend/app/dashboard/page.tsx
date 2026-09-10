"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Trash2,
  ExternalLink,
  RefreshCw,
  Shield,
  ArrowRight,
  AlertTriangle,
  FileSearch,
} from "lucide-react";
import { listAudits, deleteAudit, getUsage, type AuditListItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn, formatDate, riskColor, truncateAddress } from "@/lib/utils";

export default function DashboardPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [audits, setAudits] = useState<AuditListItem[]>([]);
  const [usage, setUsage] = useState<{
    tier: string;
    monthly_scans_used: number;
    monthly_scans_limit: number | null;
  } | null>(null);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.push("/auth/login");
      return;
    }

    Promise.all([
      listAudits(user.token).then(setAudits),
      getUsage(user.token).then(setUsage),
    ])
      .catch((e) => setError(String(e)))
      .finally(() => setFetching(false));
  }, [user, authLoading, router]);

  const handleDelete = async (auditId: string) => {
    if (!user) return;
    if (!confirm("Delete this audit?")) return;
    try {
      await deleteAudit(auditId, user.token);
      setAudits((prev) => prev.filter((a) => a.audit_id !== auditId));
    } catch (e) {
      alert(String(e));
    }
  };

  const handleRetry = () => {
    setError("");
    setFetching(true);
    if (user) {
      Promise.all([
        listAudits(user.token).then(setAudits),
        getUsage(user.token).then(setUsage),
      ])
        .catch((e) => setError(String(e)))
        .finally(() => setFetching(false));
    }
  };

  if (authLoading || fetching) {
    return (
      <div className="flex items-center justify-center py-24">
        <RefreshCw className="w-6 h-6 text-green-500 animate-spin" />
      </div>
    );
  }

  const isRateLimited =
    usage &&
    usage.monthly_scans_limit !== null &&
    usage.monthly_scans_used >= usage.monthly_scans_limit;

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-100">Dashboard</h1>
        <Link
          href="/scan"
          className="flex items-center gap-1.5 bg-green-700 hover:bg-green-600 text-white text-sm px-4 py-2 rounded-lg transition-colors"
        >
          + New Scan
        </Link>
      </div>

      {/* Usage meter */}
      {usage && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="text-sm text-gray-400">
                Plan:{" "}
                <span className="font-semibold text-gray-100 capitalize">{usage.tier}</span>
              </p>
            </div>
            <Link
              href="/pricing"
              className="text-xs text-green-400 hover:text-green-300"
            >
              Upgrade &rarr;
            </Link>
          </div>
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-gray-500">
              <span>Monthly scans used</span>
              <span>
                {usage.monthly_scans_used} /{" "}
                {usage.monthly_scans_limit ?? "\u221E"}
              </span>
            </div>
            {usage.monthly_scans_limit && (
              <div className="w-full bg-gray-800 rounded-full h-1.5">
                <div
                  className={cn(
                    "h-1.5 rounded-full transition-all",
                    isRateLimited ? "bg-red-500" : "bg-green-500"
                  )}
                  style={{
                    width: `${Math.min(
                      100,
                      (usage.monthly_scans_used / usage.monthly_scans_limit) * 100
                    )}%`,
                  }}
                />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Rate limit warning */}
      {isRateLimited && (
        <div className="bg-orange-950/30 border border-orange-800/50 rounded-xl p-5 flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="flex items-center gap-3 flex-1">
            <AlertTriangle className="w-5 h-5 text-orange-400 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-orange-300">
                Monthly scan limit reached
              </p>
              <p className="text-xs text-gray-500 mt-0.5">
                You&apos;ve used all {usage?.monthly_scans_limit} scans this month.
                Upgrade your plan for more scans and AI-powered audits.
              </p>
            </div>
          </div>
          <Link
            href="/pricing"
            className="flex items-center gap-1.5 bg-orange-600 hover:bg-orange-500 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors whitespace-nowrap"
          >
            Upgrade Plan
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-950/40 border border-red-800 rounded-lg flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-300 flex-1">{error}</p>
          <button
            onClick={handleRetry}
            className="flex items-center gap-1.5 text-sm text-red-300 hover:text-red-200 border border-red-800 hover:border-red-600 px-3 py-1.5 rounded-lg transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Retry
          </button>
        </div>
      )}

      {/* Audit list */}
      <div>
        <h2 className="text-lg font-semibold text-gray-200 mb-3">Audit History</h2>
        {audits.length === 0 ? (
          <div className="border border-gray-800 border-dashed rounded-xl py-16 px-6 text-center">
            <FileSearch className="w-12 h-12 text-gray-700 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-300 mb-2">
              No audits yet
            </h3>
            <p className="text-sm text-gray-500 max-w-sm mx-auto mb-6">
              Scan your first smart contract to find vulnerabilities before they reach mainnet.
            </p>
            <Link
              href="/scan"
              className="inline-flex items-center gap-2 bg-green-600 hover:bg-green-500 text-white font-semibold px-5 py-2.5 rounded-xl transition-colors"
            >
              <Shield className="w-4 h-4" />
              Scan Your First Contract
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        ) : (
          <div className="space-y-2">
            {audits.map((audit) => (
              <div
                key={audit.audit_id}
                className="flex items-center gap-4 bg-gray-900 border border-gray-800 hover:border-gray-700 rounded-xl px-4 py-3 transition-colors group"
              >
                {/* Status dot */}
                <div
                  className={cn(
                    "w-2 h-2 rounded-full flex-shrink-0",
                    audit.status === "complete"
                      ? "bg-green-500"
                      : audit.status === "failed"
                      ? "bg-red-500"
                      : "bg-yellow-500 animate-pulse"
                  )}
                />

                {/* Contract name */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-200 truncate">
                    {audit.contract_name ?? (audit.contract_address
                      ? truncateAddress(audit.contract_address)
                      : "Unnamed Contract")}
                  </p>
                  <div className="flex items-center gap-2">
                    <p className="text-xs text-gray-600">{formatDate(audit.timestamp)}</p>
                    {audit.status === "failed" && (
                      <span className="text-xs text-red-500 font-medium">Failed</span>
                    )}
                  </div>
                </div>

                {/* Risk score */}
                {audit.risk_score != null && (
                  <div className="text-right hidden sm:block">
                    <p className={cn("text-sm font-mono font-bold", riskColor(audit.risk_score))}>
                      {Math.round(audit.risk_score)}
                    </p>
                    <p className="text-xs text-gray-600">risk</p>
                  </div>
                )}

                {/* Verdict */}
                {audit.verdict && (
                  <p className="text-xs text-gray-400 hidden md:block max-w-32 truncate">
                    {audit.verdict}
                  </p>
                )}

                {/* Scan type */}
                <span className="text-xs font-mono text-gray-600 hidden sm:block">
                  {audit.scan_type}
                </span>

                {/* Actions */}
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Link
                    href={`/audit/${audit.audit_id}`}
                    className="p-1.5 text-gray-500 hover:text-gray-200 rounded"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </Link>
                  <button
                    onClick={() => handleDelete(audit.audit_id)}
                    className="p-1.5 text-gray-500 hover:text-red-400 rounded"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
