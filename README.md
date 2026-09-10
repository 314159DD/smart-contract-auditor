# Smart Contract Auditor

Automated security scanning for Solidity smart contracts. Static analysis catches the known vulnerability classes in seconds, then a multi-pass AI review goes after the things pattern matching cannot see: business-logic flaws, economic attack vectors, and centralization risk. Every finding ships with a severity, a confidence score, and a before/after fix.

[![Tests](https://github.com/314159DD/smart-contract-auditor/actions/workflows/test.yml/badge.svg)](https://github.com/314159DD/smart-contract-auditor/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![Next.js 15](https://img.shields.io/badge/Next.js-15-black?logo=next.js)

Built as a complete SaaS: FastAPI backend, Next.js 15 frontend, Supabase auth, Stripe subscriptions, shareable HTML reports, PDF export, and a CLI for local or CI use.

---

## How it works

```
 Solidity source ─┐
                  ├─► Parser (Slither AST) ─► 10 static detectors ─┐
 Chain address ───┘        │                                        │
   (7 chains)              │                                        ▼
                           │                              AI review (1 or 3 passes)
                           │                              business logic, economics,
                           │                              centralization, fix diffs
                           │                                        │
                           └────────────────► Merger ◄──────────────┘
                                                │
                              dedupe, cross-reference confidence, rank
                                                │
                                  ┌─────────────┼─────────────┐
                                  ▼             ▼             ▼
                              Markdown        JSON        HTML / PDF
```

Three scan depths trade time for coverage:

| Scan | What runs | Typical time |
|------|-----------|--------------|
| `quick` | Static detectors only | seconds |
| `standard` | Static + single-pass AI review | ~30 s |
| `deep` | Static + three-pass AI review (discovery, exploit reasoning, fix synthesis) | ~2 min |

## Static detectors

| Detector | Severity | Catches |
|----------|----------|---------|
| Reentrancy | CRITICAL | External calls before state updates, missing ReentrancyGuard |
| Access control | CRITICAL | Unprotected state-changing functions, missing ownership checks |
| Selfdestruct | CRITICAL | Unprotected `selfdestruct` |
| Delegatecall | CRITICAL | Dangerous `delegatecall` targets and storage collisions |
| Integer overflow | HIGH | Arithmetic in pre-0.8.0 contracts and `unchecked` blocks |
| Unchecked call | HIGH | Ignored return values on external calls |
| Front-running | HIGH | Commit-reveal violations, price-manipulation vectors |
| tx.origin auth | MEDIUM | Authentication via `tx.origin` instead of `msg.sender` |
| Timestamp dependence | MEDIUM | `block.timestamp` in critical logic |
| Gas limit / DoS | MEDIUM | Unbounded loops, push-over-pull anti-patterns |

## AI review

The AI layer runs on top of the static results, not instead of them. It receives the source plus the static findings and is asked for what static analysis structurally cannot find:

- Business-logic vulnerabilities specific to this contract
- Economic attacks: flash loans, oracle manipulation, sandwiching
- Centralization risk: admin keys, upgrade paths, kill switches
- A concrete before/after code fix for every finding
- A confidence score that is cross-referenced against the static results, so AI-only findings are labelled as such

Models are called through OpenRouter, so the backing model is a config value (`AI_MODEL`), not a code change.

## Reports

- **Markdown**: severity table, code snippets, fix suggestions
- **JSON**: structured output for API consumers and CI gates
- **HTML**: shareable via a public link with a deterministic slug
- **PDF**: audit-style document with executive summary and disclaimer, delivered by email on request

## Supported chains

Verified sources can be fetched by address from Ethereum, Polygon, Arbitrum, Base, Optimism, BSC, and Avalanche.

---

## Quick start

### Backend

```bash
pip install -r requirements.txt
cp .env.example .env    # set OPENROUTER_API_KEY at minimum; see Configuration
uvicorn src.web.app:app --reload --port 8000
```

### CLI

```bash
# Static analysis only
python -m src.audit scan contract.sol --type quick

# Static + AI, written to a Markdown report
python -m src.audit scan contract.sol --type standard --output report.md

# Deep scan of a deployed contract fetched from the chain explorer
python -m src.audit scan --address 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 --chain ethereum --type deep
```

### Frontend

```bash
cd frontend
npm install
npm run dev     # http://localhost:3000, proxies /api/* to the backend
```

---

## Configuration

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENROUTER_API_KEY` | Yes | AI review |
| `AI_MODEL` | No | OpenRouter model id (default `anthropic/claude-sonnet-4-6`) |
| `SUPABASE_URL`, `SUPABASE_KEY` | Yes | Auth and audit history |
| `ETHERSCAN_API_KEY` | No | Higher rate limits when fetching by address |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | Yes | Subscriptions |
| `RESEND_API_KEY`, `EMAIL_FROM` | No | Email delivery of reports |
| `ALERT_WEBHOOK_URL` | No | Receives a POST for every CRITICAL/HIGH finding (Discord, Slack, anything HTTP) |
| `FRONTEND_URL` | No | Used in share links and emails |
| `SECRET_KEY` | Yes | Session signing |
| `APP_ENV` | No | `development` or `production` |

The full list with examples is in [`.env.example`](.env.example).

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/audit` | Submit source or an address for scanning |
| `GET` | `/api/audit/{id}` | Audit status and results |
| `GET` | `/api/audits` | The current user's audits |
| `POST` | `/api/audit/{id}/share` | Enable sharing, returns the public slug |
| `GET` | `/api/report/{slug}` | Public report by slug |
| `GET` | `/api/audit/{id}/pdf` | PDF download |
| `POST` | `/api/billing/checkout` | Stripe checkout session |
| `POST` | `/api/billing/webhook` | Stripe webhook (signature verified) |
| `GET` | `/health` | Health check |

Interactive docs are served at `/docs` when the backend is running.

## Tiers

| | Anonymous | Free | Pro | Enterprise |
|---|---|---|---|---|
| Scans | 3 quick / day per IP | 5 / month | 50 / month | Unlimited |
| Scan depth | quick | quick | quick, standard | quick, standard, deep |
| Max contract size | | 500 lines | 5,000 lines | Unlimited |
| PDF reports, share links, email delivery | -- | -- | Yes | Yes |

Limits are enforced in backend middleware (per-IP daily limit for anonymous scans, per-tier scan type, monthly quota, and source-size gates). Stripe subscriptions move a user between tiers via signature-verified webhooks.

---

## Testing

154 test cases across integration, API, and security suites. The security suite is regression-style: it fails if a secret pattern appears in source, if a `.env` is committed, if user input can reach a shell, if SQL is built with string formatting, if CORS accepts an unknown origin, or if a bad or expired JWT gets past auth.

```bash
pytest                    # everything
pytest -m integration     # parse -> detect -> report pipeline
pytest -m api             # endpoint contracts
pytest -m security        # security regression tests
```

CI runs the backend suite and a production build of the frontend on every push and pull request.

## Deploy

- **Backend**: `railway.json` and `Dockerfile` are included. Point a Railway (or any container) service at this repo and set the variables above.
- **Frontend**: `frontend/vercel.json` proxies `/api/*` to the backend. Replace `YOUR-BACKEND-HOST` with your backend URL and import `frontend/` into Vercel.
- **Database**: `supabase/schema.sql` creates the audits table and row-level security policies.

## Project structure

```
src/
  parser/         Solidity parsing on top of Slither
  detectors/      10 static detectors, one file each, shared base class
  ai/             OpenRouter client, prompts, and the 1-pass / 3-pass analyzer
  reports/        Merger (dedupe + confidence cross-reference) and JSON / MD / HTML / PDF generators
  etherscan/      Verified-source fetcher for 7 chains
  integrations/   Alert webhook for high-severity findings
  web/            FastAPI app: routes (audit, report, billing, auth) and middleware (auth, rate limit, CORS)
  audit.py        CLI entry point
frontend/         Next.js 15 app: scan, dashboard, audit detail, public report, pricing, auth
tests/            154 tests plus sample vulnerable contracts in tests/contracts/
supabase/         Schema and RLS policies
plan/             Product vision, roadmap, architecture notes, sprint logs
```

## Disclaimer

Reports generated by this tool are informational and do not constitute a professional security audit. Engage a certified security firm before deploying contracts that handle significant value.

## License

MIT. See [LICENSE](LICENSE).
