from src.checks import (
    check_duplicate_keys,
    check_missing_values,
    check_unexpected_categorical_values,
    run_checks,
)
from src.io import load_csv
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


def test_run_checks_on_clean_dataset_returns_no_findings() -> None:
    df = load_csv("sample_data/clean/orders_clean.csv")
    findings = run_checks(df)

    assert findings == []