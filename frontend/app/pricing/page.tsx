import { PricingTable } from "@/components/PricingTable";

export default function PricingPage() {
  return (
    <div className="px-4 py-16 min-h-screen">
      <div className="max-w-5xl mx-auto text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-100 mb-4">
          Simple, transparent pricing
        </h1>
        <p className="text-gray-400 text-lg">
          Start free, upgrade when you need deeper analysis
        </p>
      </div>
      <PricingTable />

      <div className="max-w-2xl mx-auto mt-14 text-center text-sm text-gray-500">
        <p>All plans include the liability disclaimer on every report.</p>
        <p className="mt-1">
          Questions?{" "}
          <a
            href="mailto:hello@contractauditor.app"
            className="text-green-400 hover:underline"
          >
            hello@contractauditor.app
          </a>
        </p>
      </div>
    </div>
  );
}
