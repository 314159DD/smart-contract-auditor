"""Integer overflow/underflow detector.

Detects:
- Arithmetic operations in contracts compiled with Solidity < 0.8.0 (no built-in overflow protection)
- Unchecked arithmetic blocks in Solidity >= 0.8.0 contracts
"""

from __future__ import annotations
import re
from src.detectors.base import BaseDetector, Vulnerability
from src.parser.models import Contract, Function


# Arithmetic operations that can overflow/underflow
# Matches compound assignments and inc/dec even after array subscripts like balances[x] -= y
_ARITHMETIC_RE = re.compile(r"\+=|-=|\*=|/=|\*\*=|\+\+|--")
_UNCHECKED_BLOCK_RE = re.compile(r"\bunchecked\s*\{")
_SAFEMATH_RE = re.compile(r"\bSafeMath\b|\busing\s+SafeMath\b")


class OverflowDetector(BaseDetector):
    name = "overflow"
    severity = "HIGH"

    def detect(self, contract: Contract) -> list[Vulnerability]:
        findings: list[Vulnerability] = []
        uses_safemath = bool(_SAFEMATH_RE.search(contract.source))

        if contract.is_pre_080():
            # Pre-0.8.0: every arithmetic op is potentially unsafe unless SafeMath is used
            if uses_safemath:
                return findings  # SafeMath covers all arithmetic

            for fn in contract.functions:
                if fn.mutability in ("view", "pure"):
                    continue
                if _ARITHMETIC_RE.search(fn.body_source):
                    findings.append(Vulnerability(
                        detector=self.name,
                        severity="HIGH",
                        title=f"Integer overflow/underflow in `{fn.name}` (pre-0.8.0)",
                        description=(
                            f"`{contract.name}` uses Solidity {contract.compiler_version}, "
                            "which does not have built-in overflow/underflow protection. "
                            f"Function `{fn.name}` contains arithmetic that could wrap around "
                            "silently, leading to incorrect balances or bypass of checks."
                        ),
                        location=f"{contract.name}.{fn.name} (lines {fn.line_start}-{fn.line_end})",
                        recommendation=(
                            "Use OpenZeppelin's SafeMath library for all arithmetic, "
                            "or upgrade to Solidity 0.8.0+ which has built-in "
                            "overflow/underflow checks."
                        ),
                        confidence="high",
                        cwe_id="CWE-190",
                        references=[
                            "https://swcregistry.io/docs/SWC-101",
                            "https://docs.openzeppelin.com/contracts/4.x/api/utils#SafeMath",
                        ],
                    ))
        else:
            # Post-0.8.0: only flag `unchecked {}` blocks with arithmetic
            for fn in contract.functions:
                for match in _UNCHECKED_BLOCK_RE.finditer(fn.body_source):
                    block_start = match.end()
                    # Heuristically grab the block body (up to matching })
                    depth = 1
                    pos = block_start
                    while pos < len(fn.body_source) and depth > 0:
                        ch = fn.body_source[pos]
                        if ch == "{":
                            depth += 1
                        elif ch == "}":
                            depth -= 1
                        pos += 1
                    block_body = fn.body_source[block_start:pos - 1]

                    if _ARITHMETIC_RE.search(block_body):
                        findings.append(Vulnerability(
                            detector=self.name,
                            severity="LOW",
                            title=f"Unchecked arithmetic block in `{fn.name}`",
                            description=(
                                f"`{contract.name}.{fn.name}` contains an `unchecked` "
                                "block with arithmetic. The `unchecked` keyword disables "
                                "Solidity 0.8+ overflow protection for performance reasons, "
                                "which is safe ONLY when the developer has proven no overflow "
                                "is possible. Incorrect usage can cause silent under/overflow."
                            ),
                            location=f"{contract.name}.{fn.name} (lines {fn.line_start}-{fn.line_end})",
                            recommendation=(
                                "Verify that every arithmetic expression inside `unchecked` "
                                "blocks is mathematically bounded. Add comments explaining "
                                "why overflow is impossible for each expression."
                            ),
                            confidence="medium",
                            cwe_id="CWE-190",
                            references=["https://swcregistry.io/docs/SWC-101"],
                        ))
                        break  # One finding per function is enough

        return findings
