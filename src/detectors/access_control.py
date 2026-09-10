"""Access control vulnerability detector.

Detects:
- Public/external state-changing functions with no access-control modifiers
- Missing zero-address checks on admin assignment functions
- Unprotected initialize() functions (proxy upgrade pattern)
"""

from __future__ import annotations
import re
from src.detectors.base import BaseDetector, Vulnerability
from src.parser.models import Contract, Function


# Modifiers that indicate access control is present
_ACCESS_MODIFIERS = {
    "onlyOwner", "onlyAdmin", "onlyRole", "onlyGovernance", "onlyController",
    "onlyMinter", "onlyBurner", "onlyOperator", "onlyGuard", "authorized",
    "requiresAuth", "adminOnly", "ownerOnly", "restricted",
}

# Functions that are safe to leave unprotected (getters, ERC-standard callbacks)
_SAFE_UNPROTECTED = {
    "supportsInterface", "balanceOf", "totalSupply", "allowance", "decimals",
    "name", "symbol", "tokenURI", "ownerOf", "getApproved", "isApprovedForAll",
    "transfer", "transferFrom", "approve",  # ERC-20/721 transfers are intentionally public
    "receive", "fallback",
}

_ZERO_ADDRESS_RE = re.compile(r"require\s*\(\s*\w+\s*!=\s*address\(0\)")
_ADDRESS_PARAM_RE = re.compile(r"\baddress\b")


def _has_access_modifier(fn: Function) -> bool:
    """Return True if any known access-control modifier is present."""
    mods_lower = {m.lower() for m in fn.modifiers}
    for mod in _ACCESS_MODIFIERS:
        if mod.lower() in mods_lower:
            return True
    # Also check for role-based require() in the body
    if re.search(r"require\s*\(\s*\w+\.hasRole\b", fn.body_source):
        return True
    if re.search(r"require\s*\(\s*msg\.sender\s*==", fn.body_source):
        return True
    if re.search(r"_checkOwner\s*\(", fn.body_source):
        return True
    return False


class AccessControlDetector(BaseDetector):
    name = "access_control"
    severity = "HIGH"

    def detect(self, contract: Contract) -> list[Vulnerability]:
        findings: list[Vulnerability] = []

        for fn in contract.public_external_functions():
            if fn.name in _SAFE_UNPROTECTED:
                continue
            if fn.is_constructor:
                continue
            if fn.mutability in ("view", "pure"):
                continue

            # Unprotected initialize() – critical for proxy patterns
            if fn.name in ("initialize", "init", "__init__") and not _has_access_modifier(fn):
                findings.append(Vulnerability(
                    detector=self.name,
                    severity="CRITICAL",
                    title="Unprotected initialize() function",
                    description=(
                        f"`{contract.name}.{fn.name}` is callable by anyone. "
                        "In proxy-upgrade patterns, an attacker can call `initialize()` "
                        "on the implementation contract directly, taking ownership or "
                        "corrupting critical state before the legitimate deployer does."
                    ),
                    location=f"{contract.name}.{fn.name} (lines {fn.line_start}-{fn.line_end})",
                    recommendation=(
                        "Add an `initializer` modifier (OpenZeppelin Initializable) "
                        "or an `onlyOwner` check, and ensure the function can only be "
                        "called once."
                    ),
                    confidence="high",
                    cwe_id="CWE-284",
                    references=[
                        "https://swcregistry.io/docs/SWC-118",
                        "https://docs.openzeppelin.com/upgrades-plugins/1.x/writing-upgradeable",
                    ],
                ))
                continue

            # Generic unprotected state-changing function
            if not _has_access_modifier(fn):
                findings.append(Vulnerability(
                    detector=self.name,
                    severity="HIGH",
                    title=f"Missing access control on `{fn.name}`",
                    description=(
                        f"`{contract.name}.{fn.name}` is `{fn.visibility}` and modifies "
                        "state without any access-control modifier. Any address can call "
                        "this function."
                    ),
                    location=f"{contract.name}.{fn.name} (lines {fn.line_start}-{fn.line_end})",
                    recommendation=(
                        "Add an `onlyOwner` modifier or equivalent access control. "
                        "Consider using OpenZeppelin's `Ownable` or `AccessControl`."
                    ),
                    confidence="medium",
                    cwe_id="CWE-284",
                    references=[
                        "https://swcregistry.io/docs/SWC-105",
                        "https://docs.openzeppelin.com/contracts/4.x/access-control",
                    ],
                ))

            # Missing zero-address check on admin-assignment functions
            if (
                _ADDRESS_PARAM_RE.search(" ".join(p.type for p in fn.parameters))
                and any(kw in fn.name.lower() for kw in ("set", "update", "change", "transfer"))
                and not _ZERO_ADDRESS_RE.search(fn.body_source)
            ):
                findings.append(Vulnerability(
                    detector=self.name,
                    severity="MEDIUM",
                    title=f"Missing zero-address check in `{fn.name}`",
                    description=(
                        f"`{contract.name}.{fn.name}` accepts an `address` parameter "
                        "but does not validate it is not `address(0)`. Accidentally "
                        "setting a critical address to zero can brick the contract."
                    ),
                    location=f"{contract.name}.{fn.name} (lines {fn.line_start}-{fn.line_end})",
                    recommendation=(
                        'Add `require(param != address(0), "Zero address");` at the '
                        "top of the function for every address parameter."
                    ),
                    confidence="medium",
                    cwe_id="CWE-20",
                    references=["https://swcregistry.io/docs/SWC-104"],
                ))

        return findings
