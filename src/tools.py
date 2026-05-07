"""Thin wrappers that expose deterministic checks as planner tools.

Why this module exists:
- deterministic checks are currently invoked in a fixed pipeline (`run_checks`)
- future agent mode will need to inspect and call checks dynamically
- this module provides lightweight metadata + wrappers without rewriting checks

The agent may choose which tools to run, but each tool still delegates to
deterministic check functions that generate the evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

import pandas as pd

from src import checks
from src.bindings import AgentExecutionBindings
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


@dataclass(frozen=True)
class AgentToolExecutionResult:
    """Execution outcome for one agent tool invocation.

    Agent mode orchestrates which tools run; this result keeps execution details
    structured so traces can explain what ran, what was skipped, and why.
    """

    status: Literal["completed", "skipped"]
    findings: list[Finding]
    details: dict


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


def get_deterministic_tool(name: str) -> Tool:
    """Return one deterministic tool wrapper by name."""
    for tool in _DETERMINISTIC_TOOLS:
        if tool.spec.name == name:
            return tool
    raise ValueError(f"Unknown deterministic tool: {name}")


def execute_deterministic_tool(
    name: str,
    df: pd.DataFrame,
    config: AgentConfig,
) -> list[Finding]:
    """Execute one deterministic tool by name."""
    tool = get_deterministic_tool(name)
    return tool.execute(df, config)


def execute_agent_bound_tool(
    name: str,
    df: pd.DataFrame,
    config: AgentConfig,
    bindings: AgentExecutionBindings,
) -> AgentToolExecutionResult:
    """Execute one deterministic tool using resolved agent-mode bindings.

    Wrappers remain intentionally thin: selection happens in planning/execution
    orchestration, while findings come from deterministic check primitives.
    """
    if name in {"schema_surprises", "missing_values"}:
        findings = execute_deterministic_tool(name, df, config)
        return AgentToolExecutionResult(
            status="completed",
            findings=findings,
            details={"binding_scope": "not_applicable"},
        )

    bound_columns = bindings.columns_for_tool(name)
    source_map = bindings.source_map_for_tool(name)

    if not bound_columns:
        return AgentToolExecutionResult(
            status="skipped",
            findings=[],
            details={
                "binding_scope": "role_bound",
                "bound_columns": [],
                "binding_source_by_column": {},
                "skip_reason": bindings.skipped_reason_for_tool(name)
                or "No usable binding resolved for planned tool.",
            },
        )

    findings: list[Finding] = []
    details = {
        "binding_scope": "role_bound",
        "bound_columns": list(bound_columns),
        "binding_source_by_column": dict(source_map),
    }

    if name == "duplicate_keys":
        for column in bound_columns:
            findings.extend(checks.check_duplicate_keys(df, key_column=column))
    elif name == "date_gaps":
        for column in bound_columns:
            findings.extend(checks.check_date_gaps(df, column=column))
    elif name == "numeric_outliers":
        for column in bound_columns:
            findings.extend(checks.check_numeric_outliers(df, column=column))
    elif name == "unexpected_categorical_values":
        skipped_columns: list[dict[str, str]] = []
        for column in bound_columns:
            if column in config.categorical_rules:
                findings.extend(
                    checks.check_unexpected_categorical_values(
                        df,
                        column=column,
                        allowed_values=set(config.categorical_rules[column]),
                    )
                )
            else:
                skipped_columns.append(
                    {
                        "column": column,
                        "reason": "No configured categorical rule set for selected column.",
                    }
                )
        if skipped_columns:
            details["skipped_columns"] = skipped_columns
            if len(skipped_columns) == len(bound_columns):
                return AgentToolExecutionResult(
                    status="skipped",
                    findings=[],
                    details={
                        **details,
                        "skip_reason": "No configured categorical rule set for any bound categorical column.",
                    },
                )
    else:
        raise ValueError(f"Unknown deterministic tool: {name}")

    details["finding_count"] = len(findings)
    findings_by_column: dict[str, int] = {}
    for finding in findings:
        if finding.column is None:
            continue
        findings_by_column[finding.column] = findings_by_column.get(finding.column, 0) + 1
    details["columns_with_findings"] = sorted(findings_by_column.keys())
    details["finding_count_by_column"] = findings_by_column
    return AgentToolExecutionResult(status="completed", findings=findings, details=details)


def list_deterministic_tools() -> tuple[ToolSpec, ...]:
    """Return metadata for deterministic tools available to orchestrators."""
    return tuple(tool.spec for tool in _DETERMINISTIC_TOOLS)


def run_deterministic_tools(df: pd.DataFrame, config: AgentConfig) -> list[Finding]:
    """Run deterministic tools via the canonical deterministic check pipeline.

    This keeps the tool facade behavior aligned with `run_checks(...)`.
    """
    return checks.run_checks(df, config=config)
