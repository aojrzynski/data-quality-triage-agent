import sys

import pytest

from src import cli


def test_parse_args_defaults_to_deterministic_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["prog", "--input", "sample_data/clean/orders_clean.csv"])
    args = cli.parse_args()
    assert args.mode == "deterministic"


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
