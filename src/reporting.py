"""Report generation logic."""

from __future__ import annotations

from src.models import RunResult


def build_markdown_report(run_result: RunResult) -> str:
    """Create a Markdown report for one agent run."""
    profile = run_result.profile

    lines = [
        "# Data Quality Triage Report",
        "",
        "## Dataset",
        f"- Name: `{run_result.dataset_name}`",
        f"- Rows: {profile.row_count}",
        f"- Columns: {profile.column_count}",
        "",
        "## Findings Summary",
        f"- Total findings: {len(run_result.findings)}",
        "",
    ]

    if run_result.findings:
        lines.append("## Findings")
        lines.append("")

        for index, finding in enumerate(run_result.findings, start=1):
            lines.extend(
                [
                    f"### {index}. {finding.finding_type}",
                    f"- Column: `{finding.column}`" if finding.column else "- Column: _None_",
                    f"- Severity: `{finding.severity}`",
                    f"- Message: {finding.message}",
                ]
            )

            if finding.evidence:
                lines.append("- Evidence:")
                for key, value in finding.evidence.items():
                    lines.append(f"  - `{key}`: `{value}`")

            lines.append("")
    else:
        lines.extend(
            [
                "## Findings",
                "_No findings detected._",
                "",
            ]
        )

    lines.extend(
        [
            "## Columns",
            "",
        ]
    )

    for column in profile.columns:
        dtype = profile.inferred_dtypes[column]
        null_count = profile.null_counts[column]
        unique_count = profile.unique_counts[column]

        lines.extend(
            [
                f"### `{column}`",
                f"- Type: `{dtype}`",
                f"- Null count: {null_count}",
                f"- Unique count: {unique_count}",
                "",
            ]
        )

    return "\n".join(lines)