"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { Finding } from "@/lib/api";
import { SeverityBadge } from "./SeverityBadge";

export function FindingCard({ finding }: { finding: Finding }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-800/50 transition-colors"
      >
        {open ? (
          <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
        )}
        <SeverityBadge severity={finding.severity} />
        <span className="font-medium text-gray-100 flex-1">{finding.title}</span>
        {finding.location && (
          <span className="text-xs text-gray-500 font-mono hidden sm:block">
            {finding.location}
          </span>
        )}
      </button>

      {open && (
        <div className="px-4 pb-4 pt-1 border-t border-gray-700 bg-gray-900/30 space-y-4">
          <p className="text-gray-300 text-sm leading-relaxed">
            {finding.description}
          </p>

          {finding.location && (
            <div>
              <span className="text-xs text-gray-500 uppercase tracking-wider">Location</span>
              <p className="font-mono text-xs text-yellow-300 mt-1">{finding.location}</p>
            </div>
          )}

          {finding.attack_scenario && (
            <div>
              <span className="text-xs text-gray-500 uppercase tracking-wider">Attack Scenario</span>
              <p className="text-sm text-orange-300 mt-1">{finding.attack_scenario}</p>
            </div>
          )}

          {finding.fix_before && (
            <div>
              <span className="text-xs text-gray-500 uppercase tracking-wider">Vulnerable Code</span>
              <pre className="mt-1 bg-red-950/30 border border-red-900/50 rounded p-3 text-xs text-red-300 font-mono overflow-x-auto whitespace-pre-wrap">
                {finding.fix_before}
              </pre>
            </div>
          )}

          {finding.fix_after && (
            <div>
              <span className="text-xs text-gray-500 uppercase tracking-wider">Fixed Code</span>
              <pre className="mt-1 bg-green-950/30 border border-green-900/50 rounded p-3 text-xs text-green-300 font-mono overflow-x-auto whitespace-pre-wrap">
                {finding.fix_after}
              </pre>
            </div>
          )}

          <div>
            <span className="text-xs text-gray-500 uppercase tracking-wider">Recommendation</span>
            <p className="text-sm text-gray-300 mt-1">{finding.recommendation}</p>
          </div>

          <div className="flex flex-wrap gap-4 text-xs text-gray-500">
            <span>Confidence: <span className="text-gray-400">{finding.confidence}</span></span>
            {finding.cwe_id && (
              <span>CWE: <span className="text-gray-400">{finding.cwe_id}</span></span>
            )}
            <span>Source: <span className="text-gray-400">{finding.source}</span></span>
          </div>
        </div>
      )}
    </div>
  );
}
