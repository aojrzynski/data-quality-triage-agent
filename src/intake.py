"""Input intake and tabular suitability helpers.

This module provides deterministic, inspectable intake behavior for:
- file format detection
- tabular suitability scoring
- XLSX sheet discovery/ranking
- selected dataset context for downstream deterministic checks
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import pandas as pd

from src.io import list_excel_sheets, load_csv, load_excel

SuitabilityStatus = Literal["suitable", "borderline", "unsuitable"]
SelectionMode = Literal["single", "explicit", "auto"]


@dataclass(frozen=True)
class TabularSuitabilityResult:
    """Deterministic suitability assessment for a tabular candidate."""

    status: SuitabilityStatus
    score: int
    reasons: list[str]
    warnings: list[str]
    recommended_action: str
    hard_failure: bool


@dataclass(frozen=True)
class DatasetCandidateSummary:
    """Summary metrics for one dataset candidate (CSV or single XLSX sheet)."""

    candidate_id: str
    row_count: int
    column_count: int
    non_empty_row_count: int
    mostly_blank_row_ratio: float
    usable_column_count: int
    unnamed_column_count: int
    suitability: TabularSuitabilityResult
    ranking_score: float


@dataclass(frozen=True)
class IntakeResult:
    """Top-level intake output used by the CLI and downstream pipeline."""

    file_type: Literal["csv", "xlsx"]
    selection_mode: SelectionMode
    candidates: list[DatasetCandidateSummary]
    selected_candidate: DatasetCandidateSummary
    selected_sheet_name: str | None
    df: pd.DataFrame = field(repr=False)


def _is_unnamed_header(column_name: object) -> bool:
    normalized = str(column_name).strip().lower()
    return (
        normalized == ""
        or normalized.startswith("unnamed")
        or normalized.startswith("column")
        or normalized in {"none", "nan"}
    )


def assess_tabular_suitability(df: pd.DataFrame) -> TabularSuitabilityResult:
    """Compute a deterministic suitability score for tabular analysis.

    Intake is a guardrail: it prevents downstream checks from pretending that
    clearly non-tabular inputs are valid analysis targets.
    """
    row_count = int(len(df))
    column_count = int(len(df.columns))

    if row_count == 0 or column_count == 0:
        return TabularSuitabilityResult(
            status="unsuitable",
            score=0,
            reasons=["Dataset is empty."],
            warnings=["No tabular records found."],
            recommended_action="Provide a non-empty table with headers and data rows.",
            hard_failure=True,
        )

    non_empty_mask = df.notna().any(axis=1)
    non_empty_row_count = int(non_empty_mask.sum())
    if non_empty_row_count == 0:
        return TabularSuitabilityResult(
            status="unsuitable",
            score=0,
            reasons=["All rows are blank."],
            warnings=["Sheet appears to have no usable data rows."],
            recommended_action="Choose another sheet or provide a populated table.",
            hard_failure=True,
        )

    blank_row_ratio = float(1 - (non_empty_row_count / max(row_count, 1)))
    unnamed_column_count = sum(_is_unnamed_header(column) for column in df.columns)

    usable_column_count = 0
    for column in df.columns:
        non_null = int(df[column].notna().sum())
        if non_null >= 2:
            usable_column_count += 1

    reasons: list[str] = []
    warnings: list[str] = []
    score = 100

    if column_count < 2:
        score -= 35
        reasons.append("Very few columns for meaningful checks.")

    if non_empty_row_count < 3:
        score -= 30
        reasons.append("Very few non-empty rows.")

    if blank_row_ratio > 0.60:
        score -= 20
        warnings.append("Many rows are mostly blank.")

    unnamed_ratio = unnamed_column_count / max(column_count, 1)
    if unnamed_ratio > 0.5:
        score -= 25
        reasons.append("Most headers are unnamed/placeholder.")

    if usable_column_count < 2:
        score -= 25
        reasons.append("Too few columns have enough non-null values.")

    score = max(0, min(100, score))

    if score >= 70:
        status: SuitabilityStatus = "suitable"
        action = "Proceed with deterministic checks."
    elif score >= 40:
        status = "borderline"
        action = "Proceed cautiously; results may be limited."
        warnings.append("Dataset may be weak for full-quality triage.")
    else:
        status = "unsuitable"
        action = "Prefer another sheet or cleaner tabular input before running checks."

    return TabularSuitabilityResult(
        status=status,
        score=score,
        reasons=reasons,
        warnings=warnings,
        recommended_action=action,
        hard_failure=False,
    )


def _build_candidate(candidate_id: str, df: pd.DataFrame) -> DatasetCandidateSummary:
    suitability = assess_tabular_suitability(df)
    row_count = int(len(df))
    column_count = int(len(df.columns))
    non_empty_row_count = int(df.notna().any(axis=1).sum())
    mostly_blank_row_ratio = float(1 - (non_empty_row_count / max(row_count, 1)))
    unnamed_column_count = sum(_is_unnamed_header(column) for column in df.columns)

    usable_column_count = 0
    for column in df.columns:
        if int(df[column].notna().sum()) >= 2:
            usable_column_count += 1

    ranking_score = (
        suitability.score
        + min(non_empty_row_count, 25)
        + min(usable_column_count * 2, 20)
        - (unnamed_column_count * 2)
    )

    return DatasetCandidateSummary(
        candidate_id=candidate_id,
        row_count=row_count,
        column_count=column_count,
        non_empty_row_count=non_empty_row_count,
        mostly_blank_row_ratio=mostly_blank_row_ratio,
        usable_column_count=usable_column_count,
        unnamed_column_count=unnamed_column_count,
        suitability=suitability,
        ranking_score=ranking_score,
    )


def inspect_and_select_dataset(path: str | Path, sheet_name: str | int | None = None) -> IntakeResult:
    """Inspect input and select the best candidate dataset for checks."""
    input_path = Path(path)
    suffix = input_path.suffix.lower()

    if suffix == ".csv":
        df = load_csv(input_path)
        candidate = _build_candidate(candidate_id="csv", df=df)
        return IntakeResult(
            file_type="csv",
            selection_mode="single",
            candidates=[candidate],
            selected_candidate=candidate,
            selected_sheet_name=None,
            df=df,
        )

    if suffix != ".xlsx":
        raise ValueError(
            f"Unsupported file format: {suffix}. Supported formats are .csv and .xlsx"
        )

    if sheet_name is not None:
        explicit_df = load_excel(input_path, sheet_name=sheet_name)

        explicit_name = str(sheet_name)
        if isinstance(sheet_name, int):
            sheet_names = list_excel_sheets(input_path)
            if 0 <= sheet_name < len(sheet_names):
                explicit_name = sheet_names[sheet_name]

        candidate = _build_candidate(candidate_id=explicit_name, df=explicit_df)
        return IntakeResult(
            file_type="xlsx",
            selection_mode="explicit",
            candidates=[candidate],
            selected_candidate=candidate,
            selected_sheet_name=explicit_name,
            df=explicit_df,
        )

    sheet_names = list_excel_sheets(input_path)
    if not sheet_names:
        raise ValueError(f"Workbook has no sheets: {input_path}")

    evaluated: list[tuple[DatasetCandidateSummary, pd.DataFrame]] = []
    for sheet in sheet_names:
        sheet_df = load_excel(input_path, sheet_name=sheet)
        evaluated.append((_build_candidate(candidate_id=sheet, df=sheet_df), sheet_df))

    evaluated.sort(
        key=lambda item: (
            item[0].ranking_score,
            item[0].non_empty_row_count,
            item[0].usable_column_count,
        ),
        reverse=True,
    )

    selected_summary, selected_df = evaluated[0]

    return IntakeResult(
        file_type="xlsx",
        selection_mode="auto",
        candidates=[summary for summary, _ in evaluated],
        selected_candidate=selected_summary,
        selected_sheet_name=selected_summary.candidate_id,
        df=selected_df,
    )
