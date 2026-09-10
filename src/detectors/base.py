"""Base detector interface and Vulnerability dataclass."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.parser.models import Contract


@dataclass
class Vulnerability:
    """A detected vulnerability in a smart contract."""
    detector: str                        # Which detector found it (e.g. "reentrancy")
    severity: str                        # CRITICAL / HIGH / MEDIUM / LOW / INFO
    title: str                           # Short description
    description: str                     # Detailed explanation
    location: str                        # Contract.function or line number
    recommendation: str                  # How to fix it
    confidence: str                      # high / medium / low
    cwe_id: str = ""                     # CWE identifier if applicable
    references: list[str] = field(default_factory=list)   # Links to exploits / docs

    def to_dict(self) -> dict:
        return {
            "detector": self.detector,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "cwe_id": self.cwe_id,
            "references": self.references,
        }


class BaseDetector(ABC):
    """Interface that all vulnerability detectors must implement."""

    #: Human-readable name shown in reports
    name: str = ""
    #: Default severity when the detector fires
    severity: str = "MEDIUM"

    @abstractmethod
    def detect(self, contract: "Contract") -> list[Vulnerability]:
        """Analyse *contract* and return any detected vulnerabilities.

        Args:
            contract: The parsed Contract object to analyse.

        Returns:
            A (possibly empty) list of Vulnerability instances.
        """
