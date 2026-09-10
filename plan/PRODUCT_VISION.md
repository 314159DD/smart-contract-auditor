# AI Contract Auditor — Product Vision

## What

AI-powered smart contract security scanner targeting small-to-mid DeFi projects that can't afford $50-200K manual audits. Freemium: free basic scan, paid detailed reports.

## Why

- Every new DeFi project needs security review
- Manual audits: $50-200K and weeks of waiting
- AI auditors: ChainGPT decreased costs by 100x
- Long tail of unaudited projects is massive and growing
- Recurring need — new contracts deployed daily

## Revenue Model

- Free tier: basic vulnerability scan (lead gen)
- Paid: $50-500 per detailed audit report
- Enterprise: CI/CD integration, continuous monitoring

## Reality Check

- Liability risk if you miss a vulnerability that gets exploited
- Requires deep Solidity expertise
- Savant Chat claims 87-95% accuracy — good but not perfect
- 6-10 week build to MVP
- Income: $2-8K/month potential

## Tech Stack (Planned)

- Solidity AST parsing
- Claude/GPT for vulnerability analysis
- Aderyn MCP Server as foundation
- Web frontend for reports
