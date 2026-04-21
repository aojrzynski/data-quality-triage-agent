"""Dataset profiling logic.

This module describes a dataset in a structured way.
It does not decide whether anything is "bad" yet.
It simply measures and summarizes what is present.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.models import DatasetProfile


def build_dataset_profile(
    df: pd.DataFrame,
    dataset_name: str,
) -> DatasetProfile:
    """Create a basic profile for a dataset.

    Args:
        df: The dataset as a pandas DataFrame.
        dataset_name: A friendly name for the dataset, usually the filename.

    Returns:
        A DatasetProfile object containing summary information.
    """
    inferred_dtypes = {column: str(dtype) for column, dtype in df.dtypes.items()}
    null_counts = {column: int(df[column].isna().sum()) for column in df.columns}
    unique_counts = {column: int(df[column].nunique(dropna=True)) for column in df.columns}

    return DatasetProfile(
        dataset_name=dataset_name,
        row_count=int(len(df)),
        column_count=int(len(df.columns)),
        columns=list(df.columns),
        inferred_dtypes=inferred_dtypes,
        null_counts=null_counts,
        unique_counts=unique_counts,
    )


def dataset_name_from_path(path: str | Path) -> str:
    """Extract a dataset name from a file path."""
    return Path(path).name