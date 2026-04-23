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


def test_agent_mode_is_explicitly_not_implemented(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "--input", "sample_data/clean/orders_clean.csv", "--mode", "agent"],
    )

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "Agent mode is not implemented yet." in captured.out
    assert "Use --mode deterministic" in captured.out


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
