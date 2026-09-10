"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2, AlertCircle, RefreshCw, ArrowLeft } from "lucide-react";
import { getAudit, shareAudit, type AuditResult } from "@/lib/api";
import { ReportViewer } from "@/components/ReportViewer";
import { useAuth } from "@/lib/auth";

const POLL_INTERVAL_MS = 2500;

function StatusMessage({ status }: { status: string }) {
  const messages: Record<string, string> = {
    pending: "Queued...",
    scanning: "Running static analysis...",
    analyzing: "AI is analyzing vulnerabilities...",
  };
  return (
    <div className="flex flex-col items-center gap-4 py-24 text-center">
      <Loader2 className="w-8 h-8 text-green-500 animate-spin" />
      <p className="text-gray-300 font-medium">{messages[status] ?? "Processing..."}</p>
      <p className="text-gray-600 text-sm">This may take up to 60 seconds for standard scans</p>
    </div>
  );
}

function ReportSkeleton() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6 animate-pulse">
      {/* Header skeleton */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div className="space-y-3">
          <div className="h-7 w-64 bg-gray-800 rounded-lg" />
          <div className="h-4 w-40 bg-gray-800/60 rounded" />
          <div className="h-3 w-28 bg-gray-800/40 rounded" />
        </div>
        <div className="flex gap-2">
          <div className="h-9 w-24 bg-gray-800 rounded-lg" />
          <div className="h-9 w-20 bg-gray-800 rounded-lg" />
        </div>
      </div>

      {/* Summary skeleton */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 h-40" />
        <div className="sm:col-span-2 bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="grid grid-cols-3 gap-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="text-center space-y-2">
                <div className="h-8 w-10 bg-gray-800 rounded mx-auto" />
                <div className="h-3 w-14 bg-gray-800/60 rounded mx-auto" />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Contract info skeleton */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 h-20" />

      {/* Findings skeleton */}
      <div className="space-y-3">
        <div className="h-6 w-32 bg-gray-800 rounded" />
        {[...Array(3)].map((_, i) => (
          <div key={i} className="border border-gray-700 rounded-lg p-4 h-14" />
        ))}
      </div>
    </div>
  );
}

export default function AuditPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const router = useRouter();
  const [audit, setAudit] = useState<AuditResult | null>(null);
  const [error, setError] = useState("");
  const [shareSlug, setShareSlug] = useState<string | undefined>();
  const [retrying, setRetrying] = useState(false);

  useEffect(() => {
    if (!id) return;

    let cancelled = false;

    const poll = async () => {
      try {
        const result = await getAudit(id, user?.token);
        if (cancelled) return;
        setAudit(result);
        if (result.status === "complete" || result.status === "failed") return;
        setTimeout(poll, POLL_INTERVAL_MS);
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
    };

    poll();
    return () => { cancelled = true; };
  }, [id, user?.token]);

  const onShare = useCallback(async () => {
    if (!id || !user?.token) return;
    try {
      const result = await shareAudit(id, user.token);
      setShareSlug(result.slug);
      await navigator.clipboard.writeText(result.url);
    } catch {
      // Fall back to copying current URL
      await navigator.clipboard.writeText(window.location.href);
    }
  }, [id, user?.token]);

  const handleRetry = () => {
    setRetrying(true);
    router.push("/");
  };

  if (error) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <AlertCircle className="w-10 h-10 text-red-500 mx-auto mb-4" />
        <h2 className="text-lg font-semibold text-gray-100 mb-2">Something went wrong</h2>
        <p className="text-red-400 text-sm mb-6">{error}</p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            onClick={handleRetry}
            className="inline-flex items-center justify-center gap-2 bg-green-600 hover:bg-green-500 text-white font-semibold px-5 py-2.5 rounded-xl transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Try Again
          </button>
          <Link
            href="/dashboard"
            className="inline-flex items-center justify-center gap-2 border border-gray-700 hover:border-gray-500 text-gray-300 px-5 py-2.5 rounded-xl transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Dashboard
          </Link>
        </div>
      </div>
    );
  }

  if (!audit) {
    return <ReportSkeleton />;
  }

  if (audit.status === "failed") {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <AlertCircle className="w-10 h-10 text-red-500 mx-auto mb-4" />
        <h2 className="text-lg font-semibold text-gray-100 mb-2">Audit Failed</h2>
        {audit.error && (
          <p className="text-gray-400 text-sm mb-2 max-w-md mx-auto">{audit.error}</p>
        )}
        <p className="text-gray-600 text-xs mb-6">
          This can happen if the contract has import errors or uses an unsupported compiler version.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            onClick={handleRetry}
            disabled={retrying}
            className="inline-flex items-center justify-center gap-2 bg-green-600 hover:bg-green-500 disabled:bg-gray-700 text-white font-semibold px-5 py-2.5 rounded-xl transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${retrying ? "animate-spin" : ""}`} />
            Scan Again
          </button>
          <Link
            href="/dashboard"
            className="inline-flex items-center justify-center gap-2 border border-gray-700 hover:border-gray-500 text-gray-300 px-5 py-2.5 rounded-xl transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Dashboard
          </Link>
        </div>
      </div>
    );
  }

  if (audit.status !== "complete") {
    return <StatusMessage status={audit.status} />;
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <ReportViewer audit={audit} shareSlug={shareSlug} onShare={onShare} />
    </div>
  );
}
