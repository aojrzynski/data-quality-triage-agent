"""Agent-mode rule-based planner/executor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.agent_state import ActionRecord, AgentRunState, AssumptionRecord, StopRationale
from src.bindings import parse_column_override, resolve_agent_execution_bindings
from src.config import load_agent_config
from src.intake import IntakeResult, inspect_and_select_dataset
from src.investigation_tools import (
    InvestigationResult,
    investigate_duplicate_keys,
    investigate_missing_values,
    investigate_numeric_outliers,
    investigate_unexpected_categorical_values,
)
from src.io import save_json, save_markdown
from src.llm_summary import build_agent_llm_polish_payload, generate_agent_llm_polish
from src.models import AgentConfig, Finding
from src.planner import PlanResult, build_rule_based_plan
from src.role_inference import RoleInferenceResult, infer_column_roles
from src.scoring import score_findings
from src.tools import execute_agent_bound_tool
from src.triage_reporting import build_agent_markdown_report, build_triage_conclusion

RoleName = str


@dataclass(frozen=True)
class AgentRunArtifacts:
    """Agent-mode output artifact locations."""

    trace_json_path: Path
    report_markdown_path: Path
    llm_report_markdown_path: Path | None = None


@dataclass(frozen=True)
class AgentRunResult:
    """Structured output from one agent-mode execution."""

    state: AgentRunState
    intake_result: IntakeResult
    inference_result: RoleInferenceResult
    plan_result: PlanResult
    findings: list[Finding]
    triage_summary: dict
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
        "resolved_bindings": result.state.context.get("resolved_bindings", {}),
        "assumption_review": result.state.context.get("assumption_review", {}),
        "executed_actions": [_action_to_dict(action) for action in result.state.actions],
        "investigations": result.state.context.get("investigation_results", []),
        "stop_rationale": _stop_to_dict(result.state.stop_rationale),
        "findings_summary": {
            "count": len(result.findings),
            "by_type": {
                finding_type: sum(1 for finding in result.findings if finding.finding_type == finding_type)
                for finding_type in sorted({finding.finding_type for finding in result.findings})
            },
        },
        "triage_summary": result.triage_summary,
        "conclusion_basis": {
            "finding_families": sorted({finding.finding_type for finding in result.findings}),
            "investigation_count": len(result.state.context.get("investigation_results", [])),
            "executed_action_count": len(result.state.actions),
        },
        "llm_polish": result.state.context.get("llm_polish", {}),
    }


def _pick_first_findings_by_type(findings: list[Finding]) -> dict[str, Finding]:
    selected: dict[str, Finding] = {}
    for finding in findings:
        if finding.finding_type not in selected:
            selected[finding.finding_type] = finding
    return selected


def _plan_investigations(findings: list[Finding], max_investigations: int = 4) -> list[Finding]:
    by_type = _pick_first_findings_by_type(findings)
    planned: list[Finding] = []

    for finding_type in ["duplicate_key", "numeric_outliers", "unexpected_values"]:
        finding = by_type.get(finding_type)
        if finding is not None:
            planned.append(finding)

    missing_candidates = [
        finding
        for finding in findings
        if finding.finding_type == "missing_values" and finding.severity in {"high", "critical"}
    ]
    if missing_candidates:
        planned.append(missing_candidates[0])

    return planned[:max_investigations]


def _execute_investigation(df, finding: Finding) -> InvestigationResult | None:
    if finding.finding_type == "duplicate_key":
        return investigate_duplicate_keys(df, finding)
    if finding.finding_type == "numeric_outliers":
        return investigate_numeric_outliers(df, finding)
    if finding.finding_type == "unexpected_values":
        return investigate_unexpected_categorical_values(df, finding)
    if finding.finding_type == "missing_values":
        return investigate_missing_values(df, finding)
    return None


def _parse_review_input(raw: str) -> list[str] | None:
    normalized = raw.strip()
    if not normalized:
        return None
    if normalized.lower() == "none":
        return []
    return [token.strip() for token in normalized.split(",") if token.strip()]


def _set_assumption_statuses(
    state: AgentRunState,
    bindings,
    role_resolution: dict[RoleName, str],
) -> None:
    role_type_mapping = {
        "key": "key",
        "date": "date",
        "numeric": "numeric_measure",
        "categorical": "categorical",
    }

    assumption_index = {
        (assumption.role_type, assumption.column_name): assumption for assumption in state.assumptions
    }

    for role, resolution in role_resolution.items():
        role_type = role_type_mapping[role]
        role_binding = getattr(bindings, role)
        bound_columns = role_binding.columns

        if resolution == "auto_accepted":
            for column in bound_columns:
                assumption = assumption_index.get((role_type, column))
                if assumption is not None:
                    assumption.status = "auto_accepted"
            continue

        if resolution == "user_confirmed":
            for column in bound_columns:
                assumption = assumption_index.get((role_type, column))
                if assumption is not None:
                    assumption.status = "user_confirmed"
            continue

        if resolution == "user_overridden":
            for assumption in state.assumptions:
                if assumption.role_type == role_type:
                    assumption.status = "user_overridden"
            for column in bound_columns:
                assumption = assumption_index.get((role_type, column))
                if assumption is not None:
                    assumption.status = "user_overridden"
                    continue
                state.assumptions.append(
                    AssumptionRecord(
                        key=f"{role_type}:{column}",
                        value=True,
                        confidence=None,
                        status="user_overridden",
                        source="user_input",
                        notes="User provided override during assumption confirmation.",
                        role_type=role_type,
                        column_name=column,
                        evidence={},
                    )
                )


def run_agent_mode(
    input_path: str | Path,
    output_dir: str | Path,
    config_path: str | Path,
    sheet_name: str | int | None = None,
    agent_key_columns: str | None = None,
    agent_date_columns: str | None = None,
    agent_numeric_columns: str | None = None,
    agent_categorical_columns: str | None = None,
    confirm_assumptions: bool = False,
    llm_summary: bool = False,
    llm_model: str | None = None,
    prompt_fn=None,
    display_fn=None,
) -> AgentRunResult:
    """Run first-pass agent mode: intake -> infer roles -> plan -> execute tools."""
    if prompt_fn is None:
        prompt_fn = input
    if display_fn is None:
        display_fn = print

    config: AgentConfig = load_agent_config(config_path)
    intake_result = inspect_and_select_dataset(input_path, sheet_name=sheet_name)
    state = _new_run_state(dataset_name=Path(input_path).name)
    state.phase = "intake_completed"

    trace_json_path = Path(output_dir) / f"{Path(input_path).stem}_agent_trace.json"
    report_markdown_path = Path(output_dir) / f"{Path(input_path).stem}_agent_report.md"

    suitability = intake_result.selected_candidate.suitability
    if suitability.hard_failure:
        llm_status = {
            "requested": llm_summary,
            "mode": "agent",
            "status": "skipped",
            "reason": "intake_hard_failure" if llm_summary else "not_requested",
        }
        if llm_model:
            llm_status["model"] = llm_model
        state.context["llm_polish"] = llm_status
        state.stop_rationale = StopRationale(
            reason="Intake suitability hard-failed; no deterministic tools were executed.",
            code="INTAKE_HARD_FAILURE",
            details={"recommended_action": suitability.recommended_action},
        )
        state.phase = "stopped"

        triage = build_triage_conclusion(findings=[], investigations=[], stop_rationale=state.stop_rationale)
        result = AgentRunResult(
            state=state,
            intake_result=intake_result,
            inference_result=RoleInferenceResult([], [], [], [], []),
            plan_result=PlanResult(actions=[], rationale=["No planning due to intake hard failure."]),
            findings=[],
            triage_summary=triage.to_dict(),
            artifacts=AgentRunArtifacts(
                trace_json_path=trace_json_path,
                report_markdown_path=report_markdown_path,
                llm_report_markdown_path=None,
            ),
        )
        report = build_agent_markdown_report(
            dataset_name=result.state.dataset_name,
            intake_summary={
                "row_count": len(intake_result.df),
                "column_count": len(intake_result.df.columns),
                "file_type": intake_result.file_type,
                "selection_mode": intake_result.selection_mode,
                "selected_sheet_name": intake_result.selected_sheet_name,
                "suitability_status": suitability.status,
                "suitability_score": suitability.score,
            },
            assumptions=[],
            resolved_bindings={},
            planned_action_names=[],
            action_history=result.state.actions,
            findings=[],
            triage=triage,
            assumption_review=state.context.get("assumption_review"),
        )
        save_json(result.artifacts.trace_json_path, _build_trace_payload(result))
        save_markdown(result.artifacts.report_markdown_path, report)
        return result

    inference_result = infer_column_roles(intake_result.df)
    state.assumptions.extend(inference_result.assumptions)

    cli_overrides = {
        "key": parse_column_override(agent_key_columns),
        "date": parse_column_override(agent_date_columns),
        "numeric": parse_column_override(agent_numeric_columns),
        "categorical": parse_column_override(agent_categorical_columns),
    }
    interactive_overrides: dict[str, list[str] | None] = {
        "key": None,
        "date": None,
        "numeric": None,
        "categorical": None,
    }
    role_resolution = {
        "key": "auto_accepted",
        "date": "auto_accepted",
        "numeric": "auto_accepted",
        "categorical": "auto_accepted",
    }
    review_notes: dict[str, str] = {}

    if confirm_assumptions:
        display_fn("Assumption confirmation (agent mode)")
        display_fn(
            "Precedence policy: CLI override flags > interactive confirmation > inference > config fallback."
        )
        display_fn(
            "For each role: press Enter to accept proposed binding, type comma-separated columns to override, or type none to clear."
        )

        proposed = resolve_agent_execution_bindings(
            intake_result.df,
            inference_result,
            config,
            key_override=cli_overrides["key"],
            date_override=cli_overrides["date"],
            numeric_override=cli_overrides["numeric"],
            categorical_override=cli_overrides["categorical"],
        )

        for role in ["key", "date", "numeric", "categorical"]:
            role_binding = getattr(proposed, role)
            if cli_overrides[role] is not None:
                role_resolution[role] = "user_overridden"
                review_notes[role] = "locked_by_cli_override"
                display_fn(
                    f"- {role}: CLI override already provided -> {', '.join(role_binding.columns) if role_binding.columns else 'none'}"
                )
                continue

            display_fn(
                f"- {role} proposed: {', '.join(role_binding.columns) if role_binding.columns else 'none'}"
            )
            user_raw = prompt_fn(f"  {role}> ").strip()
            parsed = _parse_review_input(user_raw)
            if parsed is None:
                role_resolution[role] = "user_confirmed"
                review_notes[role] = "accepted_default"
            elif parsed == []:
                interactive_overrides[role] = []
                role_resolution[role] = "user_overridden"
                review_notes[role] = "cleared"
            else:
                interactive_overrides[role] = parsed
                role_resolution[role] = "user_overridden"
                review_notes[role] = "custom_override"

    bindings = resolve_agent_execution_bindings(
        intake_result.df,
        inference_result,
        config,
        key_override=cli_overrides["key"] if cli_overrides["key"] is not None else interactive_overrides["key"],
        date_override=cli_overrides["date"] if cli_overrides["date"] is not None else interactive_overrides["date"],
        numeric_override=cli_overrides["numeric"]
        if cli_overrides["numeric"] is not None
        else interactive_overrides["numeric"],
        categorical_override=cli_overrides["categorical"]
        if cli_overrides["categorical"] is not None
        else interactive_overrides["categorical"],
    )
    _set_assumption_statuses(state, bindings, role_resolution)

    state.context["assumption_review"] = {
        "enabled": confirm_assumptions,
        "precedence_policy": [
            "cli_override_flags",
            "interactive_confirmation",
            "inference",
            "config_fallback",
        ],
        "role_resolution": dict(role_resolution),
        "review_notes": review_notes,
        "interactive_overrides": {k: (v if v is not None else "__accepted__") for k, v in interactive_overrides.items()},
        "cli_overrides": {k: (v if v is not None else "__not_set__") for k, v in cli_overrides.items()},
    }

    state.context["resolved_bindings"] = bindings.to_dict()

    state.phase = "planning"

    plan_result = build_rule_based_plan(
        intake_result=intake_result,
        inference_result=inference_result,
        config=config,
        bindings=bindings,
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
                execution = execute_agent_bound_tool(planned.tool_name, intake_result.df, config, bindings)
                findings.extend(execution.findings)
                _complete_action(
                    action,
                    status=execution.status,
                    details={
                        "planned_reason": planned.reason,
                        "role_signals": list(planned.role_signals),
                        **execution.details,
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

        planned_investigations = _plan_investigations(findings)
        state.context["planned_investigations"] = [
            {"finding_type": finding.finding_type, "column": finding.column}
            for finding in planned_investigations
        ]

        if planned_investigations:
            state.phase = "investigating"
            investigation_results: list[dict] = []
            for finding in planned_investigations:
                investigation = _execute_investigation(intake_result.df, finding)
                if investigation is None:
                    continue
                action = ActionRecord(action_name=investigation.action_name)
                state.actions.append(action)
                _complete_action(
                    action,
                    status=investigation.status,
                    details={
                        "finding_type": finding.finding_type,
                        "column": finding.column,
                        **investigation.details,
                    },
                )
                investigation_results.append(investigation.to_dict())
            state.context["investigation_results"] = investigation_results
        else:
            state.context["investigation_results"] = []
            state.context["investigation_note"] = "No investigations were warranted by scored findings."

        if state.stop_rationale is None:
            state.stop_rationale = StopRationale(
                reason="Completed planned deterministic checks and bounded second-pass investigations.",
                code="PLAN_AND_INVESTIGATION_COMPLETED",
                details={
                    "executed_action_count": len(state.actions),
                    "investigation_count": len(state.context.get("investigation_results", [])),
                },
            )
            state.phase = "completed"

    triage = build_triage_conclusion(
        findings=findings,
        investigations=state.context.get("investigation_results", []),
        stop_rationale=state.stop_rationale,
    )

    result = AgentRunResult(
        state=state,
        intake_result=intake_result,
        inference_result=inference_result,
        plan_result=plan_result,
        findings=findings,
        triage_summary=triage.to_dict(),
        artifacts=AgentRunArtifacts(
            trace_json_path=trace_json_path,
            report_markdown_path=report_markdown_path,
            llm_report_markdown_path=None,
        ),
    )

    report = build_agent_markdown_report(
        dataset_name=result.state.dataset_name,
        intake_summary={
            "row_count": len(result.intake_result.df),
            "column_count": len(result.intake_result.df.columns),
            "file_type": result.intake_result.file_type,
            "selection_mode": result.intake_result.selection_mode,
            "selected_sheet_name": result.intake_result.selected_sheet_name,
            "suitability_status": suitability.status,
            "suitability_score": suitability.score,
        },
        assumptions=result.state.assumptions,
        resolved_bindings=result.state.context.get("resolved_bindings", {}),
        planned_action_names=[action.tool_name for action in result.plan_result.actions],
        action_history=result.state.actions,
        findings=result.findings,
        triage=triage,
        assumption_review=result.state.context.get("assumption_review"),
    )

    save_markdown(report_markdown_path, report)

    llm_status: dict = {
        "requested": llm_summary,
        "mode": "agent",
        "status": "skipped",
        "reason": "not_requested",
    }
    if llm_model:
        llm_status["model"] = llm_model

    if llm_summary:
        llm_payload = build_agent_llm_polish_payload(
            dataset_name=result.state.dataset_name,
            intake_summary={
                "row_count": len(result.intake_result.df),
                "column_count": len(result.intake_result.df.columns),
                "file_type": result.intake_result.file_type,
                "selection_mode": result.intake_result.selection_mode,
                "selected_sheet_name": result.intake_result.selected_sheet_name,
                "suitability_status": suitability.status,
                "suitability_score": suitability.score,
            },
            triage_summary=result.triage_summary,
            resolved_bindings=result.state.context.get("resolved_bindings", {}),
            action_history=[_action_to_dict(action) for action in result.state.actions],
            assumption_review=result.state.context.get("assumption_review"),
        )
        try:
            polished_report = generate_agent_llm_polish(llm_payload, model=llm_model)
            llm_report_path = Path(output_dir) / f"{Path(input_path).stem}_agent_report_llm.md"
            save_markdown(llm_report_path, polished_report)
            object.__setattr__(
                result,
                "artifacts",
                AgentRunArtifacts(
                    trace_json_path=result.artifacts.trace_json_path,
                    report_markdown_path=result.artifacts.report_markdown_path,
                    llm_report_markdown_path=llm_report_path,
                ),
            )
            llm_status = {
                "requested": True,
                "mode": "agent",
                "status": "completed",
                "output_path": str(llm_report_path),
            }
            if llm_model:
                llm_status["model"] = llm_model
        except Exception as exc:  # Optional layer must never break deterministic run.
            llm_status = {
                "requested": True,
                "mode": "agent",
                "status": "failed",
                "reason": str(exc),
            }
            if llm_model:
                llm_status["model"] = llm_model

    state.context["llm_polish"] = llm_status
    save_json(trace_json_path, _build_trace_payload(result))
    return result
