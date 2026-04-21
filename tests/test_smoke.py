from pathlib import Path

from src.io import load_csv
from src.profiling import build_dataset_profile, dataset_name_from_path


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
    name = dataset_name_from_path(Path("sample_data/clean/orders_clean.csv"))
    assert name == "orders_clean.csv"


def test_build_dataset_profile() -> None:
    df = load_csv("sample_data/clean/orders_clean.csv")
    profile = build_dataset_profile(df, "orders_clean.csv")

    assert profile.dataset_name == "orders_clean.csv"
    assert profile.row_count == 30
    assert profile.column_count == 6
    assert "order_id" in profile.columns
    assert profile.null_counts["customer_id"] == 0