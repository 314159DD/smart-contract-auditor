"""Reentrancy vulnerability detector.

Detects:
- External calls before state changes (classic reentrancy)
- Missing ReentrancyGuard on payable functions
- Cross-function reentrancy via shared state
"""

from __future__ import annotations
import re
from src.detectors.base import BaseDetector, Vulnerability
from src.parser.models import Contract, Function


# Patterns that indicate an external call
_EXTERNAL_CALL_RE = re.compile(
    r"""
    \.call\s*[({]           # low-level .call(
    | \.transfer\s*\(       # address.transfer(
    | \.send\s*\(           # address.send(
    | \.delegatecall\s*\(   # .delegatecall(
    | IERC\w+\.\w+\s*\(    # IERC20.transfer( etc.
    | I[A-Z]\w+\.\w+\s*\(  # any interface call
    """,
    re.VERBOSE,
)

# Patterns that indicate a state-change (storage write)
# These match compound assignments and inc/dec regardless of what precedes them
# (handles array subscripts like balances[msg.sender] -= amount)
_STATE_CHANGE_RE = re.compile(
    r"""
    \+=|-=|\*=|/=       # compound assignment operators
    | \+\+|--           # increment / decrement
    | \bdelete\s+\w+    # delete mapping entry
    | \.push\s*\(       # push to dynamic array
    | \.pop\s*\(        # pop from dynamic array
    """,
    re.VERBOSE,
)

_REENTRANCY_GUARD_RE = re.compile(r"\bnonReentrant\b|\bReentrancyGuard\b")


def _has_external_call(source: str) -> bool:
    return bool(_EXTERNAL_CALL_RE.search(source))


def _external_call_before_state_change(source: str) -> bool:
    """Return True if an external call appears before a state-change in *source*."""
    call_match = _EXTERNAL_CALL_RE.search(source)
    if not call_match:
        return False
    after_call = source[call_match.end():]
    return bool(_STATE_CHANGE_RE.search(after_call))


class ReentrancyDetector(BaseDetector):
    name = "reentrancy"
    severity = "CRITICAL"

    def detect(self, contract: Contract) -> list[Vulnerability]:
        findings: list[Vulnerability] = []

        for fn in contract.functions:
            body = fn.body_source

            # Classic reentrancy: external call before state change
            if _external_call_before_state_change(body):
                findings.append(Vulnerability(
                    detector=self.name,
                    severity="CRITICAL",
                    title="Reentrancy: external call before state update",
                    description=(
                        f"Function `{fn.name}` performs an external call before "
                        "updating contract state. An attacker can re-enter the "
                        "function before the state is updated, potentially draining "
                        "funds or corrupting state."
                    ),
                    location=f"{contract.name}.{fn.name} (lines {fn.line_start}-{fn.line_end})",
                    recommendation=(
                        "Apply the Checks-Effects-Interactions pattern: perform all "
                        "state changes BEFORE any external calls. Alternatively, use "
                        "OpenZeppelin's `ReentrancyGuard` (`nonReentrant` modifier)."
                    ),
                    confidence="high",
                    cwe_id="CWE-841",
                    references=[
                        "https://swcregistry.io/docs/SWC-107",
                        "https://docs.openzeppelin.com/contracts/4.x/api/security#ReentrancyGuard",
                        "https://consensys.github.io/smart-contract-best-practices/attacks/reentrancy/",
                    ],
                ))

            # Payable function without reentrancy guard
            elif (
                fn.mutability == "payable"
                and fn.visibility in ("public", "external")
                and _has_external_call(body)
                and not _REENTRANCY_GUARD_RE.search(" ".join(fn.modifiers))
            ):
                findings.append(Vulnerability(
                    detector=self.name,
                    severity="HIGH",
                    title="Reentrancy: payable function missing ReentrancyGuard",
                    description=(
                        f"Payable function `{fn.name}` makes external calls without "
                        "a `nonReentrant` guard. Although no obvious state-change "
                        "after the call was detected, reentrancy is still possible "
                        "via cross-function or cross-contract paths."
                    ),
                    location=f"{contract.name}.{fn.name} (lines {fn.line_start}-{fn.line_end})",
                    recommendation=(
                        "Add the `nonReentrant` modifier from OpenZeppelin's "
                        "`ReentrancyGuard` to all payable external/public functions "
                        "that make external calls."
                    ),
                    confidence="medium",
                    cwe_id="CWE-841",
                    references=[
                        "https://swcregistry.io/docs/SWC-107",
                        "https://docs.openzeppelin.com/contracts/4.x/api/security#ReentrancyGuard",
                    ],
                ))

        return findings
