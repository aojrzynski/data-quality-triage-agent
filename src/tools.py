"""Thin deterministic tool interface.

Why this module exists:
- deterministic checks are currently invoked in a fixed pipeline (`run_checks`)
- future agent mode will need to inspect and call checks dynamically
- this module provides lightweight metadata + wrappers without rewriting checks
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from src import checks
from src.models import AgentConfig, Finding


@dataclass(frozen=True)
class ToolSpec:
    """Metadata describing a deterministic check as a callable tool."""

    name: str
    purpose: str
    required_inputs: tuple[str, ...]
    output_shape: str


@dataclass(frozen=True)
class Tool:
    """A named deterministic tool wrapper plus human-readable metadata."""

    spec: ToolSpec
    execute: Callable[[pd.DataFrame, AgentConfig], list[Finding]]


def _schema_surprises_tool(df: pd.DataFrame, config: AgentConfig) -> list[Finding]:
    return checks.check_schema_surprises(df, expected_columns=config.expected_columns)


def _missing_values_tool(df: pd.DataFrame, _config: AgentConfig) -> list[Finding]:
    return checks.check_missing_values(df)


def _duplicate_keys_tool(df: pd.DataFrame, config: AgentConfig) -> list[Finding]:
    findings: list[Finding] = []
    for key_column in config.key_columns:
        findings.extend(checks.check_duplicate_keys(df, key_column=key_column))
    return findings


def _categorical_values_tool(df: pd.DataFrame, config: AgentConfig) -> list[Finding]:
    findings: list[Finding] = []
    for column, allowed_values in config.categorical_rules.items():
        findings.extend(
            checks.check_unexpected_categorical_values(
                df,
                column=column,
                allowed_values=set(allowed_values),
            )
        )
    return findings


def _date_gaps_tool(df: pd.DataFrame, config: AgentConfig) -> list[Finding]:
    findings: list[Finding] = []
    for column in config.date_gap_columns:
        findings.extend(checks.check_date_gaps(df, column=column))
    return findings


def _numeric_outliers_tool(df: pd.DataFrame, config: AgentConfig) -> list[Finding]:
    findings: list[Finding] = []
    for column in config.numeric_outlier_columns:
        findings.extend(checks.check_numeric_outliers(df, column=column))
    return findings


_DETERMINISTIC_TOOLS: tuple[Tool, ...] = (
    Tool(
        spec=ToolSpec(
            name="schema_surprises",
            purpose="Compare actual columns to configured expected schema.",
            required_inputs=("dataframe", "config.expected_columns"),
            output_shape="list[Finding] (0..1)",
        ),
        execute=_schema_surprises_tool,
    ),
    Tool(
        spec=ToolSpec(
            name="missing_values",
            purpose="Find columns with null/missing values.",
            required_inputs=("dataframe",),
            output_shape="list[Finding] (0..n)",
        ),
        execute=_missing_values_tool,
    ),
    Tool(
        spec=ToolSpec(
            name="duplicate_keys",
            purpose="Check configured key columns for duplicates.",
            required_inputs=("dataframe", "config.key_columns"),
            output_shape="list[Finding] (0..n)",
        ),
        execute=_duplicate_keys_tool,
    ),
    Tool(
        spec=ToolSpec(
            name="unexpected_categorical_values",
            purpose="Check categorical columns against configured allowed values.",
            required_inputs=("dataframe", "config.categorical_rules"),
            output_shape="list[Finding] (0..n)",
        ),
        execute=_categorical_values_tool,
    ),
    Tool(
        spec=ToolSpec(
            name="date_gaps",
            purpose="Identify missing dates in configured date columns.",
            required_inputs=("dataframe", "config.date_gap_columns"),
            output_shape="list[Finding] (0..n)",
        ),
        execute=_date_gaps_tool,
    ),
    Tool(
        spec=ToolSpec(
            name="numeric_outliers",
            purpose="Identify IQR-based outliers in configured numeric columns.",
            required_inputs=("dataframe", "config.numeric_outlier_columns"),
            output_shape="list[Finding] (0..n)",
        ),
        execute=_numeric_outliers_tool,
    ),
)


def list_deterministic_tools() -> tuple[ToolSpec, ...]:
    """Return metadata for deterministic tools available to orchestrators."""
    return tuple(tool.spec for tool in _DETERMINISTIC_TOOLS)


def run_deterministic_tools(df: pd.DataFrame, config: AgentConfig) -> list[Finding]:
    """Run deterministic tools in the existing stable order."""
    findings: list[Finding] = []
    for tool in _DETERMINISTIC_TOOLS:
        findings.extend(tool.execute(df, config))
    return findings
