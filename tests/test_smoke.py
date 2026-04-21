from src.checks import (
    check_date_gaps,
    check_duplicate_keys,
    check_missing_values,
    check_numeric_outliers,
    check_unexpected_categorical_values,
    run_checks,
)
from src.cli import compare_to_expected
from src.config import load_agent_config
from src.io import load_csv, load_json
from src.models import RunResult
from src.profiling import build_dataset_profile, dataset_name_from_path
from src.scoring import score_findings


def test_can_load_clean_csv() -> None:
    df = load_csv("sample_data/clean/orders_clean.csv")
    assert len(df) == 30
    assert list(df.columns) == [
        "order_id",
        "customer_id",
        "order_date",
        "status",
        "region",
        "amount",
    ]


def test_can_load_expected_json_fixture() -> None:
    payload = load_json("tests/fixtures/expected/orders_nulls_expected.json")
    assert payload["dataset"] == "orders_nulls.csv"
    assert len(payload["expected_findings"]) == 1


def test_can_load_default_config() -> None:
    config = load_agent_config()
    assert config.key_columns == ["order_id"]
    assert config.categorical_rules["status"] == [
        "pending",
        "shipped",
        "delivered",
        "cancelled",
    ]
    assert config.date_gap_columns == ["order_date"]
    assert config.numeric_outlier_columns == ["amount"]


def test_dataset_name_from_path() -> None:
    name = dataset_name_from_path("sample_data/clean/orders_clean.csv")
    assert name == "orders_clean.csv"


def test_build_dataset_profile() -> None:
    df = load_csv("sample_data/clean/orders_clean.csv")
    profile = build_dataset_profile(df, "orders_clean.csv")

    assert profile.dataset_name == "orders_clean.csv"
    assert profile.row_count == 30
    assert profile.column_count == 6
    assert "order_id" in profile.columns
    assert profile.null_counts["customer_id"] == 0


def test_missing_values_check_finds_customer_id_issue() -> None:
    df = load_csv("sample_data/broken/orders_nulls.csv")
    findings = check_missing_values(df)
    scored = score_findings(findings)

    matching = [
        finding
        for finding in scored
        if finding.finding_type == "missing_values" and finding.column == "customer_id"
    ]

    assert len(matching) == 1
    assert matching[0].severity == "high"
    assert matching[0].evidence["missing_count"] == 3


def test_duplicate_key_check_finds_order_id_issue() -> None:
    df = load_csv("sample_data/broken/orders_duplicate_keys.csv")
    findings = check_duplicate_keys(df, key_column="order_id")
    scored = score_findings(findings)

    assert len(scored) == 1
    assert scored[0].finding_type == "duplicate_key"
    assert scored[0].column == "order_id"
    assert scored[0].severity == "critical"


def test_unexpected_values_check_finds_status_typos() -> None:
    df = load_csv("sample_data/broken/orders_bad_categories.csv")
    findings = check_unexpected_categorical_values(
        df,
        column="status",
        allowed_values={"pending", "shipped", "delivered", "cancelled"},
    )
    scored = score_findings(findings)

    assert len(scored) == 1
    assert scored[0].finding_type == "unexpected_values"
    assert scored[0].column == "status"
    assert scored[0].severity == "medium"
    assert scored[0].evidence["unexpected_values"] == [
        "cncelled",
        "pendng",
        "shiped",
    ]


def test_date_gaps_check_finds_missing_dates() -> None:
    df = load_csv("sample_data/broken/orders_date_gaps.csv")
    findings = check_date_gaps(df, column="order_date")
    scored = score_findings(findings)

    assert len(scored) == 1
    assert scored[0].finding_type == "date_gaps"
    assert scored[0].column == "order_date"
    assert scored[0].severity == "medium"
    assert scored[0].evidence["missing_dates_count"] == 2


def test_numeric_outliers_check_finds_amount_issue() -> None:
    df = load_csv("sample_data/broken/orders_outliers.csv")
    findings = check_numeric_outliers(df, column="amount")
    scored = score_findings(findings)

    assert len(scored) == 1
    assert scored[0].finding_type == "numeric_outliers"
    assert scored[0].column == "amount"
    assert scored[0].severity == "medium"
    assert scored[0].evidence["outlier_count"] >= 1


def test_run_checks_on_clean_dataset_returns_no_findings() -> None:
    df = load_csv("sample_data/clean/orders_clean.csv")
    config = load_agent_config()
    findings = run_checks(df, config=config)

    assert findings == []


def test_compare_to_expected_passes_for_nulls_fixture() -> None:
    df = load_csv("sample_data/broken/orders_nulls.csv")
    profile = build_dataset_profile(df, "orders_nulls.csv")
    config = load_agent_config()
    findings = score_findings(run_checks(df, config=config))
    run_result = RunResult(
        dataset_name="orders_nulls.csv",
        profile=profile,
        findings=findings,
    )

    expected_payload = load_json("tests/fixtures/expected/orders_nulls_expected.json")
    comparison_messages = compare_to_expected(run_result, expected_payload)

    assert comparison_messages == []


def test_compare_to_expected_passes_for_duplicate_fixture() -> None:
    df = load_csv("sample_data/broken/orders_duplicate_keys.csv")
    profile = build_dataset_profile(df, "orders_duplicate_keys.csv")
    config = load_agent_config()
    findings = score_findings(run_checks(df, config=config))
    run_result = RunResult(
        dataset_name="orders_duplicate_keys.csv",
        profile=profile,
        findings=findings,
    )

    expected_payload = load_json("tests/fixtures/expected/orders_duplicate_keys_expected.json")
    comparison_messages = compare_to_expected(run_result, expected_payload)

    assert comparison_messages == []


def test_compare_to_expected_passes_for_bad_categories_fixture() -> None:
    df = load_csv("sample_data/broken/orders_bad_categories.csv")
    profile = build_dataset_profile(df, "orders_bad_categories.csv")
    config = load_agent_config()
    findings = score_findings(run_checks(df, config=config))
    run_result = RunResult(
        dataset_name="orders_bad_categories.csv",
        profile=profile,
        findings=findings,
    )

    expected_payload = load_json("tests/fixtures/expected/orders_bad_categories_expected.json")
    comparison_messages = compare_to_expected(run_result, expected_payload)

    assert comparison_messages == []


def test_compare_to_expected_passes_for_date_gaps_fixture() -> None:
    df = load_csv("sample_data/broken/orders_date_gaps.csv")
    profile = build_dataset_profile(df, "orders_date_gaps.csv")
    config = load_agent_config()
    findings = score_findings(run_checks(df, config=config))
    run_result = RunResult(
        dataset_name="orders_date_gaps.csv",
        profile=profile,
        findings=findings,
    )

    expected_payload = load_json("tests/fixtures/expected/orders_date_gaps_expected.json")
    comparison_messages = compare_to_expected(run_result, expected_payload)

    assert comparison_messages == []


def test_compare_to_expected_passes_for_outliers_fixture() -> None:
    df = load_csv("sample_data/broken/orders_outliers.csv")
    profile = build_dataset_profile(df, "orders_outliers.csv")
    config = load_agent_config()
    findings = score_findings(run_checks(df, config=config))
    run_result = RunResult(
        dataset_name="orders_outliers.csv",
        profile=profile,
        findings=findings,
    )

    expected_payload = load_json("tests/fixtures/expected/orders_outliers_expected.json")
    comparison_messages = compare_to_expected(run_result, expected_payload)

    assert comparison_messages == []