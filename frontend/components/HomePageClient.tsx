"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import {
  Shield,
  Search,
  FileText,
  Zap,
  Lock,
  AlertTriangle,
  ArrowRight,
  ChevronRight,
  Terminal,
  Cpu,
  Eye,
  Code2,
  Bug,
  Gauge,
  ShieldCheck,
  ShieldAlert,
  Layers,
  Workflow,
  Check,
  Sparkles,
  Clock,
} from "lucide-react";

/* ─── Animated Counter Hook ─── */
function useCountUp(target: number, duration = 2000, start = false) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!start) return;
    let startTime: number;
    const step = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      setCount(Math.floor(progress * target));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [target, duration, start]);
  return count;
}

/* ─── Intersection Observer Hook ─── */
function useInView(threshold = 0.2) {
  const ref = useRef<HTMLDivElement>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setInView(true);
          obs.disconnect();
        }
      },
      { threshold }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return { ref, inView };
}

/* ─── Typing Animation ─── */
function TypingText({ texts }: { texts: string[] }) {
  const [idx, setIdx] = useState(0);
  const [charIdx, setCharIdx] = useState(0);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    const current = texts[idx];
    const timeout = deleting ? 30 : 60;

    if (!deleting && charIdx === current.length) {
      const t = setTimeout(() => setDeleting(true), 2000);
      return () => clearTimeout(t);
    }
    if (deleting && charIdx === 0) {
      setDeleting(false);
      setIdx((i) => (i + 1) % texts.length);
      return;
    }

    const timer = setTimeout(() => {
      setCharIdx((c) => c + (deleting ? -1 : 1));
    }, timeout);
    return () => clearTimeout(timer);
  }, [charIdx, deleting, idx, texts]);

  return (
    <span className="text-terminal-green text-glow">
      {texts[idx].slice(0, charIdx)}
      <span className="inline-block w-[2px] h-[1em] bg-terminal-green align-middle animate-[typing-cursor_1s_step-end_infinite] ml-0.5" />
    </span>
  );
}

/* ─── Simulated Scan Animation ─── */
function ScanSimulation() {
  const [step, setStep] = useState(0);
  const [started, setStarted] = useState(false);

  const steps = [
    { label: "Parsing contract AST..." },
    { label: "Running reentrancy detector..." },
    { label: "Running access control check..." },
    { label: "Running integer overflow scan..." },
    { label: "Running unchecked calls detector..." },
    { label: "AI deep analysis (Claude Sonnet)..." },
    { label: "Generating report..." },
  ];

  useEffect(() => {
    if (!started) {
      const t = setTimeout(() => setStarted(true), 1500);
      return () => clearTimeout(t);
    }
    if (step < steps.length) {
      const delay = step === 5 ? 1800 : 400 + Math.random() * 300;
      const t = setTimeout(() => setStep((s) => s + 1), delay);
      return () => clearTimeout(t);
    }
  }, [step, started, steps.length]);

  return (
    <div className="terminal-window glow-green">
      <div className="terminal-header">
        <div className="terminal-dot bg-[#ff5f57]" />
        <div className="terminal-dot bg-[#febc2e]" />
        <div className="terminal-dot bg-[#28c840]" />
        <span className="ml-3 text-[11px] font-mono text-neutral-500">
          contractaudit --scan vault.sol --type deep
        </span>
      </div>
      <div className="p-4 sm:p-5 font-mono text-xs sm:text-[13px] space-y-1.5 min-h-[280px]">
        {!started && (
          <div className="text-neutral-600 animate-pulse">
            Initializing scanner...
          </div>
        )}
        {started &&
          steps.slice(0, step).map((s, i) => (
            <div
              key={i}
              className="flex items-center gap-2 animate-fade-in"
              style={{ animationDelay: `${i * 50}ms` }}
            >
              <span className="text-terminal-green">&#10003;</span>
              <span className="text-neutral-400">{s.label}</span>
              {i === 5 && (
                <span className="text-[#00d4ff] text-[10px] ml-auto opacity-70">
                  3 passes
                </span>
              )}
            </div>
          ))}

        {step === steps.length && (
          <div className="mt-4 pt-4 border-t border-[#1a1a1a] space-y-3 animate-fade-up">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-[#ff3e3e]" />
              <span className="text-white font-medium">
                3 vulnerabilities found
              </span>
            </div>
            <div className="space-y-1.5 ml-6">
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#ff3e3e]" />
                <span className="text-neutral-300 text-xs">
                  Reentrancy in withdraw()
                </span>
                <span className="ml-auto text-[10px] text-[#ff3e3e] font-medium uppercase">
                  Critical
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#ffb800]" />
                <span className="text-neutral-300 text-xs">
                  Missing access control on setFee()
                </span>
                <span className="ml-auto text-[10px] text-[#ffb800] font-medium uppercase">
                  High
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#00d4ff]" />
                <span className="text-neutral-300 text-xs">
                  Unchecked return in transfer()
                </span>
                <span className="ml-auto text-[10px] text-[#00d4ff] font-medium uppercase">
                  Low
                </span>
              </div>
            </div>
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-[#1a1a1a]">
              <span className="text-neutral-600 text-[11px]">
                Completed in 4.2s
              </span>
              <span className="text-terminal-green text-[11px] font-medium">
                Report ready &#8594;
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Vulnerability Code Block ─── */
function VulnCodeBlock() {
  return (
    <div className="relative font-mono text-xs sm:text-[13px] leading-relaxed">
      <div className="absolute left-0 top-0 bottom-0 w-px bg-gradient-to-b from-transparent via-[#ff3e3e]/40 to-transparent" />
      <pre className="pl-4 text-neutral-500 overflow-x-auto">
        <code>
          {`function `}
          <span className="text-white">withdraw</span>
          {`(uint amount) public {\n`}
          {`    require(balances[msg.sender] >= amount);\n`}
          <span className="bg-[#ff3e3e]/10 text-[#ff3e3e] block -ml-4 pl-4 border-l-2 border-[#ff3e3e]">
            {`    (bool ok,) = msg.sender.call{value: amount}("");`}
          </span>
          {`    require(ok);\n`}
          {`    balances[msg.sender] -= amount;  `}
          <span className="text-[#ff3e3e]">{"// \u2190 state after external call"}</span>
          {`\n}`}
        </code>
      </pre>
    </div>
  );
}

/* ═══════════════════════════════════════════ */
/* ─── Main Landing Page ─── */
/* ═══════════════════════════════════════════ */
export function HomePageClient() {
  const statsRef = useInView(0.3);
  const scansCount = useCountUp(12847, 2000, statsRef.inView);
  const vulnsCount = useCountUp(3291, 2000, statsRef.inView);
  const chainsCount = useCountUp(8, 1500, statsRef.inView);

  const detectors = [
    { name: "Reentrancy", severity: "critical", icon: Bug },
    { name: "Access Control", severity: "critical", icon: Lock },
    { name: "Integer Overflow", severity: "high", icon: AlertTriangle },
    { name: "Unchecked Calls", severity: "high", icon: ShieldAlert },
    { name: "tx.origin Auth", severity: "medium", icon: Eye },
    { name: "Delegatecall", severity: "critical", icon: Code2 },
    { name: "Timestamp Dep.", severity: "medium", icon: Clock },
    { name: "Gas Griefing", severity: "medium", icon: Gauge },
    { name: "Front-Running", severity: "high", icon: Zap },
    { name: "Self-Destruct", severity: "critical", icon: ShieldAlert },
  ];

  const severityColor: Record<string, string> = {
    critical: "text-[#ff3e3e] border-[#ff3e3e]/20 bg-[#ff3e3e]/5",
    high: "text-orange-400 border-orange-400/20 bg-orange-400/5",
    medium: "text-[#ffb800] border-[#ffb800]/20 bg-[#ffb800]/5",
  };

  return (
    <div className="relative overflow-hidden">
      {/* ═══════════ HERO ═══════════ */}
      <section className="relative min-h-[90vh] flex items-center bg-grid noise">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(0,255,65,0.06)_0%,_transparent_60%)]" />
        <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[#050505] to-transparent z-10" />

        <div className="relative z-20 max-w-6xl mx-auto px-4 sm:px-6 py-20 sm:py-28 w-full">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
            <div className="space-y-8">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[#1a1a1a] bg-[#0a0a0a] text-xs font-mono text-neutral-400 animate-fade-up">
                <span className="w-1.5 h-1.5 rounded-full bg-terminal-green animate-pulse" />
                10+ detectors &bull; AI-powered analysis
              </div>

              <h1 className="font-display font-extrabold text-4xl sm:text-5xl lg:text-[3.5rem] leading-[1.1] tracking-tight animate-fade-up delay-100">
                Find vulnerabilities
                <br />
                <TypingText
                  texts={[
                    "before hackers do.",
                    "before deployment.",
                    "before the exploit.",
                    "in seconds, not weeks.",
                  ]}
                />
              </h1>

              <p className="text-lg text-neutral-400 max-w-lg leading-relaxed animate-fade-up delay-200">
                Static analysis meets AI deep review. Scan Solidity contracts
                for reentrancy, access control flaws, and 10+ vulnerability
                classes in seconds.
              </p>

              <div className="flex flex-col sm:flex-row gap-3 animate-fade-up delay-300">
                <Link
                  href="/auth/login"
                  className="inline-flex items-center justify-center gap-2 bg-terminal-green text-black font-semibold px-6 py-3 rounded-lg hover:bg-[#00ff41]/90 transition-all btn-lift text-sm"
                >
                  <Zap className="w-4 h-4" />
                  Start Free Scan
                </Link>
                <Link
                  href="/pricing"
                  className="inline-flex items-center justify-center gap-2 border border-[#1a1a1a] text-neutral-300 hover:text-white hover:border-neutral-600 px-6 py-3 rounded-lg transition-all text-sm"
                >
                  View Pricing
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>

              <div className="flex items-center gap-6 text-xs text-neutral-600 animate-fade-up delay-400">
                <span className="flex items-center gap-1.5">
                  <Check className="w-3.5 h-3.5 text-terminal-green/60" />
                  Free tier
                </span>
                <span className="flex items-center gap-1.5">
                  <Check className="w-3.5 h-3.5 text-terminal-green/60" />
                  No credit card
                </span>
                <span className="flex items-center gap-1.5">
                  <Check className="w-3.5 h-3.5 text-terminal-green/60" />
                  PDF reports
                </span>
              </div>
            </div>

            <div className="animate-fade-up delay-300">
              <ScanSimulation />
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════ CHAIN BAR ═══════════ */}
      <section className="border-y border-[#1a1a1a] bg-[#0a0a0a]/50 py-5">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-wrap items-center justify-center gap-x-8 gap-y-2 text-[11px] font-mono text-neutral-600 tracking-wide">
          {["Ethereum", "BSC", "Polygon", "Arbitrum", "Optimism", "Base", "Avalanche", "Fantom"].map(
            (chain, i) => (
              <span key={i} className="hover:text-neutral-400 transition-colors">
                {chain}
              </span>
            )
          )}
        </div>
      </section>

      {/* ═══════════ PROBLEM ═══════════ */}
      <section className="py-20 sm:py-28">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="max-w-3xl mx-auto text-center space-y-6">
            <p className="font-mono text-xs text-[#ff3e3e] tracking-wider uppercase">
              The problem
            </p>
            <h2 className="font-display font-bold text-3xl sm:text-4xl tracking-tight">
              <span className="text-[#ff3e3e] text-glow">$3.8 billion</span>{" "}
              lost to smart contract exploits in 2024
            </h2>
            <p className="text-neutral-400 text-lg leading-relaxed">
              Manual audits cost $5K&ndash;$50K and take weeks. Most contracts ship
              without any security review. The gap between &ldquo;deployed&rdquo;
              and &ldquo;audited&rdquo; is where attackers live.
            </p>
          </div>

          <div className="mt-16 grid md:grid-cols-2 gap-6 items-start">
            <div className="terminal-window">
              <div className="terminal-header">
                <div className="terminal-dot bg-[#ff5f57]" />
                <div className="terminal-dot bg-[#febc2e]" />
                <div className="terminal-dot bg-[#28c840]" />
                <span className="ml-3 text-[11px] font-mono text-neutral-500">
                  Vault.sol &mdash; reentrancy vulnerability
                </span>
              </div>
              <div className="p-5">
                <VulnCodeBlock />
              </div>
            </div>

            <div className="space-y-4">
              <div className="border border-[#ff3e3e]/20 bg-[#ff3e3e]/5 rounded-xl p-5 space-y-3">
                <div className="flex items-center gap-2">
                  <Bug className="w-5 h-5 text-[#ff3e3e]" />
                  <span className="font-display font-bold text-white">
                    Classic Reentrancy
                  </span>
                  <span className="ml-auto text-[10px] font-mono text-[#ff3e3e] border border-[#ff3e3e]/20 px-1.5 py-0.5 rounded uppercase">
                    Critical
                  </span>
                </div>
                <p className="text-sm text-neutral-400 leading-relaxed">
                  External call on line 3 sends ETH before updating state on
                  line 5. An attacker can re-enter withdraw() and drain the vault.
                </p>
                <p className="text-sm text-terminal-green font-mono">
                  Fix: checks-effects-interactions pattern
                </p>
              </div>

              <div className="border border-[#1a1a1a] rounded-xl p-5 text-sm text-neutral-500">
                Our scanner catches this in{" "}
                <span className="text-terminal-green font-mono">0.3s</span>.
                The AI layer explains the risk and suggests the exact fix.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════ HOW IT WORKS ═══════════ */}
      <section className="py-20 sm:py-28 bg-[#0a0a0a]/30 border-y border-[#1a1a1a]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center space-y-4 mb-16">
            <p className="font-mono text-xs text-terminal-green tracking-wider uppercase">
              How it works
            </p>
            <h2 className="font-display font-bold text-3xl sm:text-4xl tracking-tight">
              Three layers of security analysis
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                step: "01",
                icon: Terminal,
                title: "Parse & Analyze",
                desc: "Upload Solidity source or paste a contract address. Our engine parses the AST and builds a complete control-flow graph.",
                detail: "Slither-powered parsing",
              },
              {
                step: "02",
                icon: Cpu,
                title: "Detect & Scan",
                desc: "10+ specialized detectors run in parallel — reentrancy, access control, integer overflow, unchecked calls, and more.",
                detail: "Static analysis + pattern matching",
              },
              {
                step: "03",
                icon: Sparkles,
                title: "AI Deep Review",
                desc: "AI performs multi-pass analysis, understanding business logic and finding subtle vulnerabilities that static tools miss.",
                detail: "3-pass analysis on deep scans",
              },
            ].map((item, i) => (
              <div
                key={i}
                className="relative border border-[#1a1a1a] rounded-2xl p-6 sm:p-8 bg-[#050505] card-hover group"
              >
                <div className="flex items-center gap-3 mb-5">
                  <span className="font-mono text-xs text-terminal-green/40 font-bold">
                    {item.step}
                  </span>
                  <div className="w-10 h-10 rounded-xl bg-terminal-green/5 border border-terminal-green/10 flex items-center justify-center group-hover:border-terminal-green/20 transition-colors">
                    <item.icon className="w-5 h-5 text-terminal-green/70" />
                  </div>
                </div>
                <h3 className="font-display font-bold text-lg text-white mb-2">
                  {item.title}
                </h3>
                <p className="text-sm text-neutral-400 leading-relaxed mb-4">
                  {item.desc}
                </p>
                <span className="text-[11px] font-mono text-neutral-600">
                  {item.detail}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════ DETECTORS ═══════════ */}
      <section className="py-20 sm:py-28">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center space-y-4 mb-16">
            <p className="font-mono text-xs text-terminal-green tracking-wider uppercase">
              Detection coverage
            </p>
            <h2 className="font-display font-bold text-3xl sm:text-4xl tracking-tight">
              10+ vulnerability detectors
            </h2>
            <p className="text-neutral-400 max-w-lg mx-auto">
              Covering the most exploited vulnerability classes in DeFi
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {detectors.map((d, i) => (
              <div
                key={i}
                className={`border rounded-xl p-4 text-center space-y-2 transition-all hover:scale-[1.02] cursor-default ${severityColor[d.severity]}`}
              >
                <d.icon className="w-5 h-5 mx-auto opacity-70" />
                <p className="text-xs font-medium">{d.name}</p>
                <p className="text-[10px] uppercase tracking-wider opacity-60">
                  {d.severity}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════ STATS ═══════════ */}
      <section
        ref={statsRef.ref}
        className="py-16 border-y border-[#1a1a1a] bg-[#0a0a0a]/30"
      >
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-3 gap-8 text-center">
            {[
              { value: scansCount.toLocaleString(), label: "Contracts Scanned" },
              { value: vulnsCount.toLocaleString(), label: "Vulnerabilities Found" },
              { value: chainsCount.toString(), label: "Chains Supported" },
            ].map((stat, i) => (
              <div key={i} className="space-y-1">
                <p className="font-mono font-bold text-3xl sm:text-4xl text-white tabular-nums">
                  {stat.value}
                  <span className="text-terminal-green">+</span>
                </p>
                <p className="text-xs sm:text-sm text-neutral-500">
                  {stat.label}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════ FEATURES ═══════════ */}
      <section className="py-20 sm:py-28">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center space-y-4 mb-16">
            <p className="font-mono text-xs text-terminal-green tracking-wider uppercase">
              Features
            </p>
            <h2 className="font-display font-bold text-3xl sm:text-4xl tracking-tight">
              Everything you need to ship secure contracts
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-4">
            {[
              {
                icon: FileText,
                title: "PDF & Markdown Reports",
                desc: "Professional audit reports ready to share with investors, teammates, or on-chain governance.",
              },
              {
                icon: Search,
                title: "Etherscan Integration",
                desc: "Paste a contract address — we fetch verified source code from Etherscan across 8 chains.",
              },
              {
                icon: Layers,
                title: "Quick & Deep Scans",
                desc: "Quick scan for fast feedback. Deep scan runs 3-pass AI analysis for production contracts.",
              },
              {
                icon: Shield,
                title: "Shareable Public Links",
                desc: "Generate a public report link to prove your contract's security to users and auditors.",
              },
              {
                icon: Terminal,
                title: "CLI Tool",
                desc: "Scan contracts from your terminal. Integrate into CI/CD pipelines and pre-commit hooks.",
              },
              {
                icon: Workflow,
                title: "Severity Classification",
                desc: "Every finding rated Critical to Info with CWE references and specific remediation steps.",
              },
            ].map((f, i) => (
              <div
                key={i}
                className="border border-[#1a1a1a] rounded-2xl p-6 bg-[#050505] card-hover group"
              >
                <div className="w-9 h-9 rounded-lg bg-terminal-green/5 border border-terminal-green/10 flex items-center justify-center mb-4 group-hover:border-terminal-green/20 transition-colors">
                  <f.icon className="w-4 h-4 text-terminal-green/60" />
                </div>
                <h3 className="font-display font-semibold text-white mb-2">
                  {f.title}
                </h3>
                <p className="text-sm text-neutral-500 leading-relaxed">
                  {f.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════ PRICING ═══════════ */}
      <section className="py-20 sm:py-28 bg-[#0a0a0a]/30 border-y border-[#1a1a1a]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center space-y-4 mb-16">
            <p className="font-mono text-xs text-terminal-green tracking-wider uppercase">
              Pricing
            </p>
            <h2 className="font-display font-bold text-3xl sm:text-4xl tracking-tight">
              Start free, scale as you ship
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            {/* Free */}
            <div className="border border-[#1a1a1a] rounded-2xl p-6 bg-[#050505] space-y-5">
              <div>
                <h3 className="font-display font-bold text-white">Free</h3>
                <p className="text-xs text-neutral-500 mt-1">For exploring</p>
              </div>
              <div className="flex items-baseline gap-1">
                <span className="font-body font-extrabold text-3xl text-white">$0</span>
                <span className="text-sm text-neutral-600">/month</span>
              </div>
              <ul className="space-y-2.5 text-sm text-neutral-400">
                {["3 quick scans per day", "Basic vulnerability detection", "Markdown reports", "Community support"].map(
                  (f, i) => (
                    <li key={i} className="flex items-center gap-2">
                      <Check className="w-3.5 h-3.5 text-neutral-600 shrink-0" />
                      {f}
                    </li>
                  )
                )}
              </ul>
              <Link
                href="/auth/login"
                className="block text-center text-sm font-medium border border-[#1a1a1a] hover:border-neutral-600 text-neutral-300 py-2.5 rounded-lg transition-colors"
              >
                Get Started
              </Link>
            </div>

            {/* Pro */}
            <div className="relative border border-terminal-green/20 rounded-2xl p-6 bg-[#050505] glow-green space-y-5">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-terminal-green text-black text-[10px] font-bold font-mono uppercase tracking-wider rounded-full">
                Most Popular
              </div>
              <div>
                <h3 className="font-display font-bold text-white">Pro</h3>
                <p className="text-xs text-neutral-500 mt-1">For DeFi teams</p>
              </div>
              <div className="flex items-baseline gap-1">
                <span className="font-body font-extrabold text-3xl text-white">$29</span>
                <span className="text-sm text-neutral-600">/month</span>
              </div>
              <ul className="space-y-2.5 text-sm text-neutral-400">
                {[
                  "25 audits per month",
                  "Deep scan (3-pass AI)",
                  "PDF reports",
                  "Email delivery",
                  "Shareable public links",
                  "Priority queue",
                ].map((f, i) => (
                  <li key={i} className="flex items-center gap-2">
                    <Check className="w-3.5 h-3.5 text-terminal-green shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href="/auth/login"
                className="block text-center text-sm font-bold bg-terminal-green text-black py-2.5 rounded-lg hover:bg-[#00ff41]/90 transition-colors btn-lift"
              >
                Start Pro Trial
              </Link>
            </div>

            {/* Enterprise */}
            <div className="border border-[#1a1a1a] rounded-2xl p-6 bg-[#050505] space-y-5">
              <div>
                <h3 className="font-display font-bold text-white">Enterprise</h3>
                <p className="text-xs text-neutral-500 mt-1">For organizations</p>
              </div>
              <div className="flex items-baseline gap-1">
                <span className="font-body font-extrabold text-3xl text-white">$99</span>
                <span className="text-sm text-neutral-600">/month</span>
              </div>
              <ul className="space-y-2.5 text-sm text-neutral-400">
                {[
                  "Unlimited audits",
                  "API access",
                  "Team dashboard",
                  "Custom integrations",
                  "Dedicated support",
                  "SLA guarantee",
                ].map((f, i) => (
                  <li key={i} className="flex items-center gap-2">
                    <Check className="w-3.5 h-3.5 text-neutral-600 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href="/auth/login"
                className="block text-center text-sm font-medium border border-[#1a1a1a] hover:border-neutral-600 text-neutral-300 py-2.5 rounded-lg transition-colors"
              >
                Contact Sales
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════ CTA ═══════════ */}
      <section className="py-20 sm:py-28">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="relative border border-[#1a1a1a] rounded-3xl p-8 sm:p-14 bg-[#0a0a0a] overflow-hidden">
            <div className="absolute inset-0 bg-grid opacity-50" />
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(0,255,65,0.04)_0%,_transparent_60%)]" />

            <div className="relative z-10 text-center space-y-6 max-w-2xl mx-auto">
              <h2 className="font-display font-bold text-3xl sm:text-4xl tracking-tight">
                Secure your contracts before you deploy
              </h2>
              <p className="text-neutral-400 text-lg">
                Start with 3 free scans per day. No credit card required.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                <Link
                  href="/auth/login"
                  className="inline-flex items-center gap-2 bg-terminal-green text-black font-semibold px-8 py-3.5 rounded-lg hover:bg-[#00ff41]/90 transition-all btn-lift text-sm"
                >
                  <Shield className="w-4 h-4" />
                  Start Free Scan
                </Link>
                <Link
                  href="/pricing"
                  className="inline-flex items-center gap-2 text-neutral-400 hover:text-white text-sm transition-colors"
                >
                  Compare plans
                  <ChevronRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════ FOOTER ═══════════ */}
      <footer className="border-t border-[#1a1a1a] py-12">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="grid sm:grid-cols-4 gap-8">
            <div className="sm:col-span-2 space-y-3">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-terminal-green" />
                <span className="font-display font-bold text-sm text-white">
                  ContractAudit AI
                </span>
              </div>
              <p className="text-xs text-neutral-600 leading-relaxed max-w-sm">
                Automated smart contract security scanning powered by static
                analysis and AI deep review.
              </p>
              <p className="text-[10px] font-mono text-neutral-700">
                &copy; {new Date().getFullYear()} Full Circle Solutions. All
                rights reserved.
              </p>
            </div>

            <div className="space-y-3">
              <p className="text-[11px] font-mono text-neutral-500 uppercase tracking-wider">
                Product
              </p>
              <div className="space-y-2">
                {[
                  { label: "Pricing", href: "/pricing" },
                  { label: "Dashboard", href: "/dashboard" },
                  { label: "Get Started", href: "/auth/login" },
                ].map((link, i) => (
                  <Link
                    key={i}
                    href={link.href}
                    className="block text-sm text-neutral-600 hover:text-neutral-400 transition-colors"
                  >
                    {link.label}
                  </Link>
                ))}
              </div>
            </div>

            <div className="space-y-3">
              <p className="text-[11px] font-mono text-neutral-500 uppercase tracking-wider">
                Legal
              </p>
              <div className="space-y-2">
                {[
                  { label: "Terms of Service", href: "/terms" },
                  { label: "Privacy Policy", href: "/privacy" },
                  { label: "Contact", href: "mailto:support@contractauditor.app" },
                ].map((link, i) => (
                  <Link
                    key={i}
                    href={link.href}
                    className="block text-sm text-neutral-600 hover:text-neutral-400 transition-colors"
                  >
                    {link.label}
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
