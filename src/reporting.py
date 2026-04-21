"""Report generation logic.

For now, this module creates a very simple Markdown summary.
Later, it will include findings and recommendations.
"""

from __future__ import annotations

from src.models import RunResult


def build_markdown_report(run_result: RunResult) -> str:
    """Create a simple Markdown report for one agent run."""
    profile = run_result.profile

    lines = [
        "# Data Quality Triage Report",
        "",
        f"## Dataset",
        f"- Name: `{run_result.dataset_name}`",
        f"- Rows: {profile.row_count}",
        f"- Columns: {profile.column_count}",
        "",
        "## Columns",
    ]

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

    lines.extend(
        [
            "## Findings",
            "_No findings yet. Checks will be added in the next milestone._",
            "",
        ]
    )

    return "\n".join(lines)