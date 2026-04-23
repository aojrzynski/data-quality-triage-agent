"""Future-facing agent state scaffolding.

These structures are intentionally not wired into a planner yet.
They define concrete state shapes so future milestones can build an explicit
agent loop without redesigning run-state representation from scratch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


AssumptionStatus = Literal["inferred", "auto_accepted", "user_confirmed", "user_overridden"]


@dataclass
class AssumptionRecord:
    """Tracks one assumption the future agent may make during triage."""

    key: str
    value: Any
    confidence: float | None = None
    status: AssumptionStatus = "inferred"
    source: str = "rule"
    notes: str | None = None
    role_type: str | None = None
    column_name: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionRecord:
    """Represents one action taken by a future planner/executor."""

    action_name: str
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None
    status: Literal["pending", "completed", "failed", "skipped"] = "pending"
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class StopRationale:
    """Explains why an agent run ended (future stop-condition output)."""

    reason: str
    code: str
    is_terminal: bool = True
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRunState:
    """Top-level mutable state for a future agent-mode run."""

    run_id: str
    dataset_name: str
    mode: Literal["deterministic", "agent"]
    phase: str = "initialized"
    actions: list[ActionRecord] = field(default_factory=list)
    assumptions: list[AssumptionRecord] = field(default_factory=list)
    stop_rationale: StopRationale | None = None
    context: dict[str, Any] = field(default_factory=dict)
