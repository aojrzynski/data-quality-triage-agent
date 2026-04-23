"""Agent-mode rule-based planner/executor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.agent_state import ActionRecord, AgentRunState, StopRationale
from src.config import load_agent_config
from src.intake import IntakeResult, inspect_and_select_dataset
from src.io import save_json
from src.models import AgentConfig, Finding
from src.planner import PlanResult, build_rule_based_plan
from src.role_inference import RoleInferenceResult, infer_column_roles
from src.scoring import score_findings
from src.tools import execute_deterministic_tool


@dataclass(frozen=True)
class AgentRunArtifacts:
    """Agent-mode output artifact locations."""

    trace_json_path: Path


@dataclass(frozen=True)
class AgentRunResult:
    """Structured output from one agent-mode execution."""

    state: AgentRunState
    intake_result: IntakeResult
    inference_result: RoleInferenceResult
    plan_result: PlanResult
    findings: list[Finding]
    artifacts: AgentRunArtifacts


def _new_run_state(dataset_name: str) -> AgentRunState:
    return AgentRunState(
        run_id=f"agent-{uuid4()}",
        dataset_name=dataset_name,
        mode="agent",
        phase="initialized",
    )


def _complete_action(action: ActionRecord, status: str, details: dict) -> None:
    action.status = status
    action.completed_at = datetime.now(timezone.utc).isoformat()
    action.details = details


def _action_to_dict(action: ActionRecord) -> dict:
    return {
        "action_name": action.action_name,
        "started_at": action.started_at,
        "completed_at": action.completed_at,
        "status": action.status,
        "details": action.details,
    }


def _stop_to_dict(stop: StopRationale | None) -> dict | None:
    if stop is None:
        return None
    return {
        "reason": stop.reason,
        "code": stop.code,
        "is_terminal": stop.is_terminal,
        "details": stop.details,
    }


def _build_trace_payload(result: AgentRunResult) -> dict:
    suitability = result.intake_result.selected_candidate.suitability
    return {
        "run_id": result.state.run_id,
        "dataset_name": result.state.dataset_name,
        "mode": result.state.mode,
        "phase": result.state.phase,
        "intake": {
            "file_type": result.intake_result.file_type,
            "selection_mode": result.intake_result.selection_mode,
            "selected_sheet_name": result.intake_result.selected_sheet_name,
            "suitability": {
                "status": suitability.status,
                "score": suitability.score,
                "hard_failure": suitability.hard_failure,
                "reasons": suitability.reasons,
                "warnings": suitability.warnings,
                "recommended_action": suitability.recommended_action,
            },
        },
        "assumptions": [assumption.__dict__ for assumption in result.state.assumptions],
        "planner": {
            "rationale": result.plan_result.rationale,
            "planned_actions": [
                {
                    "tool_name": action.tool_name,
                    "reason": action.reason,
                    "priority": action.priority,
                    "role_signals": list(action.role_signals),
                }
                for action in result.plan_result.actions
            ],
        },
        "executed_actions": [_action_to_dict(action) for action in result.state.actions],
        "stop_rationale": _stop_to_dict(result.state.stop_rationale),
        "findings_summary": {
            "count": len(result.findings),
            "by_type": {
                finding_type: sum(1 for finding in result.findings if finding.finding_type == finding_type)
                for finding_type in sorted({finding.finding_type for finding in result.findings})
            },
        },
    }


def run_agent_mode(
    input_path: str | Path,
    output_dir: str | Path,
    config_path: str | Path,
    sheet_name: str | int | None = None,
) -> AgentRunResult:
    """Run first-pass agent mode: intake -> infer roles -> plan -> execute tools."""
    config: AgentConfig = load_agent_config(config_path)
    intake_result = inspect_and_select_dataset(input_path, sheet_name=sheet_name)
    state = _new_run_state(dataset_name=Path(input_path).name)
    state.phase = "intake_completed"

    suitability = intake_result.selected_candidate.suitability
    if suitability.hard_failure:
        state.stop_rationale = StopRationale(
            reason="Intake suitability hard-failed; no deterministic tools were executed.",
            code="INTAKE_HARD_FAILURE",
            details={"recommended_action": suitability.recommended_action},
        )
        state.phase = "stopped"
        result = AgentRunResult(
            state=state,
            intake_result=intake_result,
            inference_result=RoleInferenceResult([], [], [], [], []),
            plan_result=PlanResult(actions=[], rationale=["No planning due to intake hard failure."]),
            findings=[],
            artifacts=AgentRunArtifacts(trace_json_path=Path(output_dir) / f"{Path(input_path).stem}_agent_trace.json"),
        )
        save_json(result.artifacts.trace_json_path, _build_trace_payload(result))
        return result

    inference_result = infer_column_roles(intake_result.df)
    state.assumptions.extend(inference_result.assumptions)
    state.phase = "planning"

    plan_result = build_rule_based_plan(
        intake_result=intake_result,
        inference_result=inference_result,
        config=config,
    )

    if not plan_result.actions:
        state.stop_rationale = StopRationale(
            reason="Planner produced no executable deterministic actions.",
            code="NO_PLANNED_ACTIONS",
        )
        state.phase = "stopped"
        findings: list[Finding] = []
    else:
        findings = []
        state.phase = "executing"

        for planned in plan_result.actions:
            action = ActionRecord(action_name=planned.tool_name)
            state.actions.append(action)
            try:
                action_findings = execute_deterministic_tool(planned.tool_name, intake_result.df, config)
                findings.extend(action_findings)
                _complete_action(
                    action,
                    status="completed",
                    details={
                        "planned_reason": planned.reason,
                        "role_signals": list(planned.role_signals),
                        "finding_count": len(action_findings),
                    },
                )
            except ValueError as exc:
                _complete_action(
                    action,
                    status="failed",
                    details={
                        "planned_reason": planned.reason,
                        "error": str(exc),
                    },
                )

        findings = score_findings(findings)

        if state.stop_rationale is None:
            state.stop_rationale = StopRationale(
                reason="Completed all planned deterministic actions.",
                code="PLAN_COMPLETED",
                details={"executed_action_count": len(state.actions)},
            )
            state.phase = "completed"

    trace_json_path = Path(output_dir) / f"{Path(input_path).stem}_agent_trace.json"
    result = AgentRunResult(
        state=state,
        intake_result=intake_result,
        inference_result=inference_result,
        plan_result=plan_result,
        findings=findings,
        artifacts=AgentRunArtifacts(trace_json_path=trace_json_path),
    )
    save_json(trace_json_path, _build_trace_payload(result))
    return result
