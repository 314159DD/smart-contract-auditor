"""Block timestamp dependence detector.

Detects use of block.timestamp (or 'now') in critical logic such as randomness,
deadlines enforced within a single block, or locking mechanisms.
"""

from __future__ import annotations
import re
from src.detectors.base import BaseDetector, Vulnerability
from src.parser.models import Contract


# Direct use of block.timestamp or the deprecated 'now' alias
_TIMESTAMP_RE = re.compile(r"\bblock\.timestamp\b|\bnow\b")

# Patterns suggesting timestamp is used in critical/sensitive logic
_CRITICAL_USE_RE = re.compile(
    r"""
    block\.timestamp\s*[<>]=?  # comparison
    | [<>]=?\s*block\.timestamp
    | \bnow\s*[<>]=?
    | [<>]=?\s*\bnow\b
    | block\.timestamp\s*[+\-\*\/]  # arithmetic with timestamp
    | [+\-\*\/]\s*block\.timestamp
    | require\s*\(.*block\.timestamp
    | if\s*\(.*block\.timestamp
    | require\s*\(.*\bnow\b
    | if\s*\(.*\bnow\b
    """,
    re.VERBOSE,
)

# Randomness patterns using timestamp
_RANDOM_RE = re.compile(
    r"keccak256\s*\(.*block\.timestamp|block\.timestamp.*keccak256"
)


class TimestampDetector(BaseDetector):
    name = "timestamp"
    severity = "LOW"

    def detect(self, contract: Contract) -> list[Vulnerability]:
        findings: list[Vulnerability] = []

        for fn in contract.functions:
            body = fn.body_source

            if _RANDOM_RE.search(body):
                findings.append(Vulnerability(
                    detector=self.name,
                    severity="HIGH",
                    title=f"Block timestamp used as randomness source in `{fn.name}`",
                    description=(
                        f"`{contract.name}.{fn.name}` uses `block.timestamp` as an "
                        "input to `keccak256` for randomness. Miners can manipulate "
                        "timestamps by up to ~15 seconds, allowing them to influence "
                        "outcomes in their favour."
                    ),
                    location=f"{contract.name}.{fn.name} (lines {fn.line_start}-{fn.line_end})",
                    recommendation=(
                        "Use a verifiable random function (VRF) such as Chainlink VRF "
                        "for on-chain randomness. Never rely solely on block properties "
                        "for entropy."
                    ),
                    confidence="high",
                    cwe_id="CWE-330",
                    references=[
                        "https://swcregistry.io/docs/SWC-120",
                        "https://docs.chain.link/vrf",
                    ],
                ))
            elif _CRITICAL_USE_RE.search(body):
                findings.append(Vulnerability(
                    detector=self.name,
                    severity="LOW",
                    title=f"Block timestamp dependence in `{fn.name}`",
                    description=(
                        f"`{contract.name}.{fn.name}` uses `block.timestamp` in "
                        "conditional logic. Miners can adjust timestamps within a "
                        "~15-second window, which can be exploited for time-sensitive "
                        "operations (auctions, token locks, lottery draws)."
                    ),
                    location=f"{contract.name}.{fn.name} (lines {fn.line_start}-{fn.line_end})",
                    recommendation=(
                        "For locking/vesting with multi-hour or multi-day windows, "
                        "`block.timestamp` is generally safe. For sub-minute precision "
                        "or randomness, use block.number or an oracle."
                    ),
                    confidence="medium",
                    cwe_id="CWE-829",
                    references=["https://swcregistry.io/docs/SWC-116"],
                ))

        return findings
