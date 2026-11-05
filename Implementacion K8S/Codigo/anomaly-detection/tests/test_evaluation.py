import pandas as pd
import pytest

from anomaly_detection.evaluation import alerts_by_group, classification_metrics, first_alert

LABELS = pd.Series([False, False, True, True])


def test_classification_metrics_compare_flags_with_labels():
    flag = pd.Series([False, True, True, False])
    score = pd.Series([0.1, 0.2, 0.9, 0.8])

    metrics = classification_metrics(LABELS, flag, score)

    assert metrics["precision"] == pytest.approx(0.5)
    assert metrics["recall"] == pytest.approx(0.5)
    assert metrics["f1"] == pytest.approx(0.5)
    assert metrics["average_precision"] == pytest.approx(1.0)
    assert metrics["alerts"] == 2


def test_alerts_by_group_counts_flagged_minutes_per_group():
    groups = pd.Series(["normal", "normal", "incident", "incident"])
    flags = pd.DataFrame({"detector": [False, True, True, True]})

    counts = alerts_by_group(groups, flags)

    assert counts.loc["incident"].tolist() == [2, 2]
    assert counts.loc["normal"].tolist() == [2, 1]


def test_first_alert_returns_the_earliest_flagged_timestamp():
    timestamps = pd.Series(pd.date_range("2026-01-01", periods=4, freq="min"))

    assert first_alert(timestamps, pd.Series([False, False, True, True])) == timestamps[2]
    assert first_alert(timestamps, pd.Series([False] * 4)) is None
