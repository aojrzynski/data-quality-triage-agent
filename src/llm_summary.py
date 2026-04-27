"""Optional LLM summary logic.

This module uses the OpenAI API to turn structured findings into a short,
clean summary. The model should explain findings, not discover them.
"""

from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

from src.models import RunResult


def _get_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set it in your environment before using --llm-summary."
        )
    return api_key


def _call_openai_markdown(
    *,
    payload: dict[str, Any],
    developer_instruction: str,
    model: str | None = None,
) -> str:
    selected_model = model or os.getenv("OPENAI_MODEL", "gpt-5.4")
    client = OpenAI(api_key=_get_api_key())
    response = client.responses.create(
        model=selected_model,
        input=[
            {"role": "developer", "content": developer_instruction},
            {"role": "user", "content": json.dumps(payload, indent=2)},
        ],
    )
    return response.output_text.strip()


def build_llm_summary_payload(run_result: RunResult) -> dict[str, Any]:
    """Build a compact payload for the LLM.

    We send only the structured result, not the raw dataset.
    """
    return {
        "dataset_name": run_result.dataset_name,
        "profile": {
            "row_count": run_result.profile.row_count,
            "column_count": run_result.profile.column_count,
            "columns": run_result.profile.columns,
        },
        "findings": [finding.to_dict() for finding in run_result.findings],
    }


def generate_llm_summary(
    run_result: RunResult,
    model: str | None = None,
) -> str:
    """Generate an optional LLM-written summary.

    Raises:
        RuntimeError: If OPENAI_API_KEY is not set.
    """
    if not run_result.findings:
        return "No data quality issues were detected, so no LLM summary was generated."
    payload = build_llm_summary_payload(run_result)
    return _call_openai_markdown(
        payload=payload,
        developer_instruction=(
            "You are a careful data quality analyst. "
            "Write a short markdown summary of the supplied findings. "
            "Use only the provided information. "
            "Do not invent causes, columns, counts, or business context. "
            "Keep it concise. "
            "Use these sections exactly: "
            "## Executive Summary, "
            "## Priority Issues, "
            "## Recommended Next Checks."
        ),
        model=model,
    )


def build_agent_llm_polish_payload(
    *,
    dataset_name: str,
    intake_summary: dict[str, Any],
    triage_summary: dict[str, Any],
    resolved_bindings: dict[str, Any],
    action_history: list[dict[str, Any]],
    assumption_review: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build bounded agent-mode payload for optional narrative polish."""
    return {
        "dataset_name": dataset_name,
        "intake_summary": intake_summary,
        "triage_summary": triage_summary,
        "resolved_bindings": resolved_bindings,
        "action_history": action_history,
        "assumption_review": assumption_review or {},
    }


def generate_agent_llm_polish(payload: dict[str, Any], model: str | None = None) -> str:
    """Generate optional LLM-polished agent narrative from deterministic evidence only."""
    return _call_openai_markdown(
        payload=payload,
        developer_instruction=(
            "You are polishing a deterministic data-quality triage report. "
            "Use only the provided payload as evidence. "
            "Never invent findings, counts, checks, causes, or recommendations. "
            "If an action was skipped or limited, keep that visible. "
            "Preserve uncertainty and limitations exactly when present. "
            "Do not change severity interpretation or rank independently. "
            "Write concise markdown with these sections exactly: "
            "## Triage Outcome, "
            "## Key Findings and Impact, "
            "## Investigations and Limits, "
            "## Assumptions and Bindings, "
            "## Suggested Next Steps."
        ),
        model=model,
    )
