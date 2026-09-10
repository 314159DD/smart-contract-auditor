"use client";

import { useState } from "react";
import { Share2, Download, ExternalLink } from "lucide-react";
import type { AuditResult } from "@/lib/api";
import { RiskGauge } from "./RiskGauge";
import { SeverityBadge } from "./SeverityBadge";
import { FindingCard } from "./FindingCard";
import { cn, formatDate, truncateAddress } from "@/lib/utils";

type SeverityFilter = "ALL" | "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";

interface ReportViewerProps {
  audit: AuditResult;
  shareSlug?: string;
  onShare?: () => Promise<void>;
}

export function ReportViewer({ audit, shareSlug, onShare }: ReportViewerProps) {
  const [filter, setFilter] = useState<SeverityFilter>("ALL");
  const [copied, setCopied] = useState(false);

  const findings = audit.findings ?? [];
  const filtered =
    filter === "ALL"
      ? findings
      : findings.filter((f) => f.severity.toUpperCase() === filter);

  const copyShareLink = async () => {
    if (onShare) {
      await onShare();
    } else {
      const url = shareSlug
        ? `${window.location.origin}/report/${shareSlug}`
        : window.location.href;
      await navigator.clipboard.writeText(url);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadPdf = () => {
    window.open(`/api/audit/${audit.audit_id}/pdf`, "_blank");
  };

  const scanTypeBadge: Record<string, string> = {
    quick: "bg-gray-700 text-gray-300",
    standard: "bg-blue-900/60 text-blue-300",
    deep: "bg-purple-900/60 text-purple-300",
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">
            {audit.contract_name ?? "Contract Audit"}
          </h1>
          {audit.contract_address && (
            <p className="text-sm text-gray-500 font-mono mt-1">
              {truncateAddress(audit.contract_address)}
              {audit.chain && (
                <span className="ml-2 text-gray-600">on {audit.chain}</span>
              )}
            </p>
          )}
          <p className="text-xs text-gray-600 mt-1">{formatDate(audit.timestamp)}</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={copyShareLink}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg transition-all duration-200",
              copied
                ? "border-green-600 bg-green-950/40 text-green-300"
                : "border-gray-700 hover:border-gray-500 text-gray-300"
            )}
          >
            <Share2 className="w-4 h-4" />
            {copied ? "Copied!" : "Share"}
          </button>
          <button
            onClick={downloadPdf}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-gray-700 hover:border-gray-500 rounded-lg text-gray-300 transition-colors"
          >
            <Download className="w-4 h-4" />
            PDF
          </button>
        </div>
      </div>

      {/* Executive Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Risk Gauge */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col items-center">
          {audit.summary ? (
            <>
              <RiskGauge score={audit.summary.risk_score} />
              <p className="text-sm font-semibold text-gray-300 mt-2">
                {audit.summary.verdict}
              </p>
            </>
          ) : (
            <p className="text-gray-500 text-sm">No summary</p>
          )}
        </div>

        {/* Finding counts */}
        {audit.summary && (
          <div className="sm:col-span-2 bg-gray-900 border border-gray-800 rounded-xl p-4 grid grid-cols-3 gap-3">
            {(
              [
                { label: "Critical", count: audit.summary.critical, color: "text-red-400" },
                { label: "High", count: audit.summary.high, color: "text-orange-400" },
                { label: "Medium", count: audit.summary.medium, color: "text-yellow-400" },
                { label: "Low", count: audit.summary.low, color: "text-blue-400" },
                { label: "Info", count: audit.summary.info, color: "text-gray-400" },
                { label: "Total", count: audit.summary.total_findings, color: "text-gray-200" },
              ] as const
            ).map(({ label, count, color }) => (
              <div key={label} className="text-center">
                <p className={cn("text-2xl font-bold font-mono", color)}>{count}</p>
                <p className="text-xs text-gray-500 mt-0.5">{label}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Contract Info */}
      {audit.contract_info && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Contract Info
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
            <div>
              <p className="text-gray-500 text-xs">Compiler</p>
              <p className="text-gray-200 font-mono">{audit.contract_info.compiler_version}</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs">Functions</p>
              <p className="text-gray-200 font-mono">{audit.contract_info.function_count}</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs">State Vars</p>
              <p className="text-gray-200 font-mono">{audit.contract_info.state_variable_count}</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs">Lines</p>
              <p className="text-gray-200 font-mono">{audit.contract_info.line_count}</p>
            </div>
          </div>
        </div>
      )}

      {/* Findings */}
      {findings.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-100">Findings</h3>
            <div className="flex flex-wrap gap-1">
              {(["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"] as SeverityFilter[]).map(
                (f) => (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    className={cn(
                      "px-2 py-0.5 rounded text-xs font-mono transition-colors",
                      filter === f
                        ? "bg-green-700 text-white"
                        : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                    )}
                  >
                    {f}
                  </button>
                )
              )}
            </div>
          </div>
          <div className="space-y-2">
            {filtered.length === 0 ? (
              <p className="text-gray-500 text-sm text-center py-6">
                No {filter.toLowerCase()} findings
              </p>
            ) : (
              filtered.map((f, i) => <FindingCard key={i} finding={f} />)
            )}
          </div>
        </div>
      )}

      {/* Scan type + cost metadata */}
      <div className="flex flex-wrap gap-3 text-xs text-gray-600 border-t border-gray-800 pt-4">
        <span>
          Scan type:{" "}
          <span className={cn("px-1.5 py-0.5 rounded font-mono", scanTypeBadge[audit.scan_type] ?? "bg-gray-700 text-gray-300")}>
            {audit.scan_type}
          </span>
        </span>
        {audit.ai_cost_usd > 0 && (
          <span>AI cost: ${audit.ai_cost_usd.toFixed(4)}</span>
        )}
        {audit.scan_duration_seconds > 0 && (
          <span>Duration: {audit.scan_duration_seconds.toFixed(1)}s</span>
        )}
      </div>

      {/* Disclaimer */}
      <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-4 text-xs text-gray-500">
        <strong className="text-gray-400">Disclaimer:</strong> This report is provided for
        informational purposes only and does not constitute legal or financial advice. The
        findings represent the output of automated static analysis and AI-assisted review.
        No security audit can guarantee the absence of all vulnerabilities. Always consult a
        qualified security auditor before deploying contracts with significant value.
      </div>
    </div>
  );
}
