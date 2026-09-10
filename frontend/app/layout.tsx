import type { Metadata } from "next";
import { Syne, DM_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { ClientShell } from "@/components/ClientShell";

const syne = Syne({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ContractAudit AI — Smart Contract Security Scanner",
  description:
    "Scan Solidity smart contracts for reentrancy, access control issues, and 10+ vulnerability classes. Powered by static analysis and AI deep audit. Free quick scans available.",
  keywords: [
    "smart contract audit",
    "solidity security scanner",
    "smart contract vulnerability",
    "reentrancy detection",
    "AI contract audit",
    "solidity analyzer",
    "blockchain security",
    "defi security",
  ],
  openGraph: {
    title: "ContractAudit AI — Smart Contract Security Scanner",
    description:
      "Audit Solidity contracts in seconds. 10+ vulnerability detectors plus AI-powered deep analysis.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`dark ${syne.variable} ${dmSans.variable} ${jetbrains.variable}`}
    >
      <body className="min-h-screen bg-[#050505] text-[#e5e5e5] antialiased font-[family-name:var(--font-body)]">
        <ClientShell>{children}</ClientShell>
      </body>
    </html>
  );
}
