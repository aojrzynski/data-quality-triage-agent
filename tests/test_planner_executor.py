import json
from pathlib import Path

import pandas as pd

from src.agent_runner import run_agent_mode
from src.config import load_agent_config
from src.intake import inspect_and_select_dataset
from src.planner import build_rule_based_plan
from src.role_inference import infer_column_roles


def test_planner_selects_sensible_subset_for_orders_dataset() -> None:
    config = load_agent_config()
    intake_result = inspect_and_select_dataset("sample_data/clean/orders_clean.csv")
    inference = infer_column_roles(intake_result.df)

    plan = build_rule_based_plan(intake_result, inference, config)
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

    plan = build_rule_based_plan(intake_result, inference, config)
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
    assert result.state.stop_rationale.code == "PLAN_COMPLETED"
    assert result.artifacts.trace_json_path.exists()


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


def test_agent_skips_role_bound_tool_when_no_binding_available(tmp_path: Path) -> None:
    result = run_agent_mode(
        input_path="tests/fixtures/role_inference/trades_stage7.csv",
        output_dir=tmp_path,
        config_path="config/default_config.json",
        agent_date_columns="does_not_exist",
    )

    date_action = next(action for action in result.state.actions if action.action_name == "date_gaps")
    assert date_action.status == "skipped"
    assert date_action.details["bound_columns"] == []
    assert "Override was provided" in date_action.details["skip_reason"]
