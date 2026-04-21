"""Generate small synthetic sample datasets for the Data Quality Triage Agent."""

from __future__ import annotations

import csv
import pandas as pd
import json
from copy import deepcopy
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = ROOT / "sample_data" / "clean"
BROKEN_DIR = ROOT / "sample_data" / "broken"
EXPECTED_DIR = ROOT / "tests" / "fixtures" / "expected"

FIELDNAMES = ["order_id", "customer_id", "order_date", "status", "region", "amount"]


def build_clean_rows() -> list[dict[str, str]]:
    """Create a small clean orders dataset."""
    statuses = ["pending", "shipped", "delivered", "cancelled"]
    regions = ["North", "South", "East", "West"]

    start_date = date(2025, 1, 1)
    rows: list[dict[str, str]] = []

    for i in range(1, 31):
        row = {
            "order_id": f"ORD-{i:04d}",
            "customer_id": f"CUST-{1000 + i}",
            "order_date": (start_date + timedelta(days=i - 1)).isoformat(),
            "status": statuses[(i - 1) % len(statuses)],
            "region": regions[(i - 1) % len(regions)],
            "amount": f"{49.5 + (i * 3.25):.2f}",
        }
        rows.append(row)

    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    """Write rows to a CSV file using the standard fieldnames."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def write_excel(path: Path, rows: list[dict[str, str]]) -> None:
    """Write rows to an Excel file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_excel(path, index=False)

def write_excel_with_columns(
    path: Path,
    rows: list[dict[str, str]],
    columns: list[str],
) -> None:
    """Write rows to an Excel file using an explicit column order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows, columns=columns)
    df.to_excel(path, index=False)


def write_json(path: Path, payload: dict) -> None:
    """Write a JSON payload to file."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def build_nulls_dataset(clean_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Create a dataset with missing customer IDs."""
    rows = deepcopy(clean_rows)

    for idx in [6, 13, 20]:
        rows[idx]["customer_id"] = ""

    return rows


def build_duplicate_keys_dataset(clean_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Create a dataset with duplicate order IDs."""
    rows = deepcopy(clean_rows)

    rows[10]["order_id"] = rows[4]["order_id"]
    rows[11]["order_id"] = rows[4]["order_id"]

    return rows


def build_bad_categories_dataset(clean_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Create a dataset with typo / unexpected status values."""
    rows = deepcopy(clean_rows)

    rows[7]["status"] = "pendng"
    rows[15]["status"] = "shiped"
    rows[23]["status"] = "cncelled"

    return rows


def build_date_gaps_dataset(clean_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Shift later dates forward by 2 days, creating a gap in the sequence."""
    rows = deepcopy(clean_rows)

    for idx in range(10, len(rows)):
        original = datetime.strptime(rows[idx]["order_date"], "%Y-%m-%d").date()
        rows[idx]["order_date"] = (original + timedelta(days=2)).isoformat()

    return rows


def build_outliers_dataset(clean_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Create a dataset with a clearly extreme amount value."""
    rows = deepcopy(clean_rows)
    rows[4]["amount"] = "9999.99"
    return rows


def build_schema_surprises_dataset(clean_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Create a dataset with one missing column and one extra column."""
    rows: list[dict[str, str]] = []

    for row in deepcopy(clean_rows):
        new_row = {
            "order_id": row["order_id"],
            "customer_id": row["customer_id"],
            "order_date": row["order_date"],
            "status": row["status"],
            "amount": row["amount"],
            "sales_channel": "online",
        }
        rows.append(new_row)

    return rows


def main() -> None:
    """Generate all sample datasets and expected result fixtures."""
    clean_rows = build_clean_rows()

    # Clean dataset
    write_csv(CLEAN_DIR / "orders_clean.csv", clean_rows)
    write_excel(CLEAN_DIR / "orders_clean.xlsx", clean_rows)

    # Broken datasets
    nulls_rows = build_nulls_dataset(clean_rows)
    duplicate_rows = build_duplicate_keys_dataset(clean_rows)
    bad_category_rows = build_bad_categories_dataset(clean_rows)
    date_gaps_rows = build_date_gaps_dataset(clean_rows)
    outliers_rows = build_outliers_dataset(clean_rows)
    schema_surprises_rows = build_schema_surprises_dataset(clean_rows)

    write_csv(BROKEN_DIR / "orders_nulls.csv", nulls_rows)
    write_csv(BROKEN_DIR / "orders_duplicate_keys.csv", duplicate_rows)
    write_csv(BROKEN_DIR / "orders_bad_categories.csv", bad_category_rows)
    write_csv(BROKEN_DIR / "orders_date_gaps.csv", date_gaps_rows)
    write_csv(BROKEN_DIR / "orders_outliers.csv", outliers_rows)

    write_excel(BROKEN_DIR / "orders_nulls.xlsx", nulls_rows)
    write_excel(BROKEN_DIR / "orders_duplicate_keys.xlsx", duplicate_rows)
    write_excel(BROKEN_DIR / "orders_bad_categories.xlsx", bad_category_rows)
    write_excel(BROKEN_DIR / "orders_date_gaps.xlsx", date_gaps_rows)
    write_excel(BROKEN_DIR / "orders_outliers.xlsx", outliers_rows)

    # Schema surprises dataset needs custom fieldnames because its columns differ
    schema_fieldnames = [
        "order_id",
        "customer_id",
        "order_date",
        "status",
        "amount",
        "sales_channel",
    ]
    with (BROKEN_DIR / "orders_schema_surprises.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=schema_fieldnames)
        writer.writeheader()
        writer.writerows(schema_surprises_rows)
        
    write_excel_with_columns(
        BROKEN_DIR / "orders_schema_surprises.xlsx",
        schema_surprises_rows,
        schema_fieldnames,
    )

    # Expected findings
    write_json(
        EXPECTED_DIR / "orders_nulls_expected.json",
        {
            "dataset": "orders_nulls.csv",
            "expected_findings": [
                {
                    "type": "missing_values",
                    "column": "customer_id",
                    "severity": "high",
                    "min_count": 3,
                }
            ],
        },
    )

    write_json(
        EXPECTED_DIR / "orders_duplicate_keys_expected.json",
        {
            "dataset": "orders_duplicate_keys.csv",
            "expected_findings": [
                {
                    "type": "duplicate_key",
                    "column": "order_id",
                    "severity": "critical",
                }
            ],
        },
    )

    write_json(
        EXPECTED_DIR / "orders_bad_categories_expected.json",
        {
            "dataset": "orders_bad_categories.csv",
            "expected_findings": [
                {
                    "type": "unexpected_values",
                    "column": "status",
                    "severity": "medium",
                    "unexpected_values": ["pendng", "shiped", "cncelled"],
                }
            ],
        },
    )

    write_json(
        EXPECTED_DIR / "orders_date_gaps_expected.json",
        {
            "dataset": "orders_date_gaps.csv",
            "expected_findings": [
                {
                    "type": "date_gaps",
                    "column": "order_date",
                    "severity": "medium",
                    "min_gap_count": 2,
                }
            ],
        },
    )

    write_json(
        EXPECTED_DIR / "orders_outliers_expected.json",
        {
            "dataset": "orders_outliers.csv",
            "expected_findings": [
                {
                    "type": "numeric_outliers",
                    "column": "amount",
                    "severity": "medium",
                    "min_outlier_count": 1,
                }
            ],
        },
    )

    write_json(
        EXPECTED_DIR / "orders_schema_surprises_expected.json",
        {
            "dataset": "orders_schema_surprises.csv",
            "expected_findings": [
                {
                    "type": "schema_surprises",
                    "column": None,
                    "severity": "high",
                    "missing_columns": ["region"],
                    "unexpected_columns": ["sales_channel"],
                }
            ],
        },
    )

    print("Sample data generated successfully.")
    print(f"Clean dataset:   {CLEAN_DIR / 'orders_clean.csv'}")
    print(f"Broken dataset:  {BROKEN_DIR / 'orders_nulls.csv'}")
    print(f"Broken dataset:  {BROKEN_DIR / 'orders_duplicate_keys.csv'}")
    print(f"Broken dataset:  {BROKEN_DIR / 'orders_bad_categories.csv'}")
    print(f"Broken dataset:  {BROKEN_DIR / 'orders_date_gaps.csv'}")
    print(f"Broken dataset:  {BROKEN_DIR / 'orders_outliers.csv'}")
    print(f"Broken dataset:  {BROKEN_DIR / 'orders_schema_surprises.csv'}")
    print(f"Expected files:  {EXPECTED_DIR}")


if __name__ == "__main__":
    main()