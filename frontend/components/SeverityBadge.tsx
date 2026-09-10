import { cn } from "@/lib/utils";

const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: "bg-red-900/60 text-red-300 border border-red-700",
  HIGH: "bg-orange-900/60 text-orange-300 border border-orange-700",
  MEDIUM: "bg-yellow-900/60 text-yellow-300 border border-yellow-700",
  LOW: "bg-blue-900/60 text-blue-300 border border-blue-700",
  INFO: "bg-gray-700/60 text-gray-300 border border-gray-600",
};

export function SeverityBadge({
  severity,
  className,
}: {
  severity: string;
  className?: string;
}) {
  const s = severity.toUpperCase();
  const style = SEVERITY_STYLES[s] ?? SEVERITY_STYLES.INFO;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded px-2 py-0.5 text-xs font-semibold font-mono tracking-wider",
        style,
        className
      )}
    >
      {s}
    </span>
  );
}
