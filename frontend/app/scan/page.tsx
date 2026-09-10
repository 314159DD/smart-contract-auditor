"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Shield, Zap, Search, AlertCircle } from "lucide-react";
import { ContractUpload } from "@/components/ContractUpload";
import { AddressInput } from "@/components/AddressInput";
import { submitAudit, type ScanType } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

export default function ScanPage() {
  const { user } = useAuth();
  const router = useRouter();

  const [mode, setMode] = useState<"upload" | "address">("upload");
  const [source, setSource] = useState("");
  const [addressData, setAddressData] = useState<{ address: string; chain: string } | null>(null);
  const [scanType, setScanType] = useState<ScanType>("quick");
  const [contractName, setContractName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const canSubmit = mode === "upload" ? source.trim().length > 0 : addressData !== null;

  const handleAddressSubmit = async (address: string, chain: string) => {
    setAddressData({ address, chain });
    setSubmitting(true);
    setError("");
    try {
      const result = await submitAudit(
        { address, chain, scan_type: scanType, contract_name: contractName || undefined },
        user?.token
      );
      router.push(`/audit/${result.audit_id}`);
    } catch (e) {
      setError(String(e).replace("Error: ", ""));
      setSubmitting(false);
    }
  };

  const handleSubmit = async () => {
    if (!canSubmit || submitting || mode !== "upload") return;
    setSubmitting(true);
    setError("");
    try {
      const result = await submitAudit(
        { source, scan_type: scanType, contract_name: contractName || undefined },
        user?.token
      );
      router.push(`/audit/${result.audit_id}`);
    } catch (e) {
      setError(String(e).replace("Error: ", ""));
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <Shield className="w-5 h-5 text-terminal-green" />
          <h1 className="text-2xl font-display font-bold text-white">New Scan</h1>
        </div>
        <p className="text-neutral-500 text-sm">
          Upload a Solidity file or paste contract source to scan for vulnerabilities.
        </p>
      </div>

      {/* Mode toggle */}
      <div className="flex gap-1 p-1 bg-surface-2 border border-surface-5 rounded-xl mb-6 w-fit">
        <button
          onClick={() => setMode("upload")}
          className={cn(
            "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
            mode === "upload"
              ? "bg-terminal-green/10 text-terminal-green border border-terminal-green/20"
              : "text-neutral-500 hover:text-neutral-300"
          )}
        >
          <Zap className="w-3.5 h-3.5" />
          Upload / Paste
        </button>
        <button
          onClick={() => setMode("address")}
          className={cn(
            "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
            mode === "address"
              ? "bg-terminal-green/10 text-terminal-green border border-terminal-green/20"
              : "text-neutral-500 hover:text-neutral-300"
          )}
        >
          <Search className="w-3.5 h-3.5" />
          Contract Address
        </button>
      </div>

      {/* Input area */}
      <div className="bg-surface-1 border border-surface-5 rounded-xl p-6 mb-4">
        {mode === "upload" ? (
          <ContractUpload value={source} onChange={(s) => setSource(s)} />
        ) : (
          <AddressInput onSubmit={handleAddressSubmit} loading={submitting} />
        )}
      </div>

      {/* Options */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        {/* Scan type */}
        <div>
          <label className="block text-xs font-mono text-neutral-500 mb-2 uppercase tracking-wider">
            Scan Type
          </label>
          <div className="flex gap-1 p-1 bg-surface-2 border border-surface-5 rounded-lg">
            {(["quick", "standard", "deep"] as ScanType[]).map((t) => (
              <button
                key={t}
                onClick={() => setScanType(t)}
                disabled={!user && t !== "quick"}
                className={cn(
                  "flex-1 py-1.5 rounded-md text-xs font-medium transition-all capitalize",
                  scanType === t
                    ? "bg-terminal-green/10 text-terminal-green border border-terminal-green/20"
                    : "text-neutral-500 hover:text-neutral-300 disabled:opacity-30 disabled:cursor-not-allowed"
                )}
              >
                {t}
              </button>
            ))}
          </div>
          {!user && (
            <p className="text-xs text-neutral-600 mt-1">Standard & deep require an account</p>
          )}
        </div>

        {/* Contract name (optional) */}
        <div>
          <label className="block text-xs font-mono text-neutral-500 mb-2 uppercase tracking-wider">
            Contract Name <span className="text-neutral-700">(optional)</span>
          </label>
          <input
            type="text"
            value={contractName}
            onChange={(e) => setContractName(e.target.value)}
            placeholder="e.g. Vault, MyToken"
            className="w-full bg-surface-2 border border-surface-5 rounded-lg px-3 py-2 text-sm text-neutral-200 placeholder-neutral-700 focus:outline-none focus:border-terminal-green/30 font-mono"
          />
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-start gap-2 p-3 bg-red-500/5 border border-red-500/20 rounded-lg mb-4 text-sm text-red-400">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          {error}
        </div>
      )}

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!canSubmit || submitting}
        className={cn(
          "w-full flex items-center justify-center gap-2 py-3 rounded-xl font-medium text-sm transition-all btn-lift",
          canSubmit && !submitting
            ? "bg-terminal-green/10 hover:bg-terminal-green/15 text-terminal-green border border-terminal-green/20 hover:border-terminal-green/30"
            : "bg-surface-2 text-neutral-600 border border-surface-5 cursor-not-allowed"
        )}
      >
        {submitting ? (
          <>
            <span className="w-4 h-4 border-2 border-terminal-green/30 border-t-terminal-green rounded-full animate-spin" />
            Submitting...
          </>
        ) : (
          <>
            <Shield className="w-4 h-4" />
            Run Scan
          </>
        )}
      </button>

      <p className="text-center text-xs text-neutral-700 mt-3">
        {user ? (
          <>Scan type: <span className="text-neutral-500 font-mono">{scanType}</span></>
        ) : (
          <>Free quick scan — <a href="/auth/register" className="text-terminal-green hover:underline">create account</a> for standard &amp; deep scans</>
        )}
      </p>
    </div>
  );
}
