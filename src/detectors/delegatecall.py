"""Delegatecall vulnerability detector.

Detects dangerous delegatecall patterns:
- delegatecall to user-controlled addresses
- delegatecall without access control
- Storage collision risks
"""

from __future__ import annotations
import re
from src.detectors.base import BaseDetector, Vulnerability
from src.parser.models import Contract


_DELEGATECALL_RE = re.compile(r"\bdelegatecall\s*\(")

# Patterns suggesting the target address comes from user input / state
_USER_CONTROLLED_RE = re.compile(
    r"""
    \w+\.delegatecall\s*\(   # someVar.delegatecall(
    | delegatecall\s*\(\s*\w+ # delegatecall(someParam
    """,
    re.VERBOSE,
)

_ACCESS_MODIFIERS = {
    "onlyOwner", "onlyAdmin", "onlyGovernance", "restricted",
    "authorized", "adminOnly", "ownerOnly",
}


class DelegatecallDetector(BaseDetector):
    name = "delegatecall"
    severity = "HIGH"

    def detect(self, contract: Contract) -> list[Vulnerability]:
        findings: list[Vulnerability] = []

        for fn in contract.functions:
            if not _DELEGATECALL_RE.search(fn.body_source):
                continue

            mods_lower = {m.lower() for m in fn.modifiers}
            has_access = any(m.lower() in mods_lower for m in _ACCESS_MODIFIERS)
            has_require_sender = bool(
                re.search(r"require\s*\(\s*msg\.sender\s*==", fn.body_source)
            )

            if not has_access and not has_require_sender:
                findings.append(Vulnerability(
                    detector=self.name,
                    severity="CRITICAL",
                    title=f"Unprotected delegatecall in `{fn.name}`",
                    description=(
                        f"`{contract.name}.{fn.name}` uses `delegatecall` without "
                        "access control. `delegatecall` executes external code in the "
                        "context of the calling contract's storage. An attacker could "
                        "supply a malicious target address to overwrite arbitrary "
                        "storage slots, including the owner variable."
                    ),
                    location=f"{contract.name}.{fn.name} (lines {fn.line_start}-{fn.line_end})",
                    recommendation=(
                        "Restrict functions that use `delegatecall` to trusted "
                        "administrators only. Never `delegatecall` to user-supplied "
                        "addresses. Use a whitelist of approved implementation "
                        "contracts."
                    ),
                    confidence="high",
                    cwe_id="CWE-829",
                    references=[
                        "https://swcregistry.io/docs/SWC-112",
                        "https://blog.openzeppelin.com/proxy-patterns",
                    ],
                ))
            else:
                findings.append(Vulnerability(
                    detector=self.name,
                    severity="MEDIUM",
                    title=f"Delegatecall in `{fn.name}` — verify target is trusted",
                    description=(
                        f"`{contract.name}.{fn.name}` uses `delegatecall`. Access "
                        "control is present, but the target address should be verified "
                        "to be a trusted, audited implementation contract. Storage "
                        "layout collisions between proxy and implementation must be "
                        "carefully managed."
                    ),
                    location=f"{contract.name}.{fn.name} (lines {fn.line_start}-{fn.line_end})",
                    recommendation=(
                        "Ensure the implementation address is stored in an "
                        "EIP-1967 storage slot to avoid collisions. Use "
                        "OpenZeppelin's `TransparentUpgradeableProxy` or `UUPS` "
                        "patterns."
                    ),
                    confidence="medium",
                    cwe_id="CWE-829",
                    references=[
                        "https://eips.ethereum.org/EIPS/eip-1967",
                        "https://swcregistry.io/docs/SWC-112",
                    ],
                ))

        return findings
