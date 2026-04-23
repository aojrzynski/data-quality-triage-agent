"""Deterministic second-pass investigation helpers for agent mode."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.models import Finding


@dataclass(frozen=True)
class InvestigationResult:
    """Structured output for one investigation action."""

    action_name: str
    finding_family: str
    status: str
    summary: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_name": self.action_name,
            "finding_family": self.finding_family,
            "status": self.status,
            "summary": self.summary,
            "details": self.details,
        }


def _sample_columns(df: pd.DataFrame, target_column: str | None, max_context_columns: int = 2) -> list[str]:
    if target_column is None or target_column not in df.columns:
        return list(df.columns[: max_context_columns + 1])

    context = [column for column in df.columns if column != target_column][:max_context_columns]
    return [target_column, *context]


def _rows_to_records(df: pd.DataFrame, columns: list[str], limit: int) -> list[dict[str, Any]]:
    sample = df.loc[:, columns].head(limit).copy()
    sample.insert(0, "row_index", sample.index.astype(int))
    return sample.to_dict(orient="records")


def investigate_duplicate_keys(df: pd.DataFrame, finding: Finding, max_rows: int = 5) -> InvestigationResult:
    column = finding.column
    if column is None or column not in df.columns:
        return InvestigationResult(
            action_name="investigate_duplicate_keys",
            finding_family="duplicate_key",
            status="skipped",
            summary="Duplicate-key investigation skipped because the target column was unavailable.",
            details={"column": column, "reason": "missing_target_column"},
        )

    duplicate_mask = df.duplicated(subset=[column], keep=False)
    duplicate_rows = df.loc[duplicate_mask]
    duplicate_counts = duplicate_rows[column].astype(str).value_counts().to_dict()

    sample_columns = _sample_columns(df, column)
    sample_rows = _rows_to_records(duplicate_rows, sample_columns, max_rows)

    return InvestigationResult(
        action_name="investigate_duplicate_keys",
        finding_family="duplicate_key",
        status="completed",
        summary=f"Found {len(duplicate_rows)} rows participating in duplicate values for '{column}'.",
        details={
            "column": column,
            "duplicate_value_examples": [
                {"value": value, "count": int(count)}
                for value, count in list(duplicate_counts.items())[:5]
            ],
            "affected_row_count": int(len(duplicate_rows)),
            "sample_rows": sample_rows,
        },
    )


def investigate_numeric_outliers(df: pd.DataFrame, finding: Finding, max_rows: int = 5) -> InvestigationResult:
    column = finding.column
    if column is None or column not in df.columns:
        return InvestigationResult(
            action_name="investigate_numeric_outliers",
            finding_family="numeric_outliers",
            status="skipped",
            summary="Numeric outlier investigation skipped because the target column was unavailable.",
            details={"column": column, "reason": "missing_target_column"},
        )

    numeric = pd.to_numeric(df[column], errors="coerce")
    lower_bound = float(finding.evidence.get("lower_bound", float("nan")))
    upper_bound = float(finding.evidence.get("upper_bound", float("nan")))

    if pd.isna(lower_bound) or pd.isna(upper_bound):
        q1 = numeric.dropna().quantile(0.25)
        q3 = numeric.dropna().quantile(0.75)
        iqr = q3 - q1
        lower_bound = float(q1 - (1.5 * iqr))
        upper_bound = float(q3 + (1.5 * iqr))

    outlier_mask = (numeric < lower_bound) | (numeric > upper_bound)
    outlier_rows = df.loc[outlier_mask.fillna(False)].copy()

    sample_columns = _sample_columns(df, column)
    sample_rows = _rows_to_records(outlier_rows, sample_columns, max_rows)

    return InvestigationResult(
        action_name="investigate_numeric_outliers",
        finding_family="numeric_outliers",
        status="completed",
        summary=f"Found {len(outlier_rows)} outlier rows for '{column}' using IQR bounds.",
        details={
            "column": column,
            "lower_bound": round(lower_bound, 2),
            "upper_bound": round(upper_bound, 2),
            "affected_row_count": int(len(outlier_rows)),
            "sample_rows": sample_rows,
        },
    )


def investigate_unexpected_categorical_values(
    df: pd.DataFrame,
    finding: Finding,
    max_rows: int = 5,
) -> InvestigationResult:
    column = finding.column
    if column is None or column not in df.columns:
        return InvestigationResult(
            action_name="investigate_unexpected_categorical_values",
            finding_family="unexpected_values",
            status="skipped",
            summary="Categorical investigation skipped because the target column was unavailable.",
            details={"column": column, "reason": "missing_target_column"},
        )

    unexpected_values = [str(value) for value in finding.evidence.get("unexpected_values", [])]
    as_text = df[column].astype(str)
    unexpected_mask = as_text.isin(unexpected_values)

    unexpected_rows = df.loc[unexpected_mask]
    frequencies = as_text[unexpected_mask].value_counts().to_dict()

    sample_columns = _sample_columns(df, column)
    sample_rows = _rows_to_records(unexpected_rows, sample_columns, max_rows)

    return InvestigationResult(
        action_name="investigate_unexpected_categorical_values",
        finding_family="unexpected_values",
        status="completed",
        summary=f"Found {len(unexpected_rows)} rows containing unexpected values for '{column}'.",
        details={
            "column": column,
            "unexpected_values": unexpected_values,
            "unexpected_value_frequencies": {
                value: int(frequencies.get(value, 0)) for value in unexpected_values
            },
            "affected_row_count": int(len(unexpected_rows)),
            "sample_rows": sample_rows,
        },
    )


def investigate_missing_values(df: pd.DataFrame, finding: Finding, max_rows: int = 5) -> InvestigationResult:
    column = finding.column
    if column is None or column not in df.columns:
        return InvestigationResult(
            action_name="investigate_missing_values",
            finding_family="missing_values",
            status="skipped",
            summary="Missing-values investigation skipped because the target column was unavailable.",
            details={"column": column, "reason": "missing_target_column"},
        )

    missing_rows = df.loc[df[column].isna()]
    sample_columns = _sample_columns(df, column)
    sample_rows = _rows_to_records(missing_rows, sample_columns, max_rows)

    return InvestigationResult(
        action_name="investigate_missing_values",
        finding_family="missing_values",
        status="completed",
        summary=f"Found {len(missing_rows)} rows where '{column}' is missing.",
        details={
            "column": column,
            "missing_count": int(len(missing_rows)),
            "sample_rows": sample_rows,
        },
    )
