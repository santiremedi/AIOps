"""Carga de datasets operacionales en CSV."""

from pathlib import Path

import pandas as pd


def load_csv(path: str | Path, timestamp_column: str | None = "timestamp") -> pd.DataFrame:
    data = pd.read_csv(path)
    if timestamp_column is not None:
        data[timestamp_column] = pd.to_datetime(data[timestamp_column])
        data = data.sort_values(timestamp_column, ignore_index=True)
    return data
