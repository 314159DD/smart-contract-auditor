"""Unchecked external call return value detector.

Detects low-level calls (.call, .delegatecall, .staticcall) whose boolean
return value is not captured or checked.
"""

from __future__ import annotations
import re
from src.detectors.base import BaseDetector, Vulnerability
from src.parser.models import Contract


# Matches uncaptured low-level calls: the call appears but the return value
# is not assigned to anything or placed inside a require/assert.
_UNCHECKED_CALL_RE = re.compile(
    r"""
    (?<![=,\(])          # not preceded by assignment or function arg
    \s*                  # optional whitespace
    \w+\.call\s*[({]     # address.call(
    | \w+\.staticcall\s*\(
    """,
    re.VERBOSE,
)

# Pattern for a properly captured call: (bool success, ...) = addr.call(...)
_CAPTURED_RE = re.compile(
    r"""
    \(\s*bool\s+\w+       # (bool success
    | \bbool\s+\w+\s*=    # bool ok =
    | require\s*\(.*\.call  # require(addr.call(...
    | assert\s*\(.*\.call
    """,
    re.VERBOSE,
)

_SUCCESS_CHECK_RE = re.compile(r"require\s*\(\s*\w+\s*[,)]|assert\s*\(\s*\w+\s*\)")


class UncheckedCallDetector(BaseDetector):
    name = "unchecked_call"
    severity = "MEDIUM"

    def detect(self, contract: Contract) -> list[Vulnerability]:
        findings: list[Vulnerability] = []

        for fn in contract.functions:
            body = fn.body_source

            # Look for low-level calls
            for call_match in re.finditer(r"\b\w+\.call\s*[({]|\b\w+\.staticcall\s*\(", body):
                # Check if the call result is captured/required in surrounding context
                # Look 120 chars before the call for an assignment or require
                ctx_start = max(0, call_match.start() - 120)
                context = body[ctx_start: call_match.end() + 60]

                if _CAPTURED_RE.search(context):
                    continue

                # Also check for success variable check within 200 chars after the call
                after_call = body[call_match.end(): call_match.end() + 200]
                if _SUCCESS_CHECK_RE.search(after_call):
                    continue

                findings.append(Vulnerability(
                    detector=self.name,
                    severity="MEDIUM",
                    title=f"Unchecked return value of low-level call in `{fn.name}`",
                    description=(
                        f"`{contract.name}.{fn.name}` makes a low-level `.call()` "
                        "without checking its return value. Low-level calls return "
                        "`false` on failure instead of reverting; ignoring this "
                        "means silent failures that leave the contract in an "
                        "inconsistent state."
                    ),
                    location=f"{contract.name}.{fn.name} (lines {fn.line_start}-{fn.line_end})",
                    recommendation=(
                        "Always capture the return value: "
                        "`(bool success, bytes memory data) = addr.call{...}(...)` "
                        "and then `require(success, \"Call failed\");`."
                    ),
                    confidence="high",
                    cwe_id="CWE-252",
                    references=["https://swcregistry.io/docs/SWC-104"],
                ))
                break  # One finding per function

        return findings
