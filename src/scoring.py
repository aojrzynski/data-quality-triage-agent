"""Severity scoring logic."""

from __future__ import annotations

from src.models import Finding


SEVERITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
}


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

    if finding.finding_type == "date_gaps":
        gap_count = int(evidence.get("missing_dates_count", 0))
        finding.severity = "high" if gap_count > 3 else "medium"
        return finding

    if finding.finding_type == "numeric_outliers":
        outlier_count = int(evidence.get("outlier_count", 0))
        finding.severity = "high" if outlier_count > 2 else "medium"
        return finding

    if finding.finding_type in {"missing_key_column", "missing_column"}:
        finding.severity = "high"
        return finding

    finding.severity = "info"
    return finding


def score_findings(findings: list[Finding]) -> list[Finding]:
    """Score and sort a list of findings."""
    scored = [score_finding(finding) for finding in findings]

    return sorted(
        scored,
        key=lambda finding: (
            SEVERITY_ORDER.get(finding.severity, 999),
            finding.finding_type,
            finding.column or "",
        ),
    )