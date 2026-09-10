import type { Metadata } from "next";
import { HomePageClient } from "@/components/HomePageClient";

export const metadata: Metadata = {
  title: "ContractAudit AI — Smart Contract Security Scanner",
  description:
    "Scan Solidity smart contracts for reentrancy, access control, integer overflow, and 10+ vulnerability classes. Powered by static analysis and Claude AI deep audit. Free quick scans available.",
  keywords: [
    "smart contract audit",
    "solidity security scanner",
    "smart contract vulnerability",
    "reentrancy detection",
    "AI contract audit",
    "solidity analyzer",
    "blockchain security",
    "defi security",
    "contract audit tool",
  ],
  openGraph: {
    title: "ContractAudit AI — Smart Contract Security Scanner",
    description:
      "Audit Solidity contracts in seconds. 10+ vulnerability detectors plus AI-powered analysis.",
    type: "website",
  },
};

export default function HomePage() {
  return <HomePageClient />;
}
