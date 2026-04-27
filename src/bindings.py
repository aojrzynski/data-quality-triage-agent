"""Assumption-driven tool binding resolution for agent mode."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

from src.models import AgentConfig
from src.role_inference import RoleInferenceResult

BindingSource = Literal["user_override", "inferred", "config_fallback"]


@dataclass(frozen=True)
class RoleBinding:
    """Resolved columns for one semantic role."""

    role: Literal["key", "date", "numeric", "categorical"]
    columns: list[str]
    source_by_column: dict[str, BindingSource]
    skipped_reason: str | None = None
    ignored_override_columns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "columns": list(self.columns),
            "source_by_column": dict(self.source_by_column),
            "skipped_reason": self.skipped_reason,
            "ignored_override_columns": list(self.ignored_override_columns),
        }


@dataclass(frozen=True)
class AgentExecutionBindings:
    """Complete resolved bindings used by the agent executor for this run."""

    key: RoleBinding
    date: RoleBinding
    numeric: RoleBinding
    categorical: RoleBinding

    def to_dict(self) -> dict:
        return {
            "key": self.key.to_dict(),
            "date": self.date.to_dict(),
            "numeric": self.numeric.to_dict(),
            "categorical": self.categorical.to_dict(),
        }

    def columns_for_tool(self, tool_name: str) -> list[str]:
        mapping = {
            "duplicate_keys": self.key.columns,
            "date_gaps": self.date.columns,
            "numeric_outliers": self.numeric.columns,
            "unexpected_categorical_values": self.categorical.columns,
        }
        return list(mapping.get(tool_name, []))

    def source_map_for_tool(self, tool_name: str) -> dict[str, BindingSource]:
        mapping = {
            "duplicate_keys": self.key.source_by_column,
            "date_gaps": self.date.source_by_column,
            "numeric_outliers": self.numeric.source_by_column,
            "unexpected_categorical_values": self.categorical.source_by_column,
        }
        return dict(mapping.get(tool_name, {}))

    def skipped_reason_for_tool(self, tool_name: str) -> str | None:
        mapping = {
            "duplicate_keys": self.key.skipped_reason,
            "date_gaps": self.date.skipped_reason,
            "numeric_outliers": self.numeric.skipped_reason,
            "unexpected_categorical_values": self.categorical.skipped_reason,
        }
        return mapping.get(tool_name)


def parse_column_override(raw: str | None) -> list[str] | None:
    """Parse a comma-separated override string into normalized column names."""
    if raw is None:
        return None
    return [token.strip() for token in raw.split(",") if token.strip()]


def _resolve_role_binding(
    role: Literal["key", "date", "numeric", "categorical"],
    available_columns: set[str],
    override_columns: list[str] | None,
    inferred_columns: list[str],
    fallback_columns: list[str],
) -> RoleBinding:
    ignored_override = (
        [column for column in override_columns if column not in available_columns]
        if override_columns is not None
        else []
    )

    def _valid(columns: list[str]) -> list[str]:
        seen: set[str] = set()
        valid: list[str] = []
        for column in columns:
            if column in available_columns and column not in seen:
                valid.append(column)
                seen.add(column)
        return valid

    if override_columns is not None:
        valid_override = _valid(override_columns)
        if valid_override:
            return RoleBinding(
                role=role,
                columns=valid_override,
                source_by_column={column: "user_override" for column in valid_override},
                ignored_override_columns=ignored_override,
            )
        if not override_columns:
            return RoleBinding(
                role=role,
                columns=[],
                source_by_column={},
                skipped_reason="Binding was explicitly cleared by user override.",
                ignored_override_columns=[],
            )
        return RoleBinding(
            role=role,
            columns=[],
            source_by_column={},
            skipped_reason="Override was provided but none of the override columns exist in the dataset.",
            ignored_override_columns=ignored_override,
        )

    inferred_valid = _valid(inferred_columns)
    if inferred_valid:
        return RoleBinding(
            role=role,
            columns=inferred_valid,
            source_by_column={column: "inferred" for column in inferred_valid},
            ignored_override_columns=ignored_override,
        )

    fallback_valid = _valid(fallback_columns)
    if fallback_valid:
        return RoleBinding(
            role=role,
            columns=fallback_valid,
            source_by_column={column: "config_fallback" for column in fallback_valid},
            ignored_override_columns=ignored_override,
        )

    return RoleBinding(
        role=role,
        columns=[],
        source_by_column={},
        skipped_reason="No usable binding found from override, inference, or config fallback.",
        ignored_override_columns=ignored_override,
    )


def resolve_agent_execution_bindings(
    df: pd.DataFrame,
    inference_result: RoleInferenceResult,
    config: AgentConfig,
    *,
    key_override: list[str] | None = None,
    date_override: list[str] | None = None,
    numeric_override: list[str] | None = None,
    categorical_override: list[str] | None = None,
) -> AgentExecutionBindings:
    """Resolve execution bindings using override -> inferred -> config fallback."""
    available_columns = {str(column) for column in df.columns}

    return AgentExecutionBindings(
        key=_resolve_role_binding(
            role="key",
            available_columns=available_columns,
            override_columns=key_override,
            inferred_columns=[candidate.column_name for candidate in inference_result.key_candidates],
            fallback_columns=list(config.key_columns),
        ),
        date=_resolve_role_binding(
            role="date",
            available_columns=available_columns,
            override_columns=date_override,
            inferred_columns=[candidate.column_name for candidate in inference_result.date_candidates],
            fallback_columns=list(config.date_gap_columns),
        ),
        numeric=_resolve_role_binding(
            role="numeric",
            available_columns=available_columns,
            override_columns=numeric_override,
            inferred_columns=[candidate.column_name for candidate in inference_result.numeric_measure_candidates],
            fallback_columns=list(config.numeric_outlier_columns),
        ),
        categorical=_resolve_role_binding(
            role="categorical",
            available_columns=available_columns,
            override_columns=categorical_override,
            inferred_columns=[candidate.column_name for candidate in inference_result.categorical_candidates],
            fallback_columns=list(config.categorical_rules.keys()),
        ),
    )
