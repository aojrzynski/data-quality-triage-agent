import sys
from pathlib import Path

import pandas as pd
import pytest

from src import cli


def test_parse_args_defaults_to_deterministic_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["prog", "--input", "sample_data/clean/orders_clean.csv"])
    args = cli.parse_args()
    assert args.mode == "deterministic"
    assert args.sheet is None


def test_parse_args_accepts_explicit_deterministic_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "--input", "sample_data/clean/orders_clean.csv", "--mode", "deterministic"],
    )
    args = cli.parse_args()
    assert args.mode == "deterministic"


def test_agent_mode_runs_and_emits_trace(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "outputs"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--input",
            "sample_data/clean/orders_clean.csv",
            "--mode",
            "agent",
            "--output-dir",
            str(output_dir),
        ],
    )

    cli.main()

    captured = capsys.readouterr()
    assert "Mode: agent" in captured.out
    assert "Planned actions" in captured.out
    assert "Completed actions" in captured.out
    assert "Stop reason:" in captured.out
    assert "Agent report output:" in captured.out

    trace_path = output_dir / "orders_clean_agent_trace.json"
    report_path = output_dir / "orders_clean_agent_report.md"
    assert trace_path.exists()
    assert report_path.exists()


def test_cli_surfaces_auto_selected_sheet(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    workbook_path = tmp_path / "auto_sheet.xlsx"

    with pd.ExcelWriter(workbook_path) as writer:
        pd.DataFrame({"Unnamed: 0": [None, None, "x"]}).to_excel(
            writer,
            sheet_name="Cover",
            index=False,
        )
        pd.DataFrame({"order_id": [1, 2, 3], "amount": [10, 20, 30]}).to_excel(
            writer,
            sheet_name="Orders",
            index=False,
        )

    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "--input", str(workbook_path), "--output-dir", str(tmp_path / "outputs")],
    )

    cli.main()

    captured = capsys.readouterr()
    assert "Intake sheet selection: auto" in captured.out
    assert "Selected sheet: Orders" in captured.out
    assert "Suitability:" in captured.out
    assert "Inferred assumptions (informative only):" in captured.out
    assert "numeric_measure:" in captured.out


def test_cli_hard_failure_stops_before_outputs(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "outputs"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--input",
            "tests/fixtures/intake/empty_columns.csv",
            "--output-dir",
            str(output_dir),
        ],
    )

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1

    captured = capsys.readouterr()
    assert "Suitability: unsuitable (score=0)" in captured.out
    assert "Input is unsuitable for deterministic checks" in captured.out
    assert "Recommended action:" in captured.out
    assert "JSON output:" not in captured.out
    assert "Markdown output:" not in captured.out

    assert not output_dir.exists()


def test_agent_mode_hard_failure_stops_with_trace(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "outputs"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--input",
            "tests/fixtures/intake/empty_columns.csv",
            "--mode",
            "agent",
            "--output-dir",
            str(output_dir),
        ],
    )

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Mode: agent" in captured.out
    assert "Stop reason: INTAKE_HARD_FAILURE" in captured.out

    trace_path = output_dir / "empty_columns_agent_trace.json"
    assert trace_path.exists()


def test_cli_explicit_sheet_index_prints_resolved_sheet_name(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    workbook_path = tmp_path / "explicit_index.xlsx"

    with pd.ExcelWriter(workbook_path) as writer:
        pd.DataFrame({"cover": [None, None]}).to_excel(writer, sheet_name="Cover", index=False)
        pd.DataFrame({"order_id": [1, 2, 3], "amount": [10, 20, 30]}).to_excel(
            writer,
            sheet_name="Orders",
            index=False,
        )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--input",
            str(workbook_path),
            "--sheet",
            "1",
            "--output-dir",
            str(tmp_path / "outputs"),
        ],
    )

    cli.main()
    captured = capsys.readouterr()

    assert "Intake sheet selection: explicit" in captured.out
    assert "Selected sheet: Orders" in captured.out


def test_agent_mode_cli_accepts_override_flags(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "outputs"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--input",
            "tests/fixtures/role_inference/trades_stage7.csv",
            "--mode",
            "agent",
            "--output-dir",
            str(output_dir),
            "--agent-key-columns",
            "trade_id",
            "--agent-date-columns",
            "trade_date",
        ],
    )

    cli.main()
    captured = capsys.readouterr()
    assert "Mode: agent" in captured.out
    assert "Resolved bindings used:" in captured.out
    assert "key: trade_id (user_override)" in captured.out
    assert "date: trade_date (user_override)" in captured.out


def test_deterministic_mode_rejects_agent_override_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--input",
            "sample_data/clean/orders_clean.csv",
            "--mode",
            "deterministic",
            "--agent-key-columns",
            "order_id",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert "Agent-only override flags" in str(exc.value)
