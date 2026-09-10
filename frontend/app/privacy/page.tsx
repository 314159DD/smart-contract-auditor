import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy — ContractAudit AI",
};

export default function PrivacyPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-16">
      <h1 className="text-3xl font-display font-bold text-white mb-2">Privacy Policy</h1>
      <p className="text-neutral-500 font-mono text-sm mb-12">Last updated: March 2026</p>

      <div className="space-y-10 text-neutral-300 leading-relaxed">
        <section>
          <h2 className="text-lg font-semibold text-white mb-3">1. Information We Collect</h2>
          <ul className="space-y-2 list-disc list-inside text-neutral-400">
            <li><strong className="text-neutral-300">Account data:</strong> Email address and encrypted password (via Supabase Auth)</li>
            <li><strong className="text-neutral-300">Audit data:</strong> Solidity source code or contract addresses you submit for scanning</li>
            <li><strong className="text-neutral-300">Usage data:</strong> Number of scans, scan types, timestamps</li>
            <li><strong className="text-neutral-300">Billing data:</strong> Subscription status managed by Stripe — we do not store card numbers</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-white mb-3">2. How We Use Your Data</h2>
          <ul className="space-y-2 list-disc list-inside text-neutral-400">
            <li>To provide and improve the scanning service</li>
            <li>To send audit result notifications via email</li>
            <li>To enforce rate limits and tier quotas</li>
            <li>To process payments and manage subscriptions</li>
          </ul>
          <p className="mt-3 text-neutral-400">We do not sell your data to third parties. We do not use your submitted contract code for AI training.</p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-white mb-3">3. Data Storage</h2>
          <p>Your data is stored in Supabase (PostgreSQL) hosted on AWS infrastructure in the EU region. Audit results are retained for 90 days by default. You can delete your audits at any time from the dashboard.</p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-white mb-3">4. Third-Party Services</h2>
          <ul className="space-y-2 list-disc list-inside text-neutral-400">
            <li><strong className="text-neutral-300">Supabase</strong> — database and authentication</li>
            <li><strong className="text-neutral-300">Stripe</strong> — payment processing</li>
            <li><strong className="text-neutral-300">OpenRouter / Anthropic</strong> — AI analysis (contract code is sent for analysis)</li>
            <li><strong className="text-neutral-300">Resend</strong> — transactional email delivery</li>
            <li><strong className="text-neutral-300">Etherscan</strong> — fetching verified on-chain contract source</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-white mb-3">5. Shared Reports</h2>
          <p>If you generate a public share link for an audit, that report becomes accessible to anyone with the link. You can revoke sharing at any time from the audit page.</p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-white mb-3">6. Your Rights (GDPR)</h2>
          <p>If you are in the EU/EEA, you have the right to:</p>
          <ul className="mt-2 space-y-1 list-disc list-inside text-neutral-400">
            <li>Access the personal data we hold about you</li>
            <li>Request correction or deletion of your data</li>
            <li>Object to processing or request restriction</li>
            <li>Data portability</li>
          </ul>
          <p className="mt-3">To exercise these rights, email <a href="mailto:privacy@contractauditor.app" className="text-terminal-green hover:underline">privacy@contractauditor.app</a></p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-white mb-3">7. Cookies</h2>
          <p>We use only functional cookies required for authentication (session tokens stored in localStorage). We do not use tracking or advertising cookies.</p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-white mb-3">8. Contact</h2>
          <p>Privacy questions: <a href="mailto:privacy@contractauditor.app" className="text-terminal-green hover:underline">privacy@contractauditor.app</a></p>
        </section>
      </div>
    </div>
  );
}
