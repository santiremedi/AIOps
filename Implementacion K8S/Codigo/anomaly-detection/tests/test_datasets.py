import pandas as pd

from anomaly_detection.datasets import load_csv


def test_load_csv_parses_and_sorts_by_timestamp(tmp_path):
    path = tmp_path / "metrics.csv"
    path.write_text("timestamp,requests\n2026-01-01 08:01,20\n2026-01-01 08:00,10\n")

    data = load_csv(path)

    assert pd.api.types.is_datetime64_any_dtype(data["timestamp"])
    assert data["requests"].tolist() == [10, 20]


def test_load_csv_without_timestamp_keeps_the_file_order(tmp_path):
    path = tmp_path / "metrics.csv"
    path.write_text("requests\n20\n10\n")

    assert load_csv(path, timestamp_column=None)["requests"].tolist() == [20, 10]
