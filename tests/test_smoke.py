from src.cli import main


def test_cli_exists() -> None:
    assert callable(main)