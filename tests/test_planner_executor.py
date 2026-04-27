import json
from pathlib import Path

import pandas as pd

from src.agent_runner import run_agent_mode
from src.bindings import resolve_agent_execution_bindings
from src.config import load_agent_config
from src.intake import inspect_and_select_dataset
from src.planner import build_rule_based_plan
from src.role_inference import infer_column_roles


def test_planner_selects_sensible_subset_for_orders_dataset() -> None:
    config = load_agent_config()
    intake_result = inspect_and_select_dataset("sample_data/clean/orders_clean.csv")
    inference = infer_column_roles(intake_result.df)

    bindings = resolve_agent_execution_bindings(intake_result.df, inference, config)
    plan = build_rule_based_plan(intake_result, inference, config, bindings)
    planned_tools = [action.tool_name for action in plan.actions]

    assert planned_tools == [
        "schema_surprises",
        "missing_values",
        "duplicate_keys",
        "unexpected_categorical_values",
        "date_gaps",
        "numeric_outliers",
    ]


def test_planner_skips_role_families_without_candidates(tmp_path: Path) -> None:
    sparse_path = tmp_path / "sparse.csv"
    pd.DataFrame(
        {
            "alpha": ["a", "a", "a", "a"],
            "beta": ["x", "y", "x", "y"],
            "gamma": ["foo", "bar", "foo", "bar"],
        }
    ).to_csv(sparse_path, index=False)

    config = load_agent_config()
    intake_result = inspect_and_select_dataset(sparse_path)
    inference = infer_column_roles(intake_result.df)

    bindings = resolve_agent_execution_bindings(intake_result.df, inference, config)
    plan = build_rule_based_plan(intake_result, inference, config, bindings)
    planned_tools = [action.tool_name for action in plan.actions]

    assert "schema_surprises" in planned_tools
    assert "missing_values" in planned_tools
    assert "duplicate_keys" not in planned_tools
    assert "date_gaps" not in planned_tools
    assert "numeric_outliers" not in planned_tools


def test_agent_executor_records_action_history_and_stop_rationale(tmp_path: Path) -> None:
    result = run_agent_mode(
        input_path="sample_data/broken/orders_bad_categories.csv",
        output_dir=tmp_path,
        config_path="config/default_config.json",
    )

    assert result.state.actions
    assert all(action.status in {"completed", "skipped"} for action in result.state.actions)
    assert result.state.stop_rationale is not None
    assert result.state.stop_rationale.code == "PLAN_AND_INVESTIGATION_COMPLETED"
    assert result.artifacts.trace_json_path.exists()
    assert result.artifacts.report_markdown_path.exists()


def test_agent_executor_intake_hard_failure_stops_without_actions(tmp_path: Path) -> None:
    result = run_agent_mode(
        input_path="tests/fixtures/intake/empty_columns.csv",
        output_dir=tmp_path,
        config_path="config/default_config.json",
    )

    assert result.state.actions == []
    assert result.state.stop_rationale is not None
    assert result.state.stop_rationale.code == "INTAKE_HARD_FAILURE"
    assert result.findings == []
    assert result.artifacts.trace_json_path.exists()


def test_agent_mode_runs_tools_against_inferred_non_orders_bindings(tmp_path: Path) -> None:
    result = run_agent_mode(
        input_path="tests/fixtures/role_inference/trades_stage7.csv",
        output_dir=tmp_path,
        config_path="config/default_config.json",
    )

    trace = json.loads(result.artifacts.trace_json_path.read_text())
    resolved = trace["resolved_bindings"]

    assert "trade_date" in resolved["date"]["columns"]
    assert resolved["date"]["source_by_column"]["trade_date"] == "inferred"
    assert "notional" in resolved["numeric"]["columns"]

    date_action = next(action for action in trace["executed_actions"] if action["action_name"] == "date_gaps")
    assert "trade_date" in date_action["details"]["bound_columns"]

    finding_types = {finding.finding_type for finding in result.findings}
    assert "date_gaps" in finding_types
    assert "numeric_outliers" in finding_types


def test_planner_includes_duplicate_keys_when_override_resolves_binding(tmp_path: Path) -> None:
    override_path = tmp_path / "override_keys.csv"
    pd.DataFrame(
        {
            "trade_ref": ["A1", "A1", "A2", "A3"],
            "event_ts": ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"],
            "value_amt": [10.0, 12.0, 9.0, 11.0],
        }
    ).to_csv(override_path, index=False)

    result = run_agent_mode(
        input_path=override_path,
        output_dir=tmp_path,
        config_path="config/default_config.json",
        agent_key_columns="trade_ref",
    )

    planned_tools = [action.tool_name for action in result.plan_result.actions]
    assert "duplicate_keys" in planned_tools
    duplicate_action = next(action for action in result.state.actions if action.action_name == "duplicate_keys")
    assert duplicate_action.details["bound_columns"] == ["trade_ref"]
    assert duplicate_action.details["binding_source_by_column"]["trade_ref"] == "user_override"


def test_planner_uses_inferred_resolved_binding_for_date_gaps(tmp_path: Path) -> None:
    result = run_agent_mode(
        input_path="tests/fixtures/role_inference/trades_stage7.csv",
        output_dir=tmp_path,
        config_path="config/default_config.json",
    )

    planned_date = next(action for action in result.plan_result.actions if action.tool_name == "date_gaps")
    assert "Resolved date bindings exist" in planned_date.reason
    assert "inferred: trade_date" in planned_date.reason


def test_agent_override_columns_take_precedence_and_are_recorded(tmp_path: Path) -> None:
    result = run_agent_mode(
        input_path="tests/fixtures/role_inference/trades_stage7.csv",
        output_dir=tmp_path,
        config_path="config/default_config.json",
        agent_date_columns="trade_date",
        agent_key_columns="counterparty",
    )

    trace = json.loads(result.artifacts.trace_json_path.read_text())
    key_binding = trace["resolved_bindings"]["key"]
    date_binding = trace["resolved_bindings"]["date"]

    assert key_binding["columns"] == ["counterparty"]
    assert key_binding["source_by_column"]["counterparty"] == "user_override"
    assert date_binding["columns"] == ["trade_date"]
    assert date_binding["source_by_column"]["trade_date"] == "user_override"


def test_agent_categorical_action_skips_without_matching_rule_set(tmp_path: Path) -> None:
    result = run_agent_mode(
        input_path="tests/fixtures/role_inference/trades_stage7.csv",
        output_dir=tmp_path,
        config_path="config/default_config.json",
        agent_categorical_columns="instrument_type",
    )

    categorical_action = next(
        action for action in result.state.actions if action.action_name == "unexpected_categorical_values"
    )
    assert categorical_action.status == "skipped"
    assert "No configured categorical rule set" in categorical_action.details["skip_reason"]


def test_duplicate_findings_trigger_duplicate_investigation(tmp_path: Path) -> None:
    result = run_agent_mode(
        input_path="sample_data/broken/orders_duplicate_keys.csv",
        output_dir=tmp_path,
        config_path="config/default_config.json",
    )

    investigation_actions = [action for action in result.state.actions if action.action_name == "investigate_duplicate_keys"]
    assert investigation_actions
    assert investigation_actions[0].status == "completed"
    assert "duplicate_value_examples" in investigation_actions[0].details


def test_outlier_and_categorical_findings_trigger_investigations(tmp_path: Path) -> None:
    outlier_result = run_agent_mode(
        input_path="sample_data/broken/orders_outliers.csv",
        output_dir=tmp_path,
        config_path="config/default_config.json",
    )
    outlier_actions = [action.action_name for action in outlier_result.state.actions]
    assert "investigate_numeric_outliers" in outlier_actions

    categorical_result = run_agent_mode(
        input_path="sample_data/broken/orders_bad_categories.csv",
        output_dir=tmp_path,
        config_path="config/default_config.json",
    )
    categorical_actions = [action.action_name for action in categorical_result.state.actions]
    assert "investigate_unexpected_categorical_values" in categorical_actions


def test_trace_contains_investigation_results_and_triage_summary(tmp_path: Path) -> None:
    result = run_agent_mode(
        input_path="sample_data/broken/orders_duplicate_keys.csv",
        output_dir=tmp_path,
        config_path="config/default_config.json",
    )

    trace = json.loads(result.artifacts.trace_json_path.read_text())
    assert "investigations" in trace
    assert trace["investigations"]
    assert "triage_summary" in trace
    assert trace["triage_summary"]["top_issues"]
    assert trace["triage_summary"]["severity_view"]


def test_no_investigation_case_is_explicit(tmp_path: Path) -> None:
    result = run_agent_mode(
        input_path="sample_data/clean/orders_clean.csv",
        output_dir=tmp_path,
        config_path="config/default_config.json",
    )

    assert result.state.context["investigation_results"] == []
    assert "investigation_note" in result.state.context
    trace = json.loads(result.artifacts.trace_json_path.read_text())
    assert trace["investigations"] == []
    report_text = result.artifacts.report_markdown_path.read_text()
    assert "## Investigations performed" in report_text


def test_agent_skips_role_bound_tool_when_no_binding_available(tmp_path: Path) -> None:
    result = run_agent_mode(
        input_path="tests/fixtures/role_inference/trades_stage7.csv",
        output_dir=tmp_path,
        config_path="config/default_config.json",
        agent_date_columns="does_not_exist",
    )

    planned_tools = [action.tool_name for action in result.plan_result.actions]
    assert "date_gaps" not in planned_tools
    assert any(
        "Skipped date_gaps because no usable resolved date binding exists" in reason
        for reason in result.plan_result.rationale
    )
    assert all(action.action_name != "date_gaps" for action in result.state.actions)


def test_confirm_assumptions_accepts_defaults_and_marks_user_confirmed(tmp_path: Path) -> None:
    prompts = iter(["", "", "", ""])
    result = run_agent_mode(
        input_path="tests/fixtures/role_inference/trades_stage7.csv",
        output_dir=tmp_path,
        config_path="config/default_config.json",
        confirm_assumptions=True,
        prompt_fn=lambda _msg: next(prompts),
        display_fn=lambda _msg: None,
    )

    review = result.state.context["assumption_review"]
    assert review["enabled"] is True
    assert review["role_resolution"]["key"] == "user_confirmed"
    assert review["role_resolution"]["date"] == "user_confirmed"
    assert any(assumption.status == "user_confirmed" for assumption in result.state.assumptions)

    date_action = next(action for action in result.state.actions if action.action_name == "date_gaps")
    assert "trade_date" in date_action.details["bound_columns"]


def test_confirm_assumptions_supports_override_and_clear(tmp_path: Path) -> None:
    prompts = iter(["counterparty", "none", "", "instrument_type"])
    result = run_agent_mode(
        input_path="tests/fixtures/role_inference/trades_stage7.csv",
        output_dir=tmp_path,
        config_path="config/default_config.json",
        confirm_assumptions=True,
        prompt_fn=lambda _msg: next(prompts),
        display_fn=lambda _msg: None,
    )

    resolved = result.state.context["resolved_bindings"]
    assert resolved["key"]["columns"] == ["counterparty"]
    assert resolved["date"]["columns"] == []
    assert resolved["date"]["skipped_reason"] == "Binding was explicitly cleared by user override."
    assert resolved["categorical"]["columns"] == ["instrument_type"]
    assert result.state.context["assumption_review"]["role_resolution"]["date"] == "user_overridden"

    planned_tools = [action.tool_name for action in result.plan_result.actions]
    assert "date_gaps" not in planned_tools


def test_cli_overrides_take_precedence_over_interactive_confirmation(tmp_path: Path) -> None:
    prompts = iter(["trade_id", "none", "none", "none"])
    result = run_agent_mode(
        input_path="tests/fixtures/role_inference/trades_stage7.csv",
        output_dir=tmp_path,
        config_path="config/default_config.json",
        agent_key_columns="trade_id",
        confirm_assumptions=True,
        prompt_fn=lambda _msg: next(prompts),
        display_fn=lambda _msg: None,
    )

    review = result.state.context["assumption_review"]
    assert review["role_resolution"]["key"] == "user_overridden"
    assert review["review_notes"]["key"] == "locked_by_cli_override"
    assert result.state.context["resolved_bindings"]["key"]["columns"] == ["trade_id"]


def test_action_details_include_columns_with_findings(tmp_path: Path) -> None:
    result = run_agent_mode(
        input_path="sample_data/broken/orders_duplicate_keys.csv",
        output_dir=tmp_path,
        config_path="config/default_config.json",
    )
    duplicate_action = next(action for action in result.state.actions if action.action_name == "duplicate_keys")
    assert "columns_with_findings" in duplicate_action.details
    assert "finding_count_by_column" in duplicate_action.details
