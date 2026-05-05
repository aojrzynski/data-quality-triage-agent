"""Data quality checks."""

from __future__ import annotations

import pandas as pd

from src.models import AgentConfig, Finding


def _parse_dates(values: pd.Series) -> pd.Series:
    """Parse date-like values while preserving flexible mixed-format support."""
    try:
        return pd.to_datetime(values, errors="coerce", format="mixed")
    except TypeError:
        return pd.to_datetime(values, errors="coerce")


def check_missing_values(df: pd.DataFrame) -> list[Finding]:
    findings: list[Finding] = []

    for column in df.columns:
        missing_count = int(df[column].isna().sum())

        if missing_count > 0:
            findings.append(
                Finding(
                    finding_type="missing_values",
                    column=column,
                    severity="info",
                    message=f"Column '{column}' contains {missing_count} missing values.",
                    evidence={
                        "missing_count": missing_count,
                        "row_count": int(len(df)),
                    },
                )
            )

    return findings


def check_duplicate_keys(df: pd.DataFrame, key_column: str) -> list[Finding]:
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


def check_date_gaps(df: pd.DataFrame, column: str) -> list[Finding]:
    if column not in df.columns:
        return [
            Finding(
                finding_type="missing_column",
                column=column,
                severity="info",
                message=f"Date column '{column}' does not exist in the dataset.",
                evidence={},
            )
        ]

    parsed = _parse_dates(df[column])

    if parsed.dropna().empty:
        return []

    normalized = parsed.dropna().dt.normalize()
    min_date = normalized.min()
    max_date = normalized.max()

    expected_dates = pd.date_range(start=min_date, end=max_date, freq="D")
    present_dates = set(normalized.dt.date)
    missing_dates = [ts.date().isoformat() for ts in expected_dates if ts.date() not in present_dates]

    if not missing_dates:
        return []

    return [
        Finding(
            finding_type="date_gaps",
            column=column,
            severity="info",
            message=f"Column '{column}' has missing dates in the sequence.",
            evidence={
                "missing_dates_count": len(missing_dates),
                "missing_dates": missing_dates[:10],
            },
        )
    ]


def check_numeric_outliers(df: pd.DataFrame, column: str) -> list[Finding]:
    if column not in df.columns:
        return [
            Finding(
                finding_type="missing_column",
                column=column,
                severity="info",
                message=f"Numeric column '{column}' does not exist in the dataset.",
                evidence={},
            )
        ]

    numeric = pd.to_numeric(df[column], errors="coerce").dropna()

    if len(numeric) < 4:
        return []

    q1 = numeric.quantile(0.25)
    q3 = numeric.quantile(0.75)
    iqr = q3 - q1

    if iqr == 0:
        return []

    lower_bound = q1 - (1.5 * iqr)
    upper_bound = q3 + (1.5 * iqr)

    outliers = numeric[(numeric < lower_bound) | (numeric > upper_bound)]

    if outliers.empty:
        return []

    return [
        Finding(
            finding_type="numeric_outliers",
            column=column,
            severity="info",
            message=f"Column '{column}' contains numeric outliers.",
            evidence={
                "outlier_count": int(outliers.count()),
                "lower_bound": round(float(lower_bound), 2),
                "upper_bound": round(float(upper_bound), 2),
                "outlier_values": [round(float(v), 2) for v in outliers.tolist()[:10]],
            },
        )
    ]


def check_schema_surprises(df: pd.DataFrame, expected_columns: list[str]) -> list[Finding]:
    """Compare actual columns against expected columns."""
    if not expected_columns:
        return []

    actual_columns = list(df.columns)
    missing_columns = [column for column in expected_columns if column not in actual_columns]
    unexpected_columns = [column for column in actual_columns if column not in expected_columns]

    if not missing_columns and not unexpected_columns:
        return []

    return [
        Finding(
            finding_type="schema_surprises",
            column=None,
            severity="info",
            message="Dataset columns do not match the expected schema.",
            evidence={
                "missing_columns": missing_columns,
                "unexpected_columns": unexpected_columns,
                "expected_columns": expected_columns,
                "actual_columns": actual_columns,
            },
        )
    ]


def run_checks(df: pd.DataFrame, config: AgentConfig) -> list[Finding]:
    findings: list[Finding] = []

    findings.extend(check_schema_surprises(df, expected_columns=config.expected_columns))
    findings.extend(check_missing_values(df))

    for key_column in config.key_columns:
        findings.extend(check_duplicate_keys(df, key_column=key_column))

    for column, allowed_values in config.categorical_rules.items():
        findings.extend(
            check_unexpected_categorical_values(
                df,
                column=column,
                allowed_values=set(allowed_values),
            )
        )

    for column in config.date_gap_columns:
        findings.extend(check_date_gaps(df, column=column))

    for column in config.numeric_outlier_columns:
        findings.extend(check_numeric_outliers(df, column=column))

    return findings
