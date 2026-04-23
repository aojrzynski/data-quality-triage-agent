"""Rule-based planner for first-pass agent-mode execution."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.bindings import AgentExecutionBindings
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


def _binding_summary(source_by_column: dict[str, str]) -> str:
    if not source_by_column:
        return "none"
    grouped: dict[str, list[str]] = {}
    for column, source in source_by_column.items():
        grouped.setdefault(source, []).append(column)
    return "; ".join(
        f"{source}: {', '.join(sorted(columns))}" for source, columns in sorted(grouped.items())
    )


def build_rule_based_plan(
    intake_result: IntakeResult,
    inference_result: RoleInferenceResult,
    config: AgentConfig,
    bindings: AgentExecutionBindings,
) -> PlanResult:
    """Select a deterministic first-pass tool sequence using explicit rules."""
    suitability = intake_result.selected_candidate.suitability

    rationale: list[str] = [
        (
            "Planner uses deterministic intake suitability plus resolved role bindings "
            "(override -> inferred -> config fallback) to choose deterministic tools."
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

    if bindings.key.columns:
        actions.append(
            PlannedAction(
                tool_name="duplicate_keys",
                reason=(
                    "Resolved key bindings exist; run duplicate identifier checks on "
                    f"{', '.join(bindings.key.columns)} ({_binding_summary(bindings.key.source_by_column)})."
                ),
                priority=30,
                role_signals=tuple(c.column_name for c in inference_result.key_candidates),
            )
        )
    else:
        rationale.append(
            "Skipped duplicate_keys because no usable resolved key binding exists "
            f"({bindings.key.skipped_reason or 'none'})."
        )

    if bindings.categorical.columns:
        actions.append(
            PlannedAction(
                tool_name="unexpected_categorical_values",
                reason=(
                    "Resolved categorical bindings exist; validate configured categorical rule sets on "
                    f"{', '.join(bindings.categorical.columns)} "
                    f"({_binding_summary(bindings.categorical.source_by_column)})."
                ),
                priority=40,
                role_signals=tuple(c.column_name for c in inference_result.categorical_candidates),
            )
        )
    else:
        rationale.append(
            "Skipped unexpected_categorical_values because no usable resolved categorical binding exists "
            f"({bindings.categorical.skipped_reason or 'none'})."
        )

    if bindings.date.columns:
        actions.append(
            PlannedAction(
                tool_name="date_gaps",
                reason=(
                    "Resolved date bindings exist; check continuity on "
                    f"{', '.join(bindings.date.columns)} ({_binding_summary(bindings.date.source_by_column)})."
                ),
                priority=50,
                role_signals=tuple(c.column_name for c in inference_result.date_candidates),
            )
        )
    else:
        rationale.append(
            "Skipped date_gaps because no usable resolved date binding exists "
            f"({bindings.date.skipped_reason or 'none'})."
        )

    if bindings.numeric.columns:
        actions.append(
            PlannedAction(
                tool_name="numeric_outliers",
                reason=(
                    "Resolved numeric bindings exist; evaluate outliers on "
                    f"{', '.join(bindings.numeric.columns)} "
                    f"({_binding_summary(bindings.numeric.source_by_column)})."
                ),
                priority=60,
                role_signals=tuple(
                    c.column_name for c in inference_result.numeric_measure_candidates
                ),
            )
        )
    else:
        rationale.append(
            "Skipped numeric_outliers because no usable resolved numeric binding exists "
            f"({bindings.numeric.skipped_reason or 'none'})."
        )

    ordered_actions = sorted(actions, key=lambda action: action.priority)
    return PlanResult(actions=ordered_actions, rationale=rationale)
