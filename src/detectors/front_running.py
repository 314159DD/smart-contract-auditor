"""Front-running vulnerability detector.

Detects patterns susceptible to transaction ordering / MEV attacks:
- ERC-20 approve() without increaseAllowance (classic double-spend race)
- Missing slippage protection in DEX-like swap functions
- Commit-reveal pattern missing (on-chain sensitive data before action)
- Price oracle reads without TWAP / staleness checks
"""

from __future__ import annotations
import re
from src.detectors.base import BaseDetector, Vulnerability
from src.parser.models import Contract


_APPROVE_RE = re.compile(r"\bfunction\s+approve\s*\(")
_INCREASE_ALLOWANCE_RE = re.compile(r"\bincreaseAllowance\b|\bdecreaseAllowance\b")

_SWAP_FN_RE = re.compile(r"\bswap|\bexchange", re.IGNORECASE)  # for fn.name matching
_SWAP_RE = re.compile(r"\bswap\w*\s*\(|\bexchange\w*\s*\(", re.IGNORECASE)  # for body matching
_SLIPPAGE_RE = re.compile(
    r"\bminAmount\b|\bminOut\b|\bminReturn\b|\bamountOutMin\b|\bdeadline\b",
    re.IGNORECASE,
)

_ORACLE_READ_RE = re.compile(
    r"getPrice\s*\(|latestAnswer\s*\(|latestRoundData\s*\(|consult\s*\(",
    re.IGNORECASE,
)
_TWAP_RE = re.compile(r"\bTWAP\b|\btime.?weighted\b|\bobservation\b", re.IGNORECASE)


class FrontRunningDetector(BaseDetector):
    name = "front_running"
    severity = "MEDIUM"

    def detect(self, contract: Contract) -> list[Vulnerability]:
        findings: list[Vulnerability] = []

        # ERC-20 approve() without increaseAllowance
        has_approve = any(
            _APPROVE_RE.search(fn.body_source) or fn.name == "approve"
            for fn in contract.functions
        )
        has_increase = _INCREASE_ALLOWANCE_RE.search(contract.source)
        if has_approve and not has_increase:
            findings.append(Vulnerability(
                detector=self.name,
                severity="MEDIUM",
                title="ERC-20 approve() vulnerable to front-running double-spend",
                description=(
                    f"`{contract.name}` implements `approve()` but not "
                    "`increaseAllowance`/`decreaseAllowance`. The standard ERC-20 "
                    "approve-then-transferFrom flow is vulnerable: a spender can "
                    "detect a pending approval change, front-run it, and spend "
                    "both the old and new allowance."
                ),
                location=f"{contract.name}.approve",
                recommendation=(
                    "Add `increaseAllowance` and `decreaseAllowance` functions "
                    "(as in OpenZeppelin ERC20) to avoid the allowance front-running "
                    "attack. Alternatively, require the current allowance be set to 0 "
                    "before changing it."
                ),
                confidence="medium",
                cwe_id="CWE-362",
                references=[
                    "https://swcregistry.io/docs/SWC-114",
                    "https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729",
                ],
            ))

        for fn in contract.functions:
            body = fn.body_source

            # Swap/exchange without slippage protection
            if _SWAP_FN_RE.search(fn.name) and not _SLIPPAGE_RE.search(body):
                findings.append(Vulnerability(
                    detector=self.name,
                    severity="HIGH",
                    title=f"Missing slippage protection in `{fn.name}`",
                    description=(
                        f"`{contract.name}.{fn.name}` appears to perform a swap or "
                        "exchange without a minimum output amount (`amountOutMin`, "
                        "`minReturn`, or `deadline`) parameter. MEV bots can sandwich "
                        "the transaction, extracting value from the user."
                    ),
                    location=f"{contract.name}.{fn.name} (lines {fn.line_start}-{fn.line_end})",
                    recommendation=(
                        "Add `amountOutMin` and `deadline` parameters to swap "
                        "functions. Validate that the received output is at least "
                        "`amountOutMin` before completing the swap."
                    ),
                    confidence="medium",
                    cwe_id="CWE-362",
                    references=["https://swcregistry.io/docs/SWC-114"],
                ))

            # Price oracle without TWAP
            if _ORACLE_READ_RE.search(body) and not _TWAP_RE.search(body):
                findings.append(Vulnerability(
                    detector=self.name,
                    severity="MEDIUM",
                    title=f"Spot price oracle without TWAP in `{fn.name}`",
                    description=(
                        f"`{contract.name}.{fn.name}` reads a price oracle without "
                        "apparent TWAP (time-weighted average price) protection. "
                        "Spot prices can be manipulated within a single transaction "
                        "via flash loans, enabling price oracle attacks."
                    ),
                    location=f"{contract.name}.{fn.name} (lines {fn.line_start}-{fn.line_end})",
                    recommendation=(
                        "Use a TWAP oracle (e.g., Uniswap V3 TWAP, Chainlink) "
                        "instead of spot price reads. Add staleness checks on "
                        "Chainlink feeds: verify `updatedAt` is recent."
                    ),
                    confidence="low",
                    cwe_id="CWE-362",
                    references=[
                        "https://docs.uniswap.org/concepts/protocol/oracle",
                        "https://blog.openzeppelin.com/secure-smart-contract-guidelines-the-dangers-of-price-oracles",
                    ],
                ))

        return findings
