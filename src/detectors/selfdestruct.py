"""Selfdestruct vulnerability detector.

Detects unprotected selfdestruct() / suicide() calls that could allow anyone
to destroy the contract and steal its ether.
"""

from __future__ import annotations
import re
from src.detectors.base import BaseDetector, Vulnerability
from src.parser.models import Contract


_SELFDESTRUCT_RE = re.compile(r"\bselfdestruct\s*\(|\bsuicide\s*\(")

# Access modifiers that indicate some protection
_ACCESS_MODIFIERS = {
    "onlyOwner", "onlyAdmin", "onlyGovernance", "onlyController",
    "restricted", "authorized", "adminOnly", "ownerOnly",
}


class SelfdestructDetector(BaseDetector):
    name = "selfdestruct"
    severity = "CRITICAL"

    def detect(self, contract: Contract) -> list[Vulnerability]:
        findings: list[Vulnerability] = []

        for fn in contract.functions:
            if not _SELFDESTRUCT_RE.search(fn.body_source):
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
                    title=f"Unprotected selfdestruct in `{fn.name}`",
                    description=(
                        f"`{contract.name}.{fn.name}` calls `selfdestruct()` without "
                        "adequate access control. Any address can trigger this function "
                        "to destroy the contract and send all its ether to an arbitrary "
                        "address."
                    ),
                    location=f"{contract.name}.{fn.name} (lines {fn.line_start}-{fn.line_end})",
                    recommendation=(
                        "Add strong access control (e.g., `onlyOwner`) to any function "
                        "that calls `selfdestruct`. Consider using a timelocked "
                        "governance mechanism for such destructive operations."
                    ),
                    confidence="high",
                    cwe_id="CWE-284",
                    references=["https://swcregistry.io/docs/SWC-106"],
                ))
            else:
                # Protected but still noteworthy — INFO level
                findings.append(Vulnerability(
                    detector=self.name,
                    severity="INFO",
                    title=f"Selfdestruct present in `{fn.name}` (access-controlled)",
                    description=(
                        f"`{contract.name}.{fn.name}` calls `selfdestruct()`. Access "
                        "control appears to be present, but auditors should verify the "
                        "access-control logic and consider whether this capability is "
                        "necessary."
                    ),
                    location=f"{contract.name}.{fn.name} (lines {fn.line_start}-{fn.line_end})",
                    recommendation=(
                        "Confirm the access-control modifier is correctly implemented. "
                        "Consider removing `selfdestruct` entirely — it is deprecated "
                        "post-EIP-6049."
                    ),
                    confidence="high",
                    cwe_id="",
                    references=["https://eips.ethereum.org/EIPS/eip-6049"],
                ))

        return findings
