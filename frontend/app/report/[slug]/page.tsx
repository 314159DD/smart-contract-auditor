/**
 * Public shared report page — accessible without auth.
 * Fetches audit by slug from GET /api/report/{slug}
 */
import { notFound } from "next/navigation";
import { ReportViewer } from "@/components/ReportViewer";
import type { AuditResult } from "@/lib/api";

async function getSharedReport(slug: string): Promise<AuditResult | null> {
  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) throw new Error("NEXT_PUBLIC_API_URL is not set");
    const res = await fetch(`${apiUrl}/api/public/audit/${slug}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function SharedReportPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const audit = await getSharedReport(slug);
  if (!audit) notFound();

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-4 text-xs text-gray-600 text-center">
        Shared public report — read only
      </div>
      <ReportViewer audit={audit} shareSlug={slug} />
    </div>
  );
}
