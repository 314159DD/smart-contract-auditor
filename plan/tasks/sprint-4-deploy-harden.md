# Sprint 4: Deploy, Harden & Polish — Contract Auditor

**Goal:** Deploy backend + frontend to production, harden security, fix edge cases, polish UX, add CI. By end of sprint the product is publicly accessible and processing real audits.

**Duration:** 1 week
**Status:** In Progress
**Depends On:** Sprint 3 (code complete, deployment config ready)

---

## Parallel Workstreams

### Workstream A: Backend Deploy & Harden (Agent 1)
### Workstream B: Frontend Polish & Deploy (Agent 2)
### Workstream C: Testing, QA & CI (Agent 3)

These three workstreams are **independent** and can run in parallel.

---

## Workstream A: Backend Deploy & Harden

**Agent:** Backend Engineer
**cwd:** `./`

### Task A.1: Verify Backend Runs Locally

- [ ] **A.1.1** Install dependencies: `pip install -r requirements.txt`
- [ ] **A.1.2** Verify `python -m src.audit scan tests/contracts/vulnerable_reentrancy.sol --type quick` works
- [ ] **A.1.3** Verify `uvicorn src.web.app:app --port 8000` starts without errors
- [ ] **A.1.4** Verify `GET /health` returns 200
- [ ] **A.1.5** Fix any import errors or missing deps

### Task A.2: Complete Email Service

- [ ] **A.2.1** Review `src/web/email.py` — implement if stub
- [ ] **A.2.2** Wire email sending into audit pipeline (on status=complete)
- [ ] **A.2.3** Add error handling (don't fail audit if email fails)

### Task A.3: Harden the Audit Pipeline

- [ ] **A.3.1** Add timeout to AI analysis (max 120s per pass, abort gracefully)
- [ ] **A.3.2** Add contract size validation (reject >10K lines for free tier, >50K lines for all tiers)
- [ ] **A.3.3** Sanitize Solidity input (strip null bytes, reject binary)
- [ ] **A.3.4** Add structured logging (`import logging`, log each pipeline step)
- [ ] **A.3.5** Ensure graceful error messages when slither/solc is not installed

### Task A.4: Verify Docker Build

- [ ] **A.4.1** Run `docker build -t contract-auditor .`
- [ ] **A.4.2** Run container, verify `/health` responds
- [ ] **A.4.3** Fix any build issues (system deps, solc path, etc.)

**Acceptance:** Backend starts locally, CLI scans a contract, Docker builds and runs, email service works.

---

## Workstream B: Frontend Polish & Deploy

**Agent:** Frontend Engineer
**cwd:** `./frontend`

### Task B.1: Verify Frontend Builds

- [ ] **B.1.1** Run `npm install && npm run build` — fix any TypeScript or build errors
- [ ] **B.1.2** Run `npm run dev` — verify all pages render without console errors
- [ ] **B.1.3** Check responsive layout (mobile/tablet/desktop)

### Task B.2: Landing Page Polish

- [ ] **B.2.1** Add SEO metadata (title, description, og:image)
- [ ] **B.2.2** Add "How it works" section (3 steps: Upload → Scan → Report)
- [ ] **B.2.3** Add social proof / stats section (placeholder: "X contracts scanned", "10 vulnerability detectors", "AI-powered analysis")
- [ ] **B.2.4** Add footer with links (Pricing, Dashboard, Terms, Privacy, Contact)
- [ ] **B.2.5** Ensure CTA buttons are prominent and clear

### Task B.3: Report Page Polish

- [ ] **B.3.1** Add "Copy Share URL" toast notification
- [ ] **B.3.2** Add loading skeleton while report is being fetched
- [ ] **B.3.3** Ensure code blocks in findings have syntax highlighting (or at least monospace)
- [ ] **B.3.4** Verify PDF download works end-to-end

### Task B.4: Error States & Edge Cases

- [ ] **B.4.1** Add proper error page for failed audits (show error message, retry button)
- [ ] **B.4.2** Handle network errors gracefully (show toast, not blank screen)
- [ ] **B.4.3** Add rate limit exceeded message (show upgrade CTA)
- [ ] **B.4.4** Handle empty dashboard state ("No audits yet — scan your first contract!")

**Acceptance:** `npm run build` passes, all pages render, landing page looks professional, error states handled.

---

## Workstream C: Testing, QA & CI

**Agent:** QA Engineer
**cwd:** `./`

### Task C.1: Run Existing Test Suite

- [ ] **C.1.1** Run `pytest tests/ -v` — record pass/fail counts
- [ ] **C.1.2** Fix any failing tests (update assertions if code changed since tests were written)
- [ ] **C.1.3** Add `pytest.ini` or `pyproject.toml` with test config

### Task C.2: Add Missing Test Coverage

- [ ] **C.2.1** Add integration test: full pipeline (parse → detect → report) for each sample contract
- [ ] **C.2.2** Add API test: `POST /api/audit` with valid Solidity returns audit_id
- [ ] **C.2.3** Add API test: `GET /api/audit/{id}` returns 202 then 200
- [ ] **C.2.4** Add edge case tests: empty input, invalid Solidity, oversized contract

### Task C.3: Add CI Pipeline

- [ ] **C.3.1** Create `.github/workflows/test.yml`:
  ```yaml
  - Install Python 3.12
  - pip install -r requirements.txt
  - pytest tests/ -v --tb=short
  ```
- [ ] **C.3.2** Create `.github/workflows/build-frontend.yml`:
  ```yaml
  - Install Node 20
  - cd frontend && npm install && npm run build
  ```

### Task C.4: Security Audit

- [ ] **C.4.1** Grep for hardcoded secrets/keys in source
- [ ] **C.4.2** Verify all user input is sanitized before passing to slither/subprocess
- [ ] **C.4.3** Verify rate limiting works (test with rapid requests)
- [ ] **C.4.4** Verify CORS only allows expected origins
- [ ] **C.4.5** Verify JWT auth middleware rejects invalid tokens

**Acceptance:** All tests pass, CI pipeline runs, no security issues found.

---

## Post-Sprint: Manual Steps (Owner)

These require manual action with credentials:

1. **Railway:** Create project, set env vars (ANTHROPIC_API_KEY, SUPABASE_URL/KEY, STRIPE keys, RESEND key), deploy
2. **Vercel:** Import frontend repo, set NEXT_PUBLIC_API_URL to Railway URL, deploy
3. **Supabase:** Run `supabase/schema.sql` in SQL editor
4. **Stripe:** Create products (Pro $29/mo, Enterprise $199/mo), copy price IDs to env
5. **Domain:** Point custom domain to Vercel (if desired)

---

## Sprint 4 Definition of Done

- [ ] Backend Docker image builds and runs
- [ ] Frontend `npm run build` passes
- [ ] All pytest tests pass
- [ ] CI pipeline configured
- [ ] Landing page polished with SEO, footer, how-it-works
- [ ] Error states handled in frontend
- [ ] Email notifications working
- [ ] No hardcoded secrets in source
- [ ] ROADMAP.md updated
