import pandas as pd
import pytest

from anomaly_detection.prometheus import PrometheusQueryError, series_from_response


def matrix_response(*results):
    return {"status": "success", "data": {"resultType": "matrix", "result": list(results)}}


def test_converts_a_single_series_to_utc_timestamps_and_floats():
    payload = matrix_response({"metric": {}, "values": [[1767254400, "1.5"], [1767254415, "2"]]})

    series = series_from_response(payload, "requests_per_s")

    assert series.name == "requests_per_s"
    assert series.tolist() == [1.5, 2.0]
    assert series.index[0] == pd.Timestamp("2026-01-01 08:00:00", tz="UTC")


def test_an_empty_result_is_an_empty_series():
    assert series_from_response(matrix_response(), "latency_p95_s").empty


def test_rejects_queries_that_return_more_than_one_series():
    payload = matrix_response({"metric": {"pod": "a"}, "values": []}, {"metric": {"pod": "b"}, "values": []})

    with pytest.raises(PrometheusQueryError, match="2 series"):
        series_from_response(payload, "cpu_pct_of_limit")


def test_reports_the_error_of_a_failed_query():
    with pytest.raises(PrometheusQueryError, match="parse error"):
        series_from_response({"status": "error", "error": "parse error"}, "requests_per_s")

