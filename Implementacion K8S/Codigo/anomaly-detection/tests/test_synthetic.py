import pandas as pd
import pytest

from anomaly_detection.synthetic import ANOMALOUS_KINDS, FEATURES, generate_dataset


@pytest.fixture(scope="module")
def data():
    return generate_dataset()


def test_has_one_row_per_minute_for_five_hours(data):
    assert len(data) == 300
    assert data["timestamp"].diff().dropna().eq(pd.Timedelta(minutes=1)).all()


def test_injects_each_kind_for_its_window(data):
    expected_minutes = {
        "batch": 20, "spike_error": 3, "incidente_5xx": 8, "timeouts": 4, "pico_carga": 8,
        "latencia_silenciosa": 6, "combo_sutil": 7, "degradacion": 18, "cpu_latencia": 5, "micro_burst": 2,
    }
    minutes_by_kind = data["kind"].value_counts()
    for kind, minutes in expected_minutes.items():
        assert minutes_by_kind[kind] == minutes


def test_labels_only_anomalous_kinds(data):
    assert data["is_anomaly"].equals(data["kind"].isin(ANOMALOUS_KINDS))
    assert data["is_anomaly"].sum() == 53


def test_same_seed_reproduces_the_dataset():
    pd.testing.assert_frame_equal(generate_dataset(seed=7), generate_dataset(seed=7))


def test_different_seed_changes_the_metrics(data):
    assert not data[FEATURES].equals(generate_dataset(seed=7)[FEATURES])
