# AI Contract Auditor — Roadmap

**Status:** Phase 1 Complete, Phase 2 Complete, Phase 3 Complete (deployment prep done, pending env var config)

---

## Phase 1: Core Scanner (Weeks 1-3) — COMPLETE

- [x] Solidity AST parsing (slither-based, full function/variable/modifier/event extraction)
- [x] Common vulnerability detection — 10 static detectors implemented and tested
  - [x] Reentrancy (CRITICAL)
  - [x] Access control (HIGH)
  - [x] Integer overflow/underflow (HIGH/LOW depending on pragma)
  - [x] Unchecked call return values (MEDIUM)
  - [x] tx.origin authentication (HIGH)
  - [x] Unprotected selfdestruct (CRITICAL)
  - [x] Dangerous delegatecall patterns (HIGH)
  - [x] Block timestamp dependence (LOW)
  - [x] Gas limit / unbounded loop DoS (MEDIUM)
  - [x] Front-running vulnerability patterns (MEDIUM)
- [x] AI analysis layer (Claude-powered deep analysis with fix generation)
- [x] Report generation (JSON + Markdown + PDF via weasyprint)
- [x] CLI: `python -m src.audit scan <file.sol> --type quick/standard/deep`
- [x] Etherscan source fetcher (Ethereum, Polygon, Arbitrum, Base, Optimism)
- [x] 45 tests passing (parser + detector coverage)

### Sprint 1 Detail: `plan/tasks/sprint-1-core-scanner.md`

---

## Phase 2: Web Interface (Weeks 4-5) — COMPLETE

- [x] FastAPI backend with async audit processing
  - [x] `POST /api/audit` — submit contract, returns audit_id immediately
  - [x] `GET /api/audit/{id}` — poll for result (202 while processing)
  - [x] `GET /api/audits` — paginated audit history
  - [x] `DELETE /api/audit/{id}` — remove audit record
  - [x] Auth routes (Supabase JWT, Google OAuth)
  - [x] Billing routes (Stripe Checkout, Customer Portal, webhooks)
  - [x] JWT middleware + per-tier rate limiting
- [x] Next.js 15 frontend
  - [x] Landing page with contract upload (paste + drag-and-drop + address input)
  - [x] Report viewer (`/audit/[id]`) with risk gauge, findings, code snippets
  - [x] Dashboard (`/dashboard`) with audit history and usage meter
  - [x] Pricing page (`/pricing`) with Free/Pro/Enterprise comparison
  - [x] Auth pages (login, register)
  - [x] All UI components: ContractUpload, AddressInput, ReportViewer, FindingCard, SeverityBadge, RiskGauge, PricingTable, Navbar
- [x] Supabase schema (`supabase/schema.sql`)
- [x] Stripe payment integration (products + Checkout + webhooks)
- [x] Email notifications on audit completion (Resend)
- [x] PDF export + shareable public report URLs
- [x] End-to-end deployment config (Railway + Vercel) — deploying in Phase 3

### Sprint 2 Detail: `plan/tasks/sprint-2-web-interface.md`

---

## Phase 3: Launch (Weeks 6-8) — COMPLETE (deployment prep)

- [x] Deploy to Railway (backend) + Vercel (frontend)
  - [x] Backend Dockerfile with weasyprint system deps
  - [x] railway.json config (healthcheck on /health, restart on failure)
  - [x] .dockerignore to keep image lean
  - [x] .env.example files for backend + frontend
  - [x] frontend/vercel.json with API proxy rewrites
  - [x] Dockerfile: added solc-select for slither support
  - [x] CORS: added Vercel production + preview domains
  - [x] vercel.json: added API proxy rewrites to Railway
  - [x] Frontend: upgraded Next.js to 15.5.14, build passes (NODE_ENV=production)
  - [x] Core scanner pipeline complete (parser → detectors → AI → reports)
  - [ ] Set env vars in Railway + Vercel dashboards and deploy (manual step)
- [x] Alert webhook integration: high-severity findings POSTed to a configurable endpoint (SMA-12)
- [ ] Market to DeFi communities
- [ ] Partnerships with new protocol launches
- [ ] CI/CD integration for continuous auditing
