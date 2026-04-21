"""Severity scoring logic.

This module decides how serious a finding is.
Detection and severity are kept separate on purpose.
"""

from __future__ import annotations

from src.models import Finding


def score_finding(finding: Finding) -> Finding:
    """Assign a severity level to a finding."""
    evidence = finding.evidence

    if finding.finding_type == "duplicate_key":
        finding.severity = "critical"
        return finding

    if finding.finding_type == "missing_values":
        missing_count = int(evidence.get("missing_count", 0))
        row_count = int(evidence.get("row_count", 0))
        missing_pct = (missing_count / row_count) if row_count else 0

        if finding.column == "customer_id" and missing_pct >= 0.10:
            finding.severity = "high"
        elif missing_pct >= 0.10:
            finding.severity = "medium"
        else:
            finding.severity = "low"

        return finding

    if finding.finding_type == "unexpected_values":
        finding.severity = "medium"
        return finding

    if finding.finding_type in {"missing_key_column", "missing_column"}:
        finding.severity = "high"
        return finding

    finding.severity = "info"
    return finding


def score_findings(findings: list[Finding]) -> list[Finding]:
    """Score a list of findings."""
    return [score_finding(finding) for finding in findings]