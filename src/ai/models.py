"""Dataclasses for AI-generated analysis results."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AIFinding:
    """A vulnerability finding produced by the AI analysis pass."""
    severity: str                    # CRITICAL / HIGH / MEDIUM / LOW / INFO
    title: str
    description: str
    attack_scenario: str             # Step-by-step attack explanation
    affected_code: str               # Code snippet showing the issue
    fix_before: str                  # Vulnerable code (before)
    fix_after: str                   # Fixed code (after)
    fix_explanation: str             # Why this fix works
    real_world_examples: list = field(default_factory=list)  # CVEs / exploit links
    confidence: str = "medium"       # high / medium / low
    confirmed_by_static: bool = False  # True if a static detector also flagged this
    detector_names: list = field(default_factory=list)  # Static detectors that agree


@dataclass
class AIAnalysis:
    """Full AI analysis result for a contract scan."""
    scan_type: str                   # quick / standard / deep
    findings: list = field(default_factory=list)          # list[AIFinding]
    business_logic_notes: str = ""   # Narrative business logic analysis
    centralization_risks: list = field(default_factory=list)  # list[str] summaries
    gas_optimizations: list = field(default_factory=list)     # list[str] suggestions
    model_used: str = ""             # e.g. "claude-sonnet-4-6"
    tokens_used: int = 0
    cost_usd: float = 0.0
    analysis_time_seconds: float = 0.0
    error: Optional[str] = None      # Set if the AI pass failed

    @property
    def succeeded(self) -> bool:
        return self.error is None

    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "CRITICAL")

    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "HIGH")
