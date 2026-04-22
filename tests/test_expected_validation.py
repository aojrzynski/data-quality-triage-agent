from src.expected_validation import compare_to_expected
from src.io import load_csv, load_json
from src.models import RunResult
from src.profiling import build_dataset_profile
from src.config import load_agent_config
from src.checks import run_checks
from src.scoring import score_findings


def _run_result_for_dataset(path: str) -> RunResult:
    df = load_csv(path)
    profile = build_dataset_profile(df, path.split("/")[-1])
    findings = score_findings(run_checks(df, config=load_agent_config()))
    return RunResult(dataset_name=path.split("/")[-1], profile=profile, findings=findings)


def test_compare_to_expected_returns_no_messages_on_match() -> None:
    run_result = _run_result_for_dataset("sample_data/broken/orders_nulls.csv")
    expected_payload = load_json("tests/fixtures/expected/orders_nulls_expected.json")

    assert compare_to_expected(run_result, expected_payload) == []


def test_compare_to_expected_reports_missing_expected_finding() -> None:
    run_result = _run_result_for_dataset("sample_data/clean/orders_clean.csv")
    expected_payload = {
        "expected_findings": [
            {"type": "missing_values", "column": "customer_id", "severity": "high"}
        ]
    }

    messages = compare_to_expected(run_result, expected_payload)
    assert len(messages) == 1
    assert "Missing expected finding" in messages[0]
