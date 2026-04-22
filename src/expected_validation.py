"""Expected-results fixture validation helpers.

This module keeps fixture comparison logic separate from CLI orchestration.
That separation lets deterministic runs, tests, and future agent mode reuse the
same expectation checks without coupling to command-line argument handling.
"""

from __future__ import annotations

from src.models import RunResult


def compare_to_expected(run_result: RunResult, expected_payload: dict) -> list[str]:
    """Compare actual findings to an expected-results fixture payload."""
    messages: list[str] = []
    expected_findings = expected_payload.get("expected_findings", [])

    actual_by_type_and_column = {
        (finding.finding_type, finding.column): finding
        for finding in run_result.findings
    }

    for expected in expected_findings:
        key = (expected["type"], expected.get("column"))
        actual = actual_by_type_and_column.get(key)

        if actual is None:
            messages.append(
                f"Missing expected finding: type={expected['type']}, column={expected.get('column')}"
            )
            continue

        expected_severity = expected.get("severity")
        if expected_severity and actual.severity != expected_severity:
            messages.append(
                f"Severity mismatch for {key}: expected {expected_severity}, got {actual.severity}"
            )

        expected_min_count = expected.get("min_count")
        if expected_min_count is not None:
            actual_missing_count = int(actual.evidence.get("missing_count", 0))
            if actual_missing_count < expected_min_count:
                messages.append(
                    f"Missing count too low for {key}: expected at least {expected_min_count}, got {actual_missing_count}"
                )

        expected_values = expected.get("unexpected_values")
        if expected_values is not None:
            actual_values = actual.evidence.get("unexpected_values", [])
            if sorted(actual_values) != sorted(expected_values):
                messages.append(
                    f"Unexpected values mismatch for {key}: expected {expected_values}, got {actual_values}"
                )

        expected_min_gap_count = expected.get("min_gap_count")
        if expected_min_gap_count is not None:
            actual_gap_count = int(actual.evidence.get("missing_dates_count", 0))
            if actual_gap_count < expected_min_gap_count:
                messages.append(
                    f"Gap count too low for {key}: expected at least {expected_min_gap_count}, got {actual_gap_count}"
                )

        expected_min_outlier_count = expected.get("min_outlier_count")
        if expected_min_outlier_count is not None:
            actual_outlier_count = int(actual.evidence.get("outlier_count", 0))
            if actual_outlier_count < expected_min_outlier_count:
                messages.append(
                    f"Outlier count too low for {key}: expected at least {expected_min_outlier_count}, got {actual_outlier_count}"
                )

        expected_missing_columns = expected.get("missing_columns")
        if expected_missing_columns is not None:
            actual_missing_columns = actual.evidence.get("missing_columns", [])
            if sorted(actual_missing_columns) != sorted(expected_missing_columns):
                messages.append(
                    f"Missing columns mismatch for {key}: expected {expected_missing_columns}, got {actual_missing_columns}"
                )

        expected_unexpected_columns = expected.get("unexpected_columns")
        if expected_unexpected_columns is not None:
            actual_unexpected_columns = actual.evidence.get("unexpected_columns", [])
            if sorted(actual_unexpected_columns) != sorted(expected_unexpected_columns):
                messages.append(
                    f"Unexpected columns mismatch for {key}: expected {expected_unexpected_columns}, got {actual_unexpected_columns}"
                )

    return messages
