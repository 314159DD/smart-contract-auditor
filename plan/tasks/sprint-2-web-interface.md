# Sprint 2: Web Interface — Contract Auditor

**Goal:** Build the web frontend that lets users upload contracts, view reports, and manage their audit history. Implement the freemium model: free quick scans to generate leads, paid tiers for deep audits.

**Duration:** 2 weeks
**Status:** Not Started
**Depends On:** Sprint 1 (core scanner producing reports)

---

## Task 2.1: API Backend

**Input:** Core scanner from Sprint 1, user authentication requirements
**Output:** REST API serving audit requests, report retrieval, and user management

### Subtasks

- [ ] **2.1.1** Set up FastAPI application:
  ```
  src/web/
  ├── app.py              # FastAPI application factory
  ├── routes/
  │   ├── audit.py        # POST /audit, GET /audit/{id}, GET /audits
  │   ├── auth.py         # POST /auth/register, POST /auth/login
  │   └── billing.py      # GET /usage, POST /upgrade
  ├── middleware/
  │   ├── auth.py         # JWT authentication middleware
  │   └── rate_limit.py   # Per-user rate limiting
  ├── models/
  │   ├── user.py         # User model
  │   ├── audit.py        # Audit request/response models
  │   └── billing.py      # Usage/tier models
  └── database.py         # Supabase client setup
  ```
- [ ] **2.1.2** Implement audit endpoints:
  - `POST /api/audit` — Submit contract for scanning
    - Input: Solidity source OR contract address + chain
    - Input: scan_type (quick/standard/deep)
    - Output: audit_id (async processing)
  - `GET /api/audit/{id}` — Get audit result
    - Output: AuditReport (JSON) or 202 if still processing
  - `GET /api/audits` — List user's audit history
    - Output: paginated list of past audits
  - `DELETE /api/audit/{id}` — Delete an audit from history
- [ ] **2.1.3** Implement async audit processing:
  - Accept audit request, return audit_id immediately
  - Process in background (queue-based or thread pool)
  - Update status: pending → scanning → analyzing → complete/failed
  - Webhook or polling for completion
- [ ] **2.1.4** Implement user authentication:
  - Supabase Auth (email/password, Google OAuth)
  - JWT tokens for API access
  - Anonymous quick scans (no auth required, rate limited by IP)
- [ ] **2.1.5** Implement tier-based access control:
  ```python
  TIERS = {
      "free": {"scans_per_month": 5, "scan_types": ["quick"], "max_contract_size": 500},
      "pro": {"scans_per_month": 50, "scan_types": ["quick", "standard"], "max_contract_size": 5000},
      "enterprise": {"scans_per_month": -1, "scan_types": ["quick", "standard", "deep"], "max_contract_size": -1}
  }
  ```
- [ ] **2.1.6** Implement rate limiting:
  - Free: 5 scans/month, 1 concurrent scan
  - Pro: 50 scans/month, 5 concurrent scans
  - Enterprise: unlimited
  - Anonymous: 3 quick scans/day by IP

**Acceptance Criteria:**
- `POST /api/audit` accepts Solidity source and returns audit_id within 1 second
- `GET /api/audit/{id}` returns report when complete, 202 when processing
- Free tier users are blocked after 5 scans/month with clear upgrade message
- Anonymous quick scans work without authentication
- JWT authentication works with Supabase Auth

---

## Task 2.2: Frontend Web Application

**Input:** API backend, UI/UX requirements
**Output:** Next.js web app for contract upload, report viewing, and account management

### Subtasks

- [ ] **2.2.1** Set up Next.js 15 project:
  ```
  frontend/
  ├── app/
  │   ├── page.tsx              # Landing page with upload form
  │   ├── audit/[id]/page.tsx   # Audit report viewer
  │   ├── dashboard/page.tsx    # User audit history
  │   ├── pricing/page.tsx      # Pricing tiers
  │   └── layout.tsx
  ├── components/
  │   ├── ContractUpload.tsx    # Drag-and-drop + paste Solidity
  │   ├── AddressInput.tsx      # Contract address + chain selector
  │   ├── ReportViewer.tsx      # Formatted audit report
  │   ├── FindingCard.tsx       # Individual vulnerability display
  │   ├── SeverityBadge.tsx     # CRITICAL/HIGH/MEDIUM/LOW badges
  │   ├── RiskGauge.tsx         # Visual risk score (0-100)
  │   └── PricingTable.tsx      # Tier comparison
  ├── lib/
  │   ├── api.ts               # API client
  │   └── supabase.ts          # Supabase client
  └── public/
  ```
- [ ] **2.2.2** Build landing page / upload flow:
  - Hero: "AI-Powered Smart Contract Security" with upload CTA
  - Two input modes: paste Solidity OR enter contract address
  - Drag-and-drop file upload for .sol files
  - Scan type selector (quick = free, standard = pro, deep = enterprise)
  - "Scan Now" button → shows progress → redirects to report
- [ ] **2.2.3** Build report viewer:
  - Executive summary with risk score gauge
  - Findings list sortable/filterable by severity
  - Each finding shows: title, severity badge, description, code snippet, fix suggestion
  - "Export PDF" button
  - "Share Report" link (public read-only URL)
- [ ] **2.2.4** Build dashboard:
  - List of past audits with contract name, date, risk score, verdict
  - Quick actions: view report, re-scan, delete
  - Usage meter (X of Y scans used this month)
- [ ] **2.2.5** Build pricing page:
  - Three tiers: Free / Pro ($29/mo) / Enterprise ($199/mo)
  - Feature comparison table
  - Stripe Checkout integration for upgrades
- [ ] **2.2.6** Implement authentication UI:
  - Sign up / Sign in with Supabase Auth
  - Google OAuth button
  - Email verification flow

**Acceptance Criteria:**
- User can paste Solidity, click "Scan", and see a report within 60 seconds
- User can enter a contract address and get a report from Etherscan source
- Report viewer renders all findings with code snippets and fix suggestions
- Risk gauge visually shows 0-100 score with color coding
- Dashboard shows audit history with correct usage tracking
- Pricing page displays tiers with working Stripe Checkout

---

## Task 2.3: Report Sharing & PDF Export

**Input:** Completed audit reports
**Output:** Shareable public URLs and downloadable PDF reports

### Subtasks

- [ ] **2.3.1** Implement public report URLs:
  - Generate unique slug for each report
  - Public read-only page at `/report/{slug}`
  - No authentication required to view shared reports
  - Owner can toggle sharing on/off
- [ ] **2.3.2** Implement PDF generation:
  - Use weasyprint or puppeteer for PDF rendering
  - Professional audit report format:
    - Cover page with contract name, date, auditor branding
    - Executive summary with risk score
    - Detailed findings with code and fixes
    - Methodology section
    - Disclaimer
  - Download button on report viewer
- [ ] **2.3.3** Implement report notifications:
  - Email notification when audit completes (Resend or SendGrid)
  - Include risk score summary in email
  - Link to full report

**Acceptance Criteria:**
- Shared report URL is accessible without authentication
- PDF export produces a professional-looking document
- Email notification arrives within 1 minute of audit completion
- PDF includes all findings, code snippets, and fix suggestions

---

## Task 2.4: Stripe Payment Integration

**Input:** Pricing tiers, Stripe account
**Output:** Working subscription billing for Pro and Enterprise tiers

### Subtasks

- [ ] **2.4.1** Set up Stripe products and prices:
  - Pro: $29/month or $290/year
  - Enterprise: $199/month or $1990/year
  - Free: no Stripe product needed
- [ ] **2.4.2** Implement Stripe Checkout:
  - "Upgrade" button → Stripe Checkout session → redirect back
  - Handle checkout.session.completed webhook
  - Update user tier in Supabase on successful payment
- [ ] **2.4.3** Implement Stripe Customer Portal:
  - Manage subscription (upgrade/downgrade/cancel)
  - View invoices and payment history
  - Update payment method
- [ ] **2.4.4** Implement webhook handlers:
  - `checkout.session.completed` → activate subscription
  - `customer.subscription.updated` → update tier
  - `customer.subscription.deleted` → downgrade to free
  - `invoice.payment_failed` → notify user, grace period

**Acceptance Criteria:**
- User can upgrade from Free to Pro via Stripe Checkout
- Tier change reflects immediately in scan limits
- Subscription cancellation downgrades to Free at period end
- Failed payment triggers email notification
- Customer portal allows self-service subscription management

---

## Sprint 2 Definition of Done

- [ ] API serves audit requests with async processing and status polling
- [ ] Web frontend allows upload/paste → scan → view report flow
- [ ] Free tier limits enforced (5 quick scans/month)
- [ ] Pro/Enterprise tiers unlocked via Stripe subscription
- [ ] Reports are shareable via public URL and downloadable as PDF
- [ ] Email notifications sent on audit completion
- [ ] Dashboard shows audit history and usage metrics
- [ ] All code committed, frontend deployed to Vercel, backend to Railway
