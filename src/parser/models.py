"""
Dataclasses representing parsed Solidity contract structures.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Parameter:
    name: str
    type: str
    indexed: bool = False  # For event parameters


@dataclass
class Function:
    name: str
    visibility: str               # public/external/internal/private
    mutability: str               # view/pure/payable/nonpayable
    modifiers: list[str] = field(default_factory=list)
    parameters: list[Parameter] = field(default_factory=list)
    returns: list[Parameter] = field(default_factory=list)
    body_source: str = ""
    line_start: int = 0
    line_end: int = 0
    is_constructor: bool = False


@dataclass
class StateVariable:
    name: str
    type: str
    visibility: str               # public/internal/private/constant
    is_constant: bool = False
    is_immutable: bool = False
    initial_value: Optional[str] = None
    line: int = 0


@dataclass
class Modifier:
    name: str
    parameters: list[Parameter] = field(default_factory=list)
    body_source: str = ""
    line_start: int = 0
    line_end: int = 0


@dataclass
class Event:
    name: str
    parameters: list[Parameter] = field(default_factory=list)
    line: int = 0


@dataclass
class Contract:
    name: str
    source: str
    compiler_version: str
    functions: list[Function] = field(default_factory=list)
    state_variables: list[StateVariable] = field(default_factory=list)
    modifiers: list[Modifier] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    inheritance: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    pragma: str = ""
    file_path: Optional[str] = None
    is_interface: bool = False
    is_abstract: bool = False

    def is_pre_080(self) -> bool:
        """Return True if the compiler version is before 0.8.0."""
        import re
        version_str = self.compiler_version.strip("^>=<~ ")
        match = re.match(r"(\d+)\.(\d+)", version_str)
        if match:
            major, minor = int(match.group(1)), int(match.group(2))
            return (major, minor) < (0, 8)
        return False

    def state_changing_functions(self) -> list["Function"]:
        """Return functions that modify state (not view/pure, not constructor)."""
        return [
            fn for fn in self.functions
            if fn.mutability not in ("view", "pure") and not fn.is_constructor
        ]

    def public_external_functions(self) -> list["Function"]:
        """Return functions with public or external visibility."""
        return [fn for fn in self.functions if fn.visibility in ("public", "external")]
