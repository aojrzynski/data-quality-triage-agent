"""Deterministic column role inference for agent assumptions.

Inference is intentionally heuristic and inspectable. It suggests likely roles,
but does not directly detect data quality issues; deterministic checks remain
the source of truth for issue detection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

from src.agent_state import AssumptionRecord

RoleType = Literal["key", "date", "numeric_measure", "categorical"]


@dataclass(frozen=True)
class ColumnRoleCandidate:
    """One inferred role candidate for a specific column."""

    role_type: RoleType
    column_name: str
    confidence: float
    confidence_band: Literal["low", "medium", "high"]
    source: str = "rule_based_inference"
    status: Literal["inferred", "auto_accepted", "user_confirmed", "user_overridden"] = "inferred"
    notes: str | None = None
    evidence: dict[str, float | int | str] = field(default_factory=dict)


@dataclass(frozen=True)
class RoleInferenceResult:
    """Structured inference output grouped by role and as assumptions."""

    key_candidates: list[ColumnRoleCandidate]
    date_candidates: list[ColumnRoleCandidate]
    numeric_measure_candidates: list[ColumnRoleCandidate]
    categorical_candidates: list[ColumnRoleCandidate]
    assumptions: list[AssumptionRecord]


_KEY_TOKENS = {"id", "key", "code", "uuid", "reference", "ref", "number", "num"}
_DATE_TOKENS = {"date", "time", "timestamp", "dt", "asof", "created", "updated"}
_NUMERIC_TOKENS = {
    "amount",
    "value",
    "total",
    "price",
    "qty",
    "quantity",
    "count",
    "balance",
    "score",
    "notional",
    "rate",
    "cost",
}
_CATEGORICAL_TOKENS = {"type", "status", "category", "region", "segment", "class", "bucket"}


def _token_matches(column_name: str, vocab: set[str]) -> bool:
    normalized = column_name.strip().lower().replace("-", "_").replace(" ", "_")
    parts = [token for token in normalized.split("_") if token]
    return any(part in vocab for part in parts)


def _confidence_band(score: float) -> Literal["low", "medium", "high"]:
    if score >= 0.75:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)


def _column_stats(series: pd.Series) -> dict[str, float]:
    """Collect deterministic per-column signals used by role heuristics."""
    non_null = series.dropna()
    non_null_count = int(non_null.shape[0])
    total_count = int(series.shape[0])
    unique_count = int(non_null.nunique(dropna=True)) if non_null_count > 0 else 0

    numeric = pd.to_numeric(non_null, errors="coerce")
    numeric_non_null_count = int(numeric.notna().sum())

    parsed_dates = pd.to_datetime(non_null, errors="coerce", format="mixed")
    parsed_date_count = int(parsed_dates.notna().sum())

    average_length = 0.0
    if non_null_count:
        average_length = float(non_null.astype(str).str.len().mean())

    return {
        "row_count": float(total_count),
        "non_null_ratio": _safe_ratio(non_null_count, total_count),
        "uniqueness_ratio": _safe_ratio(unique_count, non_null_count),
        "duplicate_ratio": _safe_ratio(non_null_count - unique_count, non_null_count),
        "numeric_ratio": _safe_ratio(numeric_non_null_count, non_null_count),
        "parseable_date_ratio": _safe_ratio(parsed_date_count, non_null_count),
        "average_length": average_length,
    }


def _candidate(
    role_type: RoleType,
    column_name: str,
    score: float,
    notes: str,
    evidence: dict[str, float],
) -> ColumnRoleCandidate:
    confidence = round(max(0.0, min(score, 1.0)), 2)
    return ColumnRoleCandidate(
        role_type=role_type,
        column_name=column_name,
        confidence=confidence,
        confidence_band=_confidence_band(confidence),
        notes=notes,
        evidence={k: round(v, 3) for k, v in evidence.items()},
    )


def infer_column_roles(df: pd.DataFrame) -> RoleInferenceResult:
    """Infer likely semantic roles for columns using deterministic heuristics.

    These scores are signals, not proof. Results feed assumptions and planning,
    and uncertainty is surfaced through confidence/evidence for user review.
    """
    key_candidates: list[ColumnRoleCandidate] = []
    date_candidates: list[ColumnRoleCandidate] = []
    numeric_candidates: list[ColumnRoleCandidate] = []
    categorical_candidates: list[ColumnRoleCandidate] = []

    for column in df.columns:
        column_name = str(column)
        stats = _column_stats(df[column])
        non_null_ratio = stats["non_null_ratio"]
        uniqueness_ratio = stats["uniqueness_ratio"]
        duplicate_ratio = stats["duplicate_ratio"]
        numeric_ratio = stats["numeric_ratio"]
        date_ratio = stats["parseable_date_ratio"]
        avg_len = stats["average_length"]

        # Key heuristic: reward uniqueness/completeness, penalize measure/date cues.
        key_score = 0.0
        if _token_matches(column_name, _KEY_TOKENS):
            key_score += 0.35
        if uniqueness_ratio >= 0.98:
            key_score += 0.4
        elif uniqueness_ratio >= 0.9:
            key_score += 0.25
        if non_null_ratio >= 0.98:
            key_score += 0.15
        elif non_null_ratio >= 0.9:
            key_score += 0.08
        if duplicate_ratio <= 0.02:
            key_score += 0.1
        if _token_matches(column_name, _NUMERIC_TOKENS):
            key_score -= 0.25
        if date_ratio >= 0.8:
            key_score -= 0.2
        if key_score >= 0.55:
            key_candidates.append(
                _candidate(
                    "key",
                    column_name,
                    key_score,
                    notes="High uniqueness + low duplication with key-like naming.",
                    evidence={
                        "non_null_ratio": non_null_ratio,
                        "uniqueness_ratio": uniqueness_ratio,
                        "duplicate_ratio": duplicate_ratio,
                    },
                )
            )

        # Date heuristic: combine parseability with date-like naming.
        date_score = 0.0
        if _token_matches(column_name, _DATE_TOKENS):
            date_score += 0.3
        if date_ratio >= 0.9:
            date_score += 0.45
        elif date_ratio >= 0.6:
            date_score += 0.25
        elif date_ratio >= 0.3:
            date_score += 0.1
        if non_null_ratio >= 0.5:
            date_score += 0.1
        if numeric_ratio > 0.95 and not _token_matches(column_name, _DATE_TOKENS):
            date_score -= 0.25
        if date_score >= 0.5:
            date_candidates.append(
                _candidate(
                    "date",
                    column_name,
                    date_score,
                    notes="Substantial datetime parseability and/or date-like naming.",
                    evidence={
                        "parseable_date_ratio": date_ratio,
                        "non_null_ratio": non_null_ratio,
                    },
                )
            )

        # Numeric heuristic: favor coercible measure-like columns.
        numeric_score = 0.0
        if _token_matches(column_name, _NUMERIC_TOKENS):
            numeric_score += 0.3
        if numeric_ratio >= 0.95:
            numeric_score += 0.45
        elif numeric_ratio >= 0.7:
            numeric_score += 0.25
        if non_null_ratio >= 0.6:
            numeric_score += 0.1
        if uniqueness_ratio < 0.05:
            numeric_score -= 0.15
        if date_ratio >= 0.8 and _token_matches(column_name, _DATE_TOKENS):
            numeric_score -= 0.35
        if numeric_score >= 0.5:
            numeric_candidates.append(
                _candidate(
                    "numeric_measure",
                    column_name,
                    numeric_score,
                    notes="Numeric coercion rate and measure-like naming are strong.",
                    evidence={
                        "numeric_ratio": numeric_ratio,
                        "non_null_ratio": non_null_ratio,
                        "uniqueness_ratio": uniqueness_ratio,
                    },
                )
            )

        # Categorical heuristic: favor repeated lower-cardinality values.
        categorical_score = 0.0
        if _token_matches(column_name, _CATEGORICAL_TOKENS):
            categorical_score += 0.15
        if 0.02 <= uniqueness_ratio <= 0.5:
            categorical_score += 0.35
        elif uniqueness_ratio <= 0.8:
            categorical_score += 0.15
        if (1.0 - uniqueness_ratio) >= 0.4:
            categorical_score += 0.25
        if non_null_ratio >= 0.5:
            categorical_score += 0.1
        if avg_len > 30 and uniqueness_ratio > 0.7:
            categorical_score -= 0.35
        if numeric_ratio > 0.8:
            categorical_score -= 0.25
        if date_ratio > 0.8:
            categorical_score -= 0.25
        if categorical_score >= 0.45:
            categorical_candidates.append(
                _candidate(
                    "categorical",
                    column_name,
                    categorical_score,
                    notes="Repeated string-like values with manageable cardinality.",
                    evidence={
                        "uniqueness_ratio": uniqueness_ratio,
                        "non_null_ratio": non_null_ratio,
                        "average_length": avg_len,
                    },
                )
            )

    key_candidates = sorted(key_candidates, key=lambda item: item.confidence, reverse=True)[:3]
    date_candidates = sorted(date_candidates, key=lambda item: item.confidence, reverse=True)[:3]
    numeric_candidates = sorted(numeric_candidates, key=lambda item: item.confidence, reverse=True)[:5]
    categorical_candidates = sorted(
        categorical_candidates, key=lambda item: item.confidence, reverse=True
    )[:5]

    assumptions: list[AssumptionRecord] = []
    for candidate in [
        *key_candidates,
        *date_candidates,
        *numeric_candidates,
        *categorical_candidates,
    ]:
        assumptions.append(
            AssumptionRecord(
                key=f"{candidate.role_type}:{candidate.column_name}",
                value=True,
                role_type=candidate.role_type,
                column_name=candidate.column_name,
                confidence=candidate.confidence,
                status="inferred",
                source=candidate.source,
                notes=candidate.notes,
                evidence=dict(candidate.evidence),
            )
        )

    return RoleInferenceResult(
        key_candidates=key_candidates,
        date_candidates=date_candidates,
        numeric_measure_candidates=numeric_candidates,
        categorical_candidates=categorical_candidates,
        assumptions=assumptions,
    )
