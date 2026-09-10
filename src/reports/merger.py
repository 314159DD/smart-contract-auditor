"""Merge static and AI findings into a unified Finding list."""
from src.reports.models import Finding


def merge_findings(static_findings: list, ai_analysis=None) -> list:
    """
    Combine static Vulnerability objects and AI AIFinding objects into Finding list.
    Deduplicates entries where static and AI agree on the same issue.
    """
    findings: list[Finding] = []
    seen_titles: set[str] = set()

    # Static findings first
    for v in static_findings:
        key = v.title.lower().strip()
        seen_titles.add(key)
        findings.append(Finding(
            severity=v.severity,
            title=v.title,
            description=v.description,
            location=v.location,
            recommendation=v.recommendation,
            confidence=v.confidence,
            source="static",
            detector=v.detector,
            cwe_id=v.cwe_id,
            references=list(v.references),
        ))

    # AI findings
    if ai_analysis and ai_analysis.succeeded:
        for af in ai_analysis.findings:
            key = af.title.lower().strip()
            if key in seen_titles:
                # Upgrade the existing finding with AI enrichment
                for f in findings:
                    if f.title.lower().strip() == key:
                        f.source = "both"
                        f.attack_scenario = f.attack_scenario or af.attack_scenario
                        f.fix_before = f.fix_before or af.fix_before
                        f.fix_after = f.fix_after or af.fix_after
                        f.fix_explanation = f.fix_explanation or af.fix_explanation
                        f.references = f.references or af.real_world_examples
                        # Upgrade confidence if AI confirms
                        if af.confidence == "high" and f.confidence != "high":
                            f.confidence = "high"
                        break
            else:
                seen_titles.add(key)
                findings.append(Finding(
                    severity=af.severity,
                    title=af.title,
                    description=af.description,
                    location="AI analysis",
                    recommendation=af.fix_explanation or "Apply the suggested fix.",
                    confidence=af.confidence,
                    source="ai",
                    attack_scenario=af.attack_scenario,
                    fix_before=af.fix_before,
                    fix_after=af.fix_after,
                    fix_explanation=af.fix_explanation,
                    references=list(af.real_world_examples),
                    confirmed_by_static=af.confirmed_by_static,
                ))

    # Sort by severity
    _sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    findings.sort(key=lambda f: _sev_order.get(f.severity, 99))
    return findings
