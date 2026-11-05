import pandas as pd
import pytest

from anomaly_detection.synthetic import ANOMALOUS_KINDS, FEATURES, generate_lab_dataset


@pytest.fixture(scope="module")
def lab_data():
    return generate_lab_dataset()


def test_has_one_row_per_minute_for_five_hours(lab_data):
    assert len(lab_data) == 300
    assert lab_data["timestamp"].diff().dropna().eq(pd.Timedelta(minutes=1)).all()


def test_injects_each_kind_for_its_window(lab_data):
    expected_minutes = {
        "batch": 20, "spike_error": 3, "incidente_5xx": 8, "timeouts": 4, "pico_carga": 8,
        "latencia_silenciosa": 6, "combo_sutil": 7, "degradacion": 18, "cpu_latencia": 5, "micro_burst": 2,
    }
    minutes_by_kind = lab_data["kind"].value_counts()
    for kind, minutes in expected_minutes.items():
        assert minutes_by_kind[kind] == minutes


def test_labels_only_anomalous_kinds(lab_data):
    assert lab_data["is_anomaly"].equals(lab_data["kind"].isin(ANOMALOUS_KINDS))
    assert lab_data["is_anomaly"].sum() == 53


def test_same_seed_reproduces_the_dataset():
    pd.testing.assert_frame_equal(generate_lab_dataset(seed=7), generate_lab_dataset(seed=7))


def test_different_seed_changes_the_metrics(lab_data):
    assert not lab_data[FEATURES].equals(generate_lab_dataset(seed=7)[FEATURES])
