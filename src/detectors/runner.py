"""DetectorRunner — orchestrates all vulnerability detectors against a parsed Contract."""

from __future__ import annotations
from typing import TYPE_CHECKING

from src.detectors.base import BaseDetector, Vulnerability
from src.detectors.reentrancy import ReentrancyDetector
from src.detectors.access_control import AccessControlDetector
from src.detectors.overflow import OverflowDetector
from src.detectors.unchecked_call import UncheckedCallDetector
from src.detectors.tx_origin import TxOriginDetector
from src.detectors.selfdestruct import SelfdestructDetector
from src.detectors.delegatecall import DelegatecallDetector
from src.detectors.timestamp import TimestampDetector
from src.detectors.gas_limit import GasLimitDetector
from src.detectors.front_running import FrontRunningDetector

if TYPE_CHECKING:
    from src.parser.models import Contract

# Severity ordering for sorting results
_SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}

# All built-in detectors, keyed by name
_ALL_DETECTORS: dict[str, BaseDetector] = {
    d.name: d
    for d in [
        ReentrancyDetector(),
        AccessControlDetector(),
        OverflowDetector(),
        UncheckedCallDetector(),
        TxOriginDetector(),
        SelfdestructDetector(),
        DelegatecallDetector(),
        TimestampDetector(),
        GasLimitDetector(),
        FrontRunningDetector(),
    ]
}


class DetectorRunner:
    """Runs one or more detectors against a parsed Contract.

    Args:
        detectors: Optional list of :class:`BaseDetector` instances.
            Defaults to all built-in detectors.
    """

    def __init__(self, detectors: list[BaseDetector] | None = None) -> None:
        if detectors is not None:
            self.detectors = {d.name: d for d in detectors}
        else:
            self.detectors = dict(_ALL_DETECTORS)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_all(self, contract: "Contract") -> list[Vulnerability]:
        """Run all registered detectors and return sorted vulnerabilities.

        Args:
            contract: Parsed :class:`~src.parser.models.Contract` to analyse.

        Returns:
            Vulnerabilities sorted by severity (CRITICAL first).
        """
        findings: list[Vulnerability] = []
        for detector in self.detectors.values():
            try:
                findings.extend(detector.detect(contract))
            except Exception as exc:  # noqa: BLE001
                # Never let a single detector crash the whole pipeline
                import logging
                logging.getLogger(__name__).warning(
                    "Detector %s raised an error: %s", detector.name, exc
                )
        return sorted(findings, key=lambda v: _SEVERITY_ORDER.get(v.severity, 99))

    def run_detector(self, name: str, contract: "Contract") -> list[Vulnerability]:
        """Run a single detector by name.

        Args:
            name: Detector name (e.g. ``"reentrancy"``).
            contract: Parsed contract to analyse.

        Returns:
            Findings from that detector.

        Raises:
            KeyError: If no detector with *name* is registered.
        """
        if name not in self.detectors:
            raise KeyError(
                f"Unknown detector: '{name}'. "
                f"Available: {sorted(self.detectors)}"
            )
        return self.detectors[name].detect(contract)

    @property
    def detector_names(self) -> list[str]:
        """Return sorted list of registered detector names."""
        return sorted(self.detectors)


def default_runner() -> DetectorRunner:
    """Return a :class:`DetectorRunner` pre-loaded with all built-in detectors."""
    return DetectorRunner()
