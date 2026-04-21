"""Core internal models for the Data Quality Triage Agent."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DatasetProfile:
    """Basic descriptive information about a dataset."""

    dataset_name: str
    row_count: int
    column_count: int
    columns: list[str]
    inferred_dtypes: dict[str, str]
    null_counts: dict[str, int]
    unique_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Finding:
    """Represents one data quality issue."""

    finding_type: str
    column: str | None
    severity: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentConfig:
    """Configuration for which checks to run and how to run them."""

    key_columns: list[str] = field(default_factory=list)
    categorical_rules: dict[str, list[str]] = field(default_factory=dict)
    date_gap_columns: list[str] = field(default_factory=list)
    numeric_outlier_columns: list[str] = field(default_factory=list)
    expected_columns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentConfig":
        return cls(
            key_columns=list(payload.get("key_columns", [])),
            categorical_rules={
                str(column): list(values)
                for column, values in payload.get("categorical_rules", {}).items()
            },
            date_gap_columns=list(payload.get("date_gap_columns", [])),
            numeric_outlier_columns=list(payload.get("numeric_outlier_columns", [])),
            expected_columns=list(payload.get("expected_columns", [])),
        )


@dataclass
class RunResult:
    """Top-level output object for one run of the agent."""

    dataset_name: str
    profile: DatasetProfile
    findings: list[Finding]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "profile": self.profile.to_dict(),
            "findings": [finding.to_dict() for finding in self.findings],
        }