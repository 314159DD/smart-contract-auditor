import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function truncateAddress(addr: string, chars = 6): string {
  if (addr.length <= chars * 2 + 2) return addr;
  return `${addr.slice(0, chars + 2)}...${addr.slice(-chars)}`;
}

export function formatDate(iso?: string): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(iso));
}

export function riskColor(score: number): string {
  if (score >= 80) return "text-red-500";
  if (score >= 50) return "text-orange-400";
  if (score >= 20) return "text-yellow-400";
  return "text-green-400";
}

export function verdictColor(verdict: string): string {
  const v = verdict.toLowerCase();
  if (v.includes("critical") || v.includes("high risk")) return "text-red-500";
  if (v.includes("medium")) return "text-orange-400";
  if (v.includes("low")) return "text-yellow-400";
  return "text-green-400";
}
