# Sprint 3: Launch — AI Contract Auditor

**Goal:** Complete the core scanning pipeline (parser → detectors → AI analysis → report), wire it to the API, add email + PDF + sharing, then deploy to Railway + Vercel.

**Status:** Not Started
**Depends On:** Sprint 2 (API backend + frontend scaffolding complete)

> **Important:** The audit found that `src/parser/`, `src/detectors/`, `src/ai/`, `src/reports/` directories exist but key implementation files may be stubs or missing. Before starting each task, check what's actually in each directory. Complete what exists, implement what's missing.

---

## Task 3.1: Verify and Complete the Solidity Parser

**File:** `src/parser/solidity.py`

- [ ] **3.1.1** Open `src/parser/` — list all files. Check if `solidity.py` is a stub or fully implemented.
- [ ] **3.1.2** If stub: implement `SolidityParser` that uses slither to parse a `.sol` file into an AST-like structure:
  ```python
  class SolidityParser:
      def parse(self, source_code: str) -> ParsedContract:
          # Write source to temp file
          # Run slither-analyze
          # Return functions, state vars, modifiers, events, inheritance
  ```
- [ ] **3.1.3** If fully implemented: write a quick smoke test — parse a simple ERC20 contract and confirm functions/variables are extracted correctly.
- [ ] **3.1.4** Add `src/parser/test_parser.py` with at least 2 test cases (valid contract, invalid Solidity).

**Acceptance:** `from src.parser.solidity import SolidityParser; SolidityParser().parse(erc20_source)` returns a populated `ParsedContract`.

---

## Task 3.2: Verify and Complete the Static Vulnerability Detectors

**Directory:** `src/detectors/`

- [ ] **3.2.1** List all files in `src/detectors/`. Identify which detectors are implemented vs stubbed.
- [ ] **3.2.2** For each missing detector, implement it. Required set:
  - `reentrancy.py` — check for state changes after external calls
  - `access_control.py` — unprotected admin functions (no `onlyOwner` or modifier)
  - `integer_overflow.py` — SafeMath missing (pre-Solidity 0.8) or unchecked blocks
  - `unchecked_return.py` — `.call()` return value not checked
  - `tx_origin.py` — `tx.origin` used for authentication
  - `selfdestruct.py` — unprotected `selfdestruct()`
  - `delegatecall.py` — dangerous `delegatecall` to user-supplied address
  - `timestamp_dependence.py` — `block.timestamp` used in critical logic
  - `gas_limit.py` — unbounded loops or `transfer()`/`send()` in loops
  - `front_running.py` — price-sensitive operations without slippage protection
- [ ] **3.2.3** Each detector must implement:
  ```python
  class ReentrancyDetector:
      severity = "CRITICAL"
      def detect(self, parsed: ParsedContract) -> list[Finding]:
          # Returns list of Finding(severity, title, description, line, recommendation)
  ```
- [ ] **3.2.4** Register all detectors in `src/detectors/__init__.py` for easy import.

**Acceptance:** Each detector returns `[]` for a clean contract, and ≥1 `Finding` for a vulnerable contract.

---

## Task 3.3: Verify and Complete the AI Analysis Layer

**File:** `src/ai/analyzer.py`

- [ ] **3.3.1** Check if `src/ai/analyzer.py` exists and is implemented or a stub.
- [ ] **3.3.2** If stub/missing: implement `AIAnalyzer` using Claude API:
  ```python
  class AIAnalyzer:
      def analyze(self, source_code: str, static_findings: list[Finding]) -> AIAnalysis:
          # Build prompt:
          # - Contract source code
          # - Static detector findings
          # - Ask Claude to: identify additional vulnerabilities,
          #   rate severity, generate fix recommendations,
          #   assess overall security posture (CRITICAL/HIGH/MEDIUM/LOW/SAFE)
          # Return AIAnalysis(overall_risk, ai_findings, fix_suggestions, summary)
  ```
- [ ] **3.3.3** Implement retry logic (up to 3 retries on rate limit / API error).
- [ ] **3.3.4** Cache analysis by contract hash in `data/ai_cache/` (24h TTL) to avoid re-analyzing unchanged contracts.

**Acceptance:** `AIAnalyzer().analyze(source, findings)` returns `AIAnalysis` with `overall_risk` and `ai_findings` populated.

---

## Task 3.4: Verify and Complete Report Generation

**File:** `src/reports/generator.py`

- [ ] **3.4.1** Check `src/reports/` — list all files, determine what's implemented.
- [ ] **3.4.2** Implement `ReportGenerator`:
  ```python
  class ReportGenerator:
      def generate_json(self, audit: AuditResult) -> dict: ...
      def generate_markdown(self, audit: AuditResult) -> str: ...
      def generate_pdf(self, audit: AuditResult) -> bytes:
          # Use weasyprint to render HTML → PDF
          # weasyprint is already in requirements.txt
  ```
- [ ] **3.4.3** HTML template for PDF: `src/reports/templates/report.html`
  - Show: contract name, audit date, overall risk score (gauge), findings list with severity badges, code snippets, fix recommendations
  - Style: dark theme, severity color coding (red=critical, orange=high, yellow=medium, blue=low)
- [ ] **3.4.4** Wire report generator to the API — `GET /api/audit/{id}/pdf` should return the PDF bytes with `Content-Type: application/pdf`.

**Acceptance:** `ReportGenerator().generate_pdf(audit_result)` returns valid PDF bytes that open correctly in a browser.

---

## Task 3.5: Wire the Full Audit Pipeline to the API

**File:** `src/web/routes/audit.py`

The API accepts contracts but the scanning logic was not connected. Wire it end-to-end.

- [ ] **3.5.1** In `POST /api/audit`, after accepting the request:
  ```python
  # Background task flow:
  # 1. parser.parse(source_code)          → ParsedContract
  # 2. [detector.detect(parsed) for d in detectors]  → list[Finding]
  # 3. ai_analyzer.analyze(source, findings)          → AIAnalysis
  # 4. report_generator.generate_json(result)         → dict
  # 5. Store in Supabase audits table
  # 6. Update status: pending → scanning → analyzing → complete
  ```
- [ ] **3.5.2** Confirm `GET /api/audit/{id}` returns 202 while processing, 200 with full report when complete.
- [ ] **3.5.3** Add error handling: if slither fails (invalid Solidity), return clear error message in the audit result (don't crash the server).

---

## Task 3.6: Supabase Schema

**File:** `supabase/schema.sql`

Check what's in `supabase/` — if schema.sql exists but is incomplete, add the missing tables.

- [ ] **3.6.1** Required tables (create if missing):
  ```sql
  -- Audit history
  CREATE TABLE audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),  -- null for anonymous
    contract_address TEXT,
    contract_source TEXT NOT NULL,
    chain TEXT DEFAULT 'ethereum',
    scan_type TEXT DEFAULT 'quick',
    status TEXT DEFAULT 'pending',  -- pending, scanning, analyzing, complete, failed
    result JSONB,
    is_public BOOLEAN DEFAULT false,
    public_slug TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
  );

  -- Usage tracking (for tier limits)
  CREATE TABLE usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    month TEXT NOT NULL,  -- '2026-03'
    scan_count INTEGER DEFAULT 0,
    UNIQUE(user_id, month)
  );

  -- User tiers (synced from Stripe webhook)
  CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id),
    tier TEXT DEFAULT 'free',  -- free, pro, enterprise
    stripe_customer_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
  );
  ```
- [ ] **3.6.2** Add RLS policies:
  - Users can only read/write their own audits
  - Public audits (`is_public = true`) are readable by anyone
- [ ] **3.6.3** Run schema in Supabase project (instructions in README).

---

## Task 3.7: Email Notifications (Resend)

**File:** `src/web/services/email.py`

- [ ] **3.7.1** Install: add `resend` to requirements.txt
- [ ] **3.7.2** Implement `EmailService`:
  ```python
  class EmailService:
      def send_audit_complete(self, to_email: str, audit_id: str, report: AuditResult):
          # Send email with:
          # - Overall risk level
          # - Count by severity (X critical, Y high, Z medium)
          # - Link to full report: {FRONTEND_URL}/audit/{audit_id}
  ```
- [ ] **3.7.3** Trigger from audit pipeline when status transitions to `complete`.
- [ ] **3.7.4** Only send if user is authenticated (anonymous scans don't get emails).
- [ ] **3.7.5** Add `RESEND_API_KEY` and `EMAIL_FROM` to .env.example (already there — just implement the service).

---

## Task 3.8: Shareable Public Report URLs

**Files:** `src/web/routes/audit.py`, `frontend/src/app/report/[slug]/`

- [ ] **3.8.1** Add `POST /api/audit/{id}/share` endpoint:
  - Generates a short slug (nanoid or UUID prefix)
  - Sets `is_public = true` and `public_slug` in Supabase
  - Returns `{url: "{FRONTEND_URL}/report/{slug}"}`
- [ ] **3.8.2** Add `GET /api/public/audit/{slug}` (no auth required):
  - Returns full report for Pro/Enterprise users' shared audits
  - Returns summary-only for free tier (hide detailed findings)
- [ ] **3.8.3** Frontend: Share button on `/audit/[id]` page → copies URL to clipboard.
- [ ] **3.8.4** Frontend: `/report/[slug]` page already exists — wire it to `GET /api/public/audit/{slug}`.

---

## Task 3.9: Deploy to Railway + Vercel

**Note:** Dockerfile, railway.json, and .env.example already exist. Just verify and finalize.

- [ ] **3.9.1** Verify Dockerfile builds: `docker build -t contract-auditor .`
  - Fix any build errors (slither may need extra system deps)
  - Note: slither requires solc — add to Dockerfile: `RUN pip install solc-select && solc-select install 0.8.19 && solc-select use 0.8.19`
- [ ] **3.9.2** Verify frontend builds: `cd frontend && npm install && npm run build`
  - Fix any TypeScript or import errors
- [ ] **3.9.3** Confirm vercel.json rewrites `/api/*` to the correct Railway backend URL.
- [ ] **3.9.4** Update CORS in `src/web/app.py` to include production frontend URL.
- [ ] **3.9.5** Update `plan/ROADMAP.md`: mark Sprint 3 complete, record Railway + Vercel URLs.

---

## Acceptance Criteria (Full Sprint = MVP)

- [ ] End-to-end audit works: submit Solidity → get JSON report with findings within 60 seconds
- [ ] PDF download works via `GET /api/audit/{id}/pdf`
- [ ] Email notification sent on audit completion (authenticated users)
- [ ] Shareable public URL generates and renders correctly
- [ ] Supabase schema applied, RLS active
- [ ] `docker build` passes
- [ ] `npm run build` passes
- [ ] ROADMAP.md updated, sprint marked complete
