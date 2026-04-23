"""Rule-based planner for first-pass agent-mode execution."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.intake import IntakeResult
from src.models import AgentConfig
from src.role_inference import RoleInferenceResult


@dataclass(frozen=True)
class PlannedAction:
    """A deterministic action selected by the planner."""

    tool_name: str
    reason: str
    priority: int
    role_signals: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PlanResult:
    """Planner output with ordered actions and inspectable metadata."""

    actions: list[PlannedAction]
    rationale: list[str]


def _has_key_signal(_config: AgentConfig, inference: RoleInferenceResult) -> bool:
    return bool(inference.key_candidates)


def _has_date_signal(_config: AgentConfig, inference: RoleInferenceResult) -> bool:
    return bool(inference.date_candidates)


def _has_numeric_signal(_config: AgentConfig, inference: RoleInferenceResult) -> bool:
    return bool(inference.numeric_measure_candidates)


def _has_categorical_signal(_config: AgentConfig, inference: RoleInferenceResult) -> bool:
    return bool(inference.categorical_candidates)


def build_rule_based_plan(
    intake_result: IntakeResult,
    inference_result: RoleInferenceResult,
    config: AgentConfig,
) -> PlanResult:
    """Select a deterministic first-pass tool sequence using explicit rules."""
    suitability = intake_result.selected_candidate.suitability

    rationale: list[str] = [
        (
            "Planner uses deterministic intake suitability + role-candidate "
            "signals to choose deterministic tools."
        )
    ]

    actions: list[PlannedAction] = [
        PlannedAction(
            tool_name="schema_surprises",
            reason="Run early to validate incoming columns against expected schema.",
            priority=10,
        ),
        PlannedAction(
            tool_name="missing_values",
            reason="Run early to assess baseline data completeness.",
            priority=20,
        ),
    ]

    if suitability.status == "borderline":
        rationale.append(
            "Suitability is borderline, so the plan prioritizes foundational schema/completeness checks."
        )
    else:
        rationale.append(
            "Suitability is strong enough to include role-driven checks after foundational checks."
        )

    if _has_key_signal(config, inference_result):
        actions.append(
            PlannedAction(
                tool_name="duplicate_keys",
                reason="Key role candidates exist; run duplicate identifier checks with resolved bindings.",
                priority=30,
                role_signals=tuple(c.column_name for c in inference_result.key_candidates),
            )
        )
    else:
        rationale.append("Skipped duplicate_keys because key-role candidates are absent.")

    if _has_categorical_signal(config, inference_result):
        actions.append(
            PlannedAction(
                tool_name="unexpected_categorical_values",
                reason="Categorical role candidates exist; validate where configured categorical rule sets are available.",
                priority=40,
                role_signals=tuple(c.column_name for c in inference_result.categorical_candidates),
            )
        )
    else:
        rationale.append(
            "Skipped unexpected_categorical_values because categorical role candidates are absent."
        )

    if _has_date_signal(config, inference_result):
        actions.append(
            PlannedAction(
                tool_name="date_gaps",
                reason="Date role candidates exist; check continuity on resolved date bindings.",
                priority=50,
                role_signals=tuple(c.column_name for c in inference_result.date_candidates),
            )
        )
    else:
        rationale.append("Skipped date_gaps because date-role candidates are absent.")

    if _has_numeric_signal(config, inference_result):
        actions.append(
            PlannedAction(
                tool_name="numeric_outliers",
                reason="Numeric-measure candidates exist; evaluate resolved numeric bindings for outliers.",
                priority=60,
                role_signals=tuple(
                    c.column_name for c in inference_result.numeric_measure_candidates
                ),
            )
        )
    else:
        rationale.append(
            "Skipped numeric_outliers because numeric-measure candidates are absent."
        )

    ordered_actions = sorted(actions, key=lambda action: action.priority)
    return PlanResult(actions=ordered_actions, rationale=rationale)
