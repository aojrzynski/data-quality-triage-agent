"""Core internal models for the Data Quality Triage Agent.

These models keep the rest of the code consistent.
Instead of passing around loose dictionaries everywhere,
we define a few clear shapes for the important data.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DatasetProfile:
    """Basic descriptive information about a dataset.

    This is not a list of data quality problems.
    It is just a structured summary of what the file contains.
    """

    dataset_name: str
    row_count: int
    column_count: int
    columns: list[str]
    inferred_dtypes: dict[str, str]
    null_counts: dict[str, int]
    unique_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Convert the profile to a plain dictionary."""
        return asdict(self)


@dataclass
class Finding:
    """Represents one data quality issue.

    We are not using this fully yet, but defining it now gives us a stable
    shape for later milestones.
    """

    finding_type: str
    column: str | None
    severity: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert the finding to a plain dictionary."""
        return asdict(self)


@dataclass
class RunResult:
    """Top-level output object for one run of the agent.

    This lets us save one structured JSON file containing:
    - input dataset details
    - profile summary
    - findings (empty for now)
    """

    dataset_name: str
    profile: DatasetProfile
    findings: list[Finding]

    def to_dict(self) -> dict[str, Any]:
        """Convert the full run result to a plain dictionary."""
        return {
            "dataset_name": self.dataset_name,
            "profile": self.profile.to_dict(),
            "findings": [finding.to_dict() for finding in self.findings],
        }