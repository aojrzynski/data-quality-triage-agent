"""Dataset input/output helpers.

This module handles:
- loading a CSV into a pandas DataFrame
- saving structured JSON output
- saving Markdown reports

Important design idea:
The rest of the agent should not care where the data came from.
Later, we can extend this module to support XLSX, JSON, or Parquet
without changing the rest of the pipeline much.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def load_csv(path: str | Path) -> pd.DataFrame:
    """Load a CSV file into a pandas DataFrame.

    Args:
        path: Path to a CSV file.

    Returns:
        A pandas DataFrame containing the file contents.
    """
    csv_path = Path(path)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    return pd.read_csv(csv_path)


def save_json(path: str | Path, payload: dict[str, Any]) -> None:
    """Save a dictionary to a JSON file.

    Args:
        path: Destination file path.
        payload: Data to write as JSON.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def save_markdown(path: str | Path, content: str) -> None:
    """Save Markdown text to a file.

    Args:
        path: Destination file path.
        content: Markdown text to write.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        f.write(content)