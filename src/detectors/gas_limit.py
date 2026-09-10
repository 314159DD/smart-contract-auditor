"""Gas limit / DoS vulnerability detector.

Detects:
- Unbounded loops over dynamic arrays (DoS via block gas limit)
- Use of .transfer() / .send() which forwards only 2300 gas (DoS via gas stipend)
- Loops with external calls inside (expensive and potentially DOS-able)
"""

from __future__ import annotations
import re
from src.detectors.base import BaseDetector, Vulnerability
from src.parser.models import Contract


# Unbounded loop patterns
_LOOP_RE = re.compile(r"\bfor\s*\(|\bwhile\s*\(")
# Dynamic array length access inside a loop condition
_ARRAY_LENGTH_LOOP_RE = re.compile(r"for\s*\([^;]*;\s*\w+\s*<\s*\w+\.length")
# External call inside a loop
_CALL_IN_LOOP_RE = re.compile(
    r"for\s*\([^)]*\)[^{]*\{[^}]*(?:\.call|\.transfer|\.send|\.delegatecall)[^}]*\}"
)

# .transfer() and .send() — forward only 2300 gas, can fail if recipient is a contract
_TRANSFER_SEND_RE = re.compile(r"\b\w+\.transfer\s*\(|\b\w+\.send\s*\(")


class GasLimitDetector(BaseDetector):
    name = "gas_limit"
    severity = "MEDIUM"

    def detect(self, contract: Contract) -> list[Vulnerability]:
        findings: list[Vulnerability] = []

        for fn in contract.functions:
            body = fn.body_source

            # Unbounded loop over dynamic array
            if _ARRAY_LENGTH_LOOP_RE.search(body):
                findings.append(Vulnerability(
                    detector=self.name,
                    severity="MEDIUM",
                    title=f"Unbounded loop over dynamic array in `{fn.name}`",
                    description=(
                        f"`{contract.name}.{fn.name}` iterates over a dynamic array "
                        "using `.length`. As the array grows, the gas cost increases "
                        "linearly. An attacker can grow the array until the function "
                        "exceeds the block gas limit, permanently bricking it (DoS)."
                    ),
                    location=f"{contract.name}.{fn.name} (lines {fn.line_start}-{fn.line_end})",
                    recommendation=(
                        "Implement pagination or a pull-over-push pattern. Consider "
                        "bounding the array size with a maximum length check on entry. "
                        "For large data sets, process in batches with explicit start/end "
                        "indices."
                    ),
                    confidence="medium",
                    cwe_id="CWE-400",
                    references=["https://swcregistry.io/docs/SWC-128"],
                ))

            # External call inside a loop
            if _LOOP_RE.search(body):
                # Simplified check: external call pattern appears anywhere in a
                # function that also has a loop.
                if re.search(r"\.call\s*[({]|\.transfer\s*\(|\.send\s*\(", body):
                    # Verify the call is actually inside the loop block (heuristic)
                    loop_match = _LOOP_RE.search(body)
                    if loop_match:
                        after_loop = body[loop_match.start():]
                        if re.search(r"\.call\s*[({]|\.transfer\s*\(|\.send\s*\(", after_loop[:300]):
                            findings.append(Vulnerability(
                                detector=self.name,
                                severity="HIGH",
                                title=f"External call inside loop in `{fn.name}`",
                                description=(
                                    f"`{contract.name}.{fn.name}` appears to make "
                                    "external calls within a loop. If any recipient "
                                    "reverts (or runs out of gas), the entire transaction "
                                    "fails, permanently blocking the function."
                                ),
                                location=f"{contract.name}.{fn.name} (lines {fn.line_start}-{fn.line_end})",
                                recommendation=(
                                    "Use the pull-payment pattern: record owed amounts "
                                    "and let recipients withdraw individually. Avoid "
                                    "external calls in loops."
                                ),
                                confidence="medium",
                                cwe_id="CWE-400",
                                references=["https://swcregistry.io/docs/SWC-113"],
                            ))

            # .transfer() / .send() gas stipend issue
            if _TRANSFER_SEND_RE.search(body):
                findings.append(Vulnerability(
                    detector=self.name,
                    severity="LOW",
                    title=f"Use of .transfer()/.send() with 2300 gas stipend in `{fn.name}`",
                    description=(
                        f"`{contract.name}.{fn.name}` uses `.transfer()` or `.send()`, "
                        "which forward only 2300 gas. If the recipient is a smart "
                        "contract with a non-trivial fallback function, the transfer "
                        "will fail, permanently locking funds."
                    ),
                    location=f"{contract.name}.{fn.name} (lines {fn.line_start}-{fn.line_end})",
                    recommendation=(
                        "Replace `.transfer()` with `.call{value: amount}(\"\")` and "
                        "check the return value. This is the recommended pattern since "
                        "EIP-1884 increased gas costs for certain opcodes."
                    ),
                    confidence="high",
                    cwe_id="CWE-400",
                    references=[
                        "https://swcregistry.io/docs/SWC-134",
                        "https://consensys.github.io/smart-contract-best-practices/development-recommendations/general/use-call-not-send/",
                    ],
                ))

        return findings
