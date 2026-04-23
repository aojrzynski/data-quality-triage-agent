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
    assert all(action.status == "completed" for action in result.state.actions)
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
