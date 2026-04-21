"""Data quality checks.

This module contains simple deterministic checks.
These checks are the real source of truth for issue detection.
The LLM layer, if added later, should explain findings rather than discover them.
"""

from __future__ import annotations

import pandas as pd

from src.models import Finding


def check_missing_values(df: pd.DataFrame) -> list[Finding]:
    """Find columns with missing values."""
    findings: list[Finding] = []

    for column in df.columns:
        missing_count = int(df[column].isna().sum())

        if missing_count > 0:
            findings.append(
                Finding(
                    finding_type="missing_values",
                    column=column,
                    severity="info",  # temporary; real severity comes later
                    message=f"Column '{column}' contains {missing_count} missing values.",
                    evidence={
                        "missing_count": missing_count,
                        "row_count": int(len(df)),
                    },
                )
            )

    return findings


def check_duplicate_keys(df: pd.DataFrame, key_column: str) -> list[Finding]:
    """Find duplicate values in a key column."""
    if key_column not in df.columns:
        return [
            Finding(
                finding_type="missing_key_column",
                column=key_column,
                severity="info",
                message=f"Key column '{key_column}' does not exist in the dataset.",
                evidence={},
            )
        ]

    duplicate_mask = df.duplicated(subset=[key_column], keep=False)
    duplicate_count = int(duplicate_mask.sum())

    if duplicate_count == 0:
        return []

    duplicate_values = (
        df.loc[duplicate_mask, key_column]
        .astype(str)
        .value_counts()
        .to_dict()
    )

    return [
        Finding(
            finding_type="duplicate_key",
            column=key_column,
            severity="info",
            message=f"Key column '{key_column}' contains duplicate values.",
            evidence={
                "duplicate_row_count": duplicate_count,
                "duplicate_values": duplicate_values,
            },
        )
    ]


def check_unexpected_categorical_values(
    df: pd.DataFrame,
    column: str,
    allowed_values: set[str],
) -> list[Finding]:
    """Find values in a categorical column that are not in the allowed set."""
    if column not in df.columns:
        return [
            Finding(
                finding_type="missing_column",
                column=column,
                severity="info",
                message=f"Categorical column '{column}' does not exist in the dataset.",
                evidence={},
            )
        ]

    non_null_values = set(df[column].dropna().astype(str).unique())
    unexpected_values = sorted(non_null_values - allowed_values)

    if not unexpected_values:
        return []

    return [
        Finding(
            finding_type="unexpected_values",
            column=column,
            severity="info",
            message=f"Column '{column}' contains unexpected categorical values.",
            evidence={
                "unexpected_values": unexpected_values,
                "allowed_values": sorted(allowed_values),
            },
        )
    ]


def run_checks(df: pd.DataFrame) -> list[Finding]:
    """Run the first set of hard-coded checks for the MVP.

    For now, this function is deliberately simple and explicit.
    Later, we can make it more flexible and configurable.
    """
    findings: list[Finding] = []

    findings.extend(check_missing_values(df))
    findings.extend(check_duplicate_keys(df, key_column="order_id"))
    findings.extend(
        check_unexpected_categorical_values(
            df,
            column="status",
            allowed_values={"pending", "shipped", "delivered", "cancelled"},
        )
    )

    return findings