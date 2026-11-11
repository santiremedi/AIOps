import pytest

from anomaly_detection.detectors import detect, fit_isolation_forest, fit_one_class_svm
from anomaly_detection.synthetic import FEATURES, generate_lab_dataset

DETECTOR_FITS = {"isolation_forest": fit_isolation_forest, "one_class_svm": fit_one_class_svm}


@pytest.fixture(scope="module")
def lab_data():
    return generate_lab_dataset()


@pytest.fixture(scope="module", params=DETECTOR_FITS)
def detection(request, lab_data):
    model = DETECTOR_FITS[request.param](lab_data[FEATURES])
    return detect(model, lab_data[FEATURES])


def test_flag_is_a_positive_score(detection):
    assert detection.flag.equals(detection.score > 0)


def test_keeps_the_index_of_the_features(detection, lab_data):
    assert detection.score.index.equals(lab_data.index)


def test_alert_budget_follows_contamination_and_nu(detection):
    assert detection.flag.sum() == pytest.approx(30, abs=3)


def test_flags_every_micro_burst_minute(detection, lab_data):
    assert detection.flag[lab_data["kind"] == "micro_burst"].all()


def test_ranks_the_5xx_incident_above_normal_traffic(detection, lab_data):
    median_score_by_kind = detection.score.groupby(lab_data["kind"]).median()

    assert median_score_by_kind["incidente_5xx"] > median_score_by_kind["normal"]


def test_isolation_forest_flags_every_5xx_incident_minute(lab_data):
    detection = detect(fit_isolation_forest(lab_data[FEATURES]), lab_data[FEATURES])

    assert detection.flag[lab_data["kind"] == "incidente_5xx"].all()


def test_isolation_forest_is_reproducible_with_the_same_seed(lab_data):
    first = detect(fit_isolation_forest(lab_data[FEATURES], random_state=1), lab_data[FEATURES])
    second = detect(fit_isolation_forest(lab_data[FEATURES], random_state=1), lab_data[FEATURES])

    assert first.score.equals(second.score)
