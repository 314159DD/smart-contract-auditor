"use client";

import { Check, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { createCheckout } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";

const PLANS = [
  {
    id: "free",
    name: "Free",
    price: "$0",
    period: "/month",
    description: "For curious developers",
    features: [
      "5 quick scans / month",
      "Solidity paste & upload",
      "Basic vulnerability detection",
      "Public report link",
    ],
    cta: "Get Started",
    highlight: false,
  },
  {
    id: "pro",
    name: "Pro",
    price: "$29",
    period: "/month",
    description: "For active builders",
    features: [
      "50 quick scans / month",
      "50 standard scans / month",
      "AI-powered deep analysis",
      "PDF report export",
      "Contract address import",
      "Multi-chain support",
      "Email on completion",
    ],
    cta: "Upgrade to Pro",
    highlight: true,
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: "$199",
    period: "/month",
    description: "For teams & protocols",
    features: [
      "Unlimited scans",
      "Deep audit mode (Claude AI)",
      "Economic attack vector analysis",
      "Priority processing",
      "PDF + custom branding",
      "Slack / webhook alerts",
      "Dedicated support",
    ],
    cta: "Contact Sales",
    highlight: false,
  },
] as const;

export function PricingTable() {
  const { user } = useAuth();
  const router = useRouter();

  const handleCta = async (planId: (typeof PLANS)[number]["id"]) => {
    if (planId === "free") {
      router.push("/auth/register");
      return;
    }
    if (planId === "enterprise") {
      window.location.href = "mailto:hello@contractauditor.app?subject=Enterprise";
      return;
    }
    if (!user) {
      router.push("/auth/login");
      return;
    }
    try {
      const { checkout_url } = await createCheckout(
        planId,
        user.token,
        `${window.location.origin}/dashboard?upgraded=1`,
        `${window.location.origin}/pricing`
      );
      window.location.href = checkout_url;
    } catch (err) {
      alert(String(err));
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
      {PLANS.map((plan) => (
        <div
          key={plan.id}
          className={cn(
            "relative rounded-2xl border p-6 flex flex-col gap-5",
            plan.highlight
              ? "border-green-600 bg-green-950/20 shadow-lg shadow-green-900/20"
              : "border-gray-700 bg-gray-900"
          )}
        >
          {plan.highlight && (
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
              <span className="flex items-center gap-1 bg-green-600 text-white text-xs font-semibold px-3 py-1 rounded-full">
                <Zap className="w-3 h-3" /> Most Popular
              </span>
            </div>
          )}

          <div>
            <h3 className="text-lg font-bold text-gray-100">{plan.name}</h3>
            <p className="text-gray-500 text-sm mt-0.5">{plan.description}</p>
          </div>

          <div className="flex items-end gap-1">
            <span className="text-4xl font-bold text-gray-100">{plan.price}</span>
            <span className="text-gray-500 mb-1">{plan.period}</span>
          </div>

          <ul className="space-y-2 flex-1">
            {plan.features.map((f) => (
              <li key={f} className="flex items-start gap-2 text-sm text-gray-300">
                <Check className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                {f}
              </li>
            ))}
          </ul>

          <button
            onClick={() => handleCta(plan.id)}
            className={cn(
              "w-full py-2.5 rounded-xl font-semibold text-sm transition-colors",
              plan.highlight
                ? "bg-green-600 hover:bg-green-500 text-white"
                : "bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700"
            )}
          >
            {plan.cta}
          </button>
        </div>
      ))}
    </div>
  );
}
