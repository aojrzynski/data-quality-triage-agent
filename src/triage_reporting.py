"""Deterministic triage-summary/report helpers for agent mode.

These helpers transform deterministic findings and investigation outputs into a
compact, inspectable triage narrative. They do not infer new issues.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from src.agent_state import ActionRecord, AssumptionRecord, StopRationale
from src.models import Finding


@dataclass
class TriageConclusion:
    """Structured agent triage conclusion built from deterministic evidence."""

    top_issues: list[dict[str, Any]]
    issue_categories: dict[str, int]
    severity_view: dict[str, int]
    investigations: list[dict[str, Any]] = field(default_factory=list)
    key_evidence_snippets: list[str] = field(default_factory=list)
    stop_rationale: dict[str, Any] | None = None
    recommended_next_steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "top_issues": self.top_issues,
            "issue_categories": self.issue_categories,
            "severity_view": self.severity_view,
            "investigations": self.investigations,
            "key_evidence_snippets": self.key_evidence_snippets,
            "stop_rationale": self.stop_rationale,
            "recommended_next_steps": self.recommended_next_steps,
        }


def _severity_sort_key(finding: Finding) -> tuple[int, str, str]:
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    return (order.get(finding.severity, 99), finding.finding_type, finding.column or "")


def build_triage_conclusion(
    findings: list[Finding],
    investigations: list[dict[str, Any]],
    stop_rationale: StopRationale | None,
) -> TriageConclusion:
    issue_categories = dict(sorted(Counter(f.finding_type for f in findings).items()))
    severity_view = dict(sorted(Counter(f.severity for f in findings).items()))

    ranked = sorted(findings, key=_severity_sort_key)
    top_issues = [
        {
            "finding_type": f.finding_type,
            "column": f.column,
            "severity": f.severity,
            "message": f.message,
        }
        for f in ranked[:5]
    ]

    snippets: list[str] = []
    for issue in top_issues[:3]:
        snippets.append(
            f"{issue['severity'].upper()}: {issue['finding_type']}"
            + (f" on {issue['column']}" if issue["column"] else "")
        )

    for inv in investigations:
        if inv.get("status") == "completed":
            snippets.append(inv.get("summary", "Investigation completed."))

    next_steps: list[str] = []
    if issue_categories.get("duplicate_key", 0):
        next_steps.append("Review key uniqueness constraints and deduplicate affected records.")
    if issue_categories.get("numeric_outliers", 0):
        next_steps.append("Validate extreme numeric values against source systems/business thresholds.")
    if issue_categories.get("unexpected_values", 0):
        next_steps.append("Update categorical rule sets or correct invalid category values.")
    if issue_categories.get("missing_values", 0):
        next_steps.append("Assess null-capture paths and backfill required missing fields.")
    if not next_steps:
        next_steps.append("No immediate follow-up checks were indicated by deterministic findings.")

    stop_payload = None
    if stop_rationale is not None:
        stop_payload = {
            "code": stop_rationale.code,
            "reason": stop_rationale.reason,
            "details": stop_rationale.details,
        }

    return TriageConclusion(
        top_issues=top_issues,
        issue_categories=issue_categories,
        severity_view=severity_view,
        investigations=investigations,
        key_evidence_snippets=snippets,
        stop_rationale=stop_payload,
        recommended_next_steps=next_steps,
    )


def build_agent_markdown_report(
    *,
    dataset_name: str,
    intake_summary: dict[str, Any],
    assumptions: list[AssumptionRecord],
    resolved_bindings: dict[str, Any],
    planned_action_names: list[str],
    action_history: list[ActionRecord],
    findings: list[Finding],
    triage: TriageConclusion,
    assumption_review: dict[str, Any] | None = None,
) -> str:
    """Build the agent-mode human-readable report from inspectable artifacts."""
    lines = [
        "# Agent Triage Report",
        "",
        "## Dataset summary",
        f"- Dataset: `{dataset_name}`",
        f"- Rows: {intake_summary.get('row_count', 'unknown')}",
        f"- Columns: {intake_summary.get('column_count', 'unknown')}",
        "",
        "## Intake summary",
        f"- File type: {intake_summary.get('file_type')}",
        f"- Selection mode: {intake_summary.get('selection_mode')}",
        f"- Selected sheet: {intake_summary.get('selected_sheet_name')}",
        f"- Suitability: {intake_summary.get('suitability_status')} (score={intake_summary.get('suitability_score')})",
        "",
        "## Inferred assumptions",
    ]
    if assumptions:
        for assumption in assumptions:
            lines.append(
                f"- {assumption.role_type or assumption.key}: {assumption.column_name or assumption.value} "
                f"({assumption.status}, confidence={assumption.confidence})"
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Resolved bindings"])
    for role_name in ["key", "date", "numeric", "categorical"]:
        binding = resolved_bindings.get(role_name, {})
        columns = binding.get("columns", [])
        if columns:
            lines.append(f"- {role_name}: {', '.join(columns)}")
        else:
            lines.append(f"- {role_name}: none")

    lines.extend(["", "## Planned and completed actions"])
    lines.append(f"- Planned: {', '.join(planned_action_names) if planned_action_names else 'none'}")
    completed = [f"{action.action_name} ({action.status})" for action in action_history]
    lines.append(f"- Executed: {', '.join(completed) if completed else 'none'}")
    for action in action_history:
        details = action.details
        if not isinstance(details, dict):
            continue
        bound_columns = details.get("bound_columns")
        if bound_columns is not None:
            lines.append(f"  - {action.action_name} checked columns: {', '.join(bound_columns) if bound_columns else 'none'}")
        finding_columns = details.get("columns_with_findings")
        if finding_columns is not None:
            lines.append(
                f"  - {action.action_name} columns with findings: {', '.join(finding_columns) if finding_columns else 'none'}"
            )

    lines.extend(["", "## Main findings"])
    lines.append(f"- Total findings: {len(findings)}")
    for issue in triage.top_issues:
        lines.append(
            f"- [{issue['severity'].upper()}] {issue['finding_type']}"
            + (f" ({issue['column']})" if issue["column"] else "")
        )

    lines.extend(["", "## Investigations performed"])
    if triage.investigations:
        for inv in triage.investigations:
            lines.append(f"- {inv.get('action_name')}: {inv.get('status')} — {inv.get('summary')}")
    else:
        lines.append("- none")

    lines.extend(["", "## Notable evidence"])
    if triage.key_evidence_snippets:
        for snippet in triage.key_evidence_snippets:
            lines.append(f"- {snippet}")
    else:
        lines.append("- none")

    lines.extend(["", "## Stop rationale"])
    if triage.stop_rationale:
        lines.append(f"- {triage.stop_rationale['code']}: {triage.stop_rationale['reason']}")
    else:
        lines.append("- none")

    lines.extend(["", "## Suggested next steps"])
    for step in triage.recommended_next_steps:
        lines.append(f"- {step}")

    if assumption_review:
        lines.extend(["", "## Assumption review"])
        lines.append(f"- Enabled: {assumption_review.get('enabled')}")
        for role, decision in assumption_review.get("role_resolution", {}).items():
            lines.append(f"- {role}: {decision}")

    lines.append("")
    return "\n".join(lines)
