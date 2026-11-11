import pytest

from anomaly_detection.detectors import detect, fit_isolation_forest, fit_one_class_svm
from anomaly_detection.synthetic import FEATURES, generate_dataset

DETECTOR_FITS = {"isolation_forest": fit_isolation_forest, "one_class_svm": fit_one_class_svm}


@pytest.fixture(scope="module")
def data():
    return generate_dataset()


@pytest.fixture(scope="module", params=DETECTOR_FITS)
def detection(request, data):
    model = DETECTOR_FITS[request.param](data[FEATURES])
    return detect(model, data[FEATURES])


def test_flag_is_a_positive_score(detection):
    assert detection.flag.equals(detection.score > 0)


def test_keeps_the_index_of_the_features(detection, data):
    assert detection.score.index.equals(data.index)


def test_alert_budget_follows_contamination_and_nu(detection):
    assert detection.flag.sum() == pytest.approx(30, abs=3)


def test_flags_every_micro_burst_minute(detection, data):
    assert detection.flag[data["kind"] == "micro_burst"].all()


def test_ranks_the_5xx_incident_above_normal_traffic(detection, data):
    median_score_by_kind = detection.score.groupby(data["kind"]).median()

    assert median_score_by_kind["incidente_5xx"] > median_score_by_kind["normal"]


def test_isolation_forest_flags_every_5xx_incident_minute(data):
    detection = detect(fit_isolation_forest(data[FEATURES]), data[FEATURES])

    assert detection.flag[data["kind"] == "incidente_5xx"].all()


def test_isolation_forest_is_reproducible_with_the_same_seed(data):
    first = detect(fit_isolation_forest(data[FEATURES], random_state=1), data[FEATURES])
    second = detect(fit_isolation_forest(data[FEATURES], random_state=1), data[FEATURES])

    assert first.score.equals(second.score)
