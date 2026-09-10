"""Prompt templates for the AI vulnerability analysis layer."""
from typing import Optional


SYSTEM_PROMPT = """\
You are an expert smart contract security auditor with deep knowledge of:
- Solidity vulnerabilities and attack patterns
- DeFi protocol economics and attack vectors
- EVM internals and gas optimization
- OpenZeppelin contracts and EIP standards
- Real-world exploits (Ronin, Poly Network, Euler Finance, etc.)

Your job is to analyze the provided Solidity contract and produce a rigorous
security audit report. Be specific, actionable, and reference real-world exploits
where relevant.
"""


def quick_scan_prompt(contract_source: str, contract_name: str) -> str:
    """Prompt for quick scan (static analysis only - no AI call made)."""
    raise NotImplementedError("Quick scan uses static detectors only; no AI prompt needed.")


def standard_scan_prompt(
    contract_source: str,
    contract_name: str,
    static_findings: list,
) -> str:
    """Single-pass analysis prompt for standard tier."""
    static_summary = _format_static_findings(static_findings)
    return f"""\
## Contract: {contract_name}

### Static Analysis Results
The following issues were already detected by static analysis tools:

{static_summary}

### Contract Source
```solidity
{contract_source[:12000]}
```

### Your Task
Analyze this contract and produce a JSON response with the following structure:

```json
{{
  "findings": [
    {{
      "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
      "title": "Short title",
      "description": "Detailed explanation of the vulnerability",
      "attack_scenario": "Step-by-step: 1) Attacker calls X, 2) ...",
      "affected_code": "The vulnerable code snippet",
      "fix_before": "The vulnerable code",
      "fix_after": "The fixed code",
      "fix_explanation": "Why this fix prevents the attack",
      "real_world_examples": ["https://..."],
      "confidence": "high|medium|low"
    }}
  ],
  "business_logic_notes": "Narrative analysis of business logic risks",
  "centralization_risks": ["List of centralization concerns"],
  "gas_optimizations": ["List of gas improvement suggestions"]
}}
```

Focus on:
1. Business logic vulnerabilities NOT caught by static analysis
2. Economic attack vectors: flash loans, oracle manipulation, sandwich attacks
3. Centralization risks: admin keys, upgrade proxies, kill switches
4. Any issues in the static results that need deeper explanation
5. Interactions with external protocols

Return ONLY valid JSON. No markdown wrapping.
"""


def deep_audit_pass1_prompt(
    contract_source: str,
    contract_name: str,
    static_findings: list,
) -> str:
    """First pass of deep audit: broad vulnerability sweep."""
    return standard_scan_prompt(contract_source, contract_name, static_findings)


def deep_audit_pass2_prompt(
    contract_source: str,
    contract_name: str,
    pass1_findings: list,
) -> str:
    """Second pass: cross-reference and exploit scenario generation."""
    findings_json = _format_ai_findings(pass1_findings)
    return f"""\
## Contract: {contract_name} — Deep Audit Pass 2

### Pass 1 Findings
{findings_json}

### Contract Source
```solidity
{contract_source[:12000]}
```

### Your Task
1. Validate each Pass 1 finding — mark confidence as high/medium/low
2. Identify any ADDITIONAL findings not caught in Pass 1
3. For CRITICAL and HIGH findings, provide a concrete proof-of-concept attack
4. Check for cross-function vulnerabilities and composability risks

Return the same JSON structure as Pass 1, but including all findings
(both validated Pass 1 findings and new ones). Adjust severity/confidence as needed.

Return ONLY valid JSON.
"""


def deep_audit_pass3_prompt(
    contract_source: str,
    contract_name: str,
    all_findings: list,
) -> str:
    """Third pass: fix generation and final remediation advice."""
    findings_json = _format_ai_findings(all_findings)
    return f"""\
## Contract: {contract_name} — Deep Audit Pass 3: Fix Generation

### Confirmed Findings
{findings_json}

### Contract Source
```solidity
{contract_source[:12000]}
```

### Your Task
For each finding above, provide:
1. A complete, correct code fix (before/after diff)
2. An explanation of why the fix works
3. Any deployment considerations or migration notes

Return the same JSON structure, enriching each finding with detailed
fix_before, fix_after, and fix_explanation fields.

Return ONLY valid JSON.
"""


def _format_static_findings(findings: list) -> str:
    if not findings:
        return "No static analysis findings."
    lines = []
    for i, f in enumerate(findings, 1):
        lines.append(
            f"{i}. [{f.severity}] {f.title} — {f.location}\n"
            f"   {f.description[:200]}"
        )
    return "\n".join(lines)


def _format_ai_findings(findings: list) -> str:
    import json
    try:
        serializable = []
        for f in findings:
            if hasattr(f, "__dict__"):
                serializable.append(f.__dict__)
            elif isinstance(f, dict):
                serializable.append(f)
        return json.dumps(serializable, indent=2)[:8000]
    except Exception:
        return str(findings)[:4000]
