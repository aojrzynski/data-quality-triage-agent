"""Future agent-mode triage reporting scaffolding.

Deterministic reporting remains in `src.reporting`.
This module creates a separate home for narrative/triage-oriented outputs that
agent mode can generate later, keeping output responsibilities explicit.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TriageConclusion:
    """Minimal scaffold for future triage-mode conclusions."""

    summary: str
    confidence: str | None = None
    recommended_next_steps: list[str] = field(default_factory=list)


def build_triage_markdown_stub() -> str:
    """Return an explicit placeholder until triage reporting is implemented."""
    return (
        "# Data Quality Triage Narrative (Planned)\n\n"
        "Agent-mode narrative reporting is not implemented in this stage.\n"
    )
