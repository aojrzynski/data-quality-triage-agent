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

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set it in your environment before using --llm-summary."
        )

    selected_model = model or os.getenv("OPENAI_MODEL", "gpt-5.4")
    client = OpenAI(api_key=api_key)

    payload = build_llm_summary_payload(run_result)

    response = client.responses.create(
        model=selected_model,
        input=[
            {
                "role": "developer",
                "content": (
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
            },
            {
                "role": "user",
                "content": json.dumps(payload, indent=2),
            },
        ],
    )

    return response.output_text.strip()