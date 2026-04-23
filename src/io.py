"""Dataset input/output helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def load_csv(path: str | Path) -> pd.DataFrame:
    """Load a CSV file into a pandas DataFrame."""
    csv_path = Path(path)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    return pd.read_csv(csv_path)


def load_excel(path: str | Path, sheet_name: str | int = 0) -> pd.DataFrame:
    """Load an Excel file into a pandas DataFrame."""
    excel_path = Path(path)

    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    return pd.read_excel(excel_path, sheet_name=sheet_name)


def list_excel_sheets(path: str | Path) -> list[str]:
    """List worksheet names in an Excel workbook."""
    excel_path = Path(path)

    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    workbook = pd.ExcelFile(excel_path)
    return [str(name) for name in workbook.sheet_names]


def load_dataset(path: str | Path, sheet_name: str | int = 0) -> pd.DataFrame:
    """Load a supported dataset file based on its extension.

    Supported formats:
    - .csv
    - .xlsx
    """
    dataset_path = Path(path)
    suffix = dataset_path.suffix.lower()

    if suffix == ".csv":
        return load_csv(dataset_path)

    if suffix == ".xlsx":
        return load_excel(dataset_path, sheet_name=sheet_name)

    raise ValueError(
        f"Unsupported file format: {suffix}. Supported formats are .csv and .xlsx"
    )


def load_json(path: str | Path) -> dict[str, Any]:
    """Load a JSON file into a Python dictionary."""
    json_path = Path(path)

    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str | Path, payload: dict[str, Any]) -> None:
    """Save a dictionary to a JSON file."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def save_markdown(path: str | Path, content: str) -> None:
    """Save Markdown text to a file."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        f.write(content)
