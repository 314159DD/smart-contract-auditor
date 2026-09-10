# Contract Auditor — Architecture Overview

## System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        Web Frontend (Next.js)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Upload/Paste │  │ Report View  │  │ Dashboard    │         │
│  │ Contract     │  │ (findings,   │  │ (history,    │         │
│  └──────┬───────┘  │  risk gauge) │  │  usage)      │         │
│         │          └──────────────┘  └──────────────┘         │
└─────────┼─────────────────────────────────────────────────────┘
          │ POST /api/audit
          ▼
┌────────────────────────────────────────────────────────────────┐
│                     API Backend (FastAPI)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Auth     │  │ Audit    │  │ Billing  │  │ Rate     │      │
│  │ (Supa)   │  │ Routes   │  │ (Stripe) │  │ Limiter  │      │
│  └──────────┘  └────┬─────┘  └──────────┘  └──────────┘      │
└──────────────────────┼────────────────────────────────────────┘
                       │ async queue
                       ▼
┌────────────────────────────────────────────────────────────────┐
│                     Audit Pipeline                               │
│                                                                  │
│  1. Source Acquisition                                           │
│     ├─ Direct upload (.sol file)                                │
│     ├─ Paste (raw Solidity)                                     │
│     └─ Etherscan fetch (address + chain)                        │
│                                                                  │
│  2. Parsing                                                      │
│     └─ SolidityParser → Contract AST                            │
│                                                                  │
│  3. Static Analysis                                              │
│     ├─ ReentrancyDetector                                       │
│     ├─ AccessControlDetector                                    │
│     ├─ OverflowDetector                                         │
│     ├─ UncheckedCallDetector                                    │
│     ├─ TxOriginDetector                                         │
│     ├─ SelfdestructDetector                                     │
│     ├─ DelegatecallDetector                                     │
│     ├─ TimestampDetector                                        │
│     ├─ GasLimitDetector                                         │
│     └─ FrontRunningDetector                                     │
│                                                                  │
│  4. AI Analysis (paid tiers only)                                │
│     ├─ Business logic review                                    │
│     ├─ Economic attack vectors                                  │
│     ├─ Centralization risks                                     │
│     └─ Fix generation (before/after code)                       │
│                                                                  │
│  5. Report Generation                                            │
│     ├─ JSON (API response)                                      │
│     ├─ Markdown (display)                                       │
│     └─ PDF (download)                                           │
└────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
smart-contract-auditor/
├── src/
│   ├── parser/
│   │   ├── solidity.py          # Solidity source → Contract AST
│   │   ├── ast_analyzer.py      # AST traversal utilities
│   │   └── models.py            # Contract, Function, Variable models
│   ├── detectors/
│   │   ├── base.py              # BaseDetector interface
│   │   ├── reentrancy.py        # Reentrancy detection
│   │   ├── access_control.py    # Missing access controls
│   │   ├── overflow.py          # Integer overflow/underflow
│   │   ├── unchecked_call.py    # Unchecked return values
│   │   ├── tx_origin.py         # tx.origin auth
│   │   ├── selfdestruct.py      # Unprotected selfdestruct
│   │   ├── delegatecall.py      # Dangerous delegatecall
│   │   ├── timestamp.py         # Timestamp dependence
│   │   ├── gas_limit.py         # Unbounded loops / DoS
│   │   └── front_running.py     # Front-running patterns
│   ├── ai/
│   │   ├── analyzer.py          # Claude-powered deep analysis
│   │   ├── prompts.py           # Prompt templates
│   │   └── models.py            # AIFinding dataclass
│   ├── reports/
│   │   ├── generator.py         # Report orchestrator
│   │   ├── markdown.py          # Markdown report formatter
│   │   ├── pdf.py               # PDF export (weasyprint)
│   │   └── models.py            # AuditReport, Finding, Summary
│   ├── web/
│   │   ├── app.py               # FastAPI application
│   │   ├── routes/              # API endpoints
│   │   ├── middleware/          # Auth, rate limiting
│   │   └── database.py         # Supabase client
│   ├── etherscan/
│   │   └── fetcher.py           # Verified source code fetcher
│   └── config.py
├── frontend/                     # Next.js 15 web app
│   ├── app/
│   ├── components/
│   └── lib/
├── tests/
│   ├── contracts/               # Sample Solidity files
│   └── test_detectors.py
├── plan/
├── .env.example
├── requirements.txt
└── CLAUDE.md
```

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Parser | slither-analyzer or py-solc-x | Industry-standard Solidity analysis |
| Static Analysis | Custom detectors | Tailored to our vulnerability list |
| AI Analysis | Anthropic Claude API | Best reasoning for complex code review |
| Backend | FastAPI | Async-native, auto OpenAPI docs |
| Frontend | Next.js 15 | SSR, App Router, fast iteration |
| Auth | Supabase Auth | Already using across other projects |
| Database | Supabase PostgreSQL | Stores audits, users, usage |
| Payments | Stripe | Industry standard, webhooks |
| PDF | weasyprint | Python-native, CSS-based PDF generation |
| Deploy | Railway (API) + Vercel (frontend) | Already familiar stack |

## Tier System

| Feature | Free | Pro ($29/mo) | Enterprise ($199/mo) |
|---------|------|-------------|---------------------|
| Quick Scan (static only) | 5/month | 50/month | Unlimited |
| Standard Scan (static + AI) | -- | 50/month | Unlimited |
| Deep Audit (multi-pass AI) | -- | -- | Unlimited |
| Max contract size | 500 lines | 5000 lines | Unlimited |
| PDF export | -- | Yes | Yes |
| Public sharing | Yes | Yes | Yes |
| API access | -- | -- | Yes |
| Concurrent scans | 1 | 5 | Unlimited |

## Key Design Decisions

- **Free tier = lead gen**: Quick scan (static only) is free. This builds trust and funnels to paid.
- **Slither as foundation**: Rather than writing a Solidity parser from scratch, build on Slither's proven AST capabilities.
- **AI is the differentiator**: Static analysis is commoditized. The AI layer (business logic, economic attacks, fix generation) is what makes this worth paying for.
- **No liability claims**: Reports include prominent disclaimer. We provide analysis, not guarantees.
- **Async processing**: Scans take 5s-3min. Always process async and poll for results.
