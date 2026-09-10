"""tx.origin authentication detector.

Detects use of tx.origin for authentication/authorization. This is vulnerable
to phishing attacks where a malicious contract can act on behalf of the original
transaction sender.
"""

from __future__ import annotations
import re
from src.detectors.base import BaseDetector, Vulnerability
from src.parser.models import Contract


_TX_ORIGIN_AUTH_RE = re.compile(
    r"""
    tx\.origin\s*==          # tx.origin == someAddress
    | tx\.origin\s*!=        # tx.origin != someAddress
    | require\s*\(.*tx\.origin   # require(... tx.origin ...)
    | if\s*\(.*tx\.origin        # if (... tx.origin ...)
    """,
    re.VERBOSE,
)


class TxOriginDetector(BaseDetector):
    name = "tx_origin"
    severity = "HIGH"

    def detect(self, contract: Contract) -> list[Vulnerability]:
        findings: list[Vulnerability] = []

        for fn in contract.functions:
            if _TX_ORIGIN_AUTH_RE.search(fn.body_source):
                findings.append(Vulnerability(
                    detector=self.name,
                    severity="HIGH",
                    title=f"Use of tx.origin for authentication in `{fn.name}`",
                    description=(
                        f"`{contract.name}.{fn.name}` uses `tx.origin` to authenticate "
                        "the caller. A malicious contract can trick an authorised user "
                        "into calling it, and that contract can then call this function "
                        "with the victim's `tx.origin`, bypassing the check."
                    ),
                    location=f"{contract.name}.{fn.name} (lines {fn.line_start}-{fn.line_end})",
                    recommendation=(
                        "Replace `tx.origin` with `msg.sender` for authentication. "
                        "Use `tx.origin` only for gas-refund patterns where the "
                        "initiator of the entire call chain must be identified, and "
                        "ensure that scenario is safe from re-entry."
                    ),
                    confidence="high",
                    cwe_id="CWE-807",
                    references=["https://swcregistry.io/docs/SWC-115"],
                ))

        return findings
