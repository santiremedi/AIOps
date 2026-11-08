import numpy as np
import pandas as pd
import pytest

from anomaly_detection.baselines import MAD_TO_SIGMA, fit_k_sigma, fit_mad
from anomaly_detection.synthetic import generate_dataset

STABLE = pd.Series([10.0, 11.0, 9.0, 10.0, 12.0, 8.0, 10.0, 11.0, 9.0, 10.0])
WITH_SPIKE = pd.concat([STABLE, pd.Series([100.0])], ignore_index=True)


def test_k_sigma_uses_mean_and_sample_standard_deviation():
    baseline = fit_k_sigma(STABLE)

    assert baseline.center == pytest.approx(STABLE.mean())
    assert baseline.scale == pytest.approx(STABLE.std(ddof=1))


def test_mad_scales_the_median_absolute_deviation():
    baseline = fit_mad(STABLE)

    assert baseline.center == 10.0
    assert baseline.scale == pytest.approx(MAD_TO_SIGMA * 1.0)


def test_a_spike_inflates_k_sigma_but_not_mad():
    assert fit_k_sigma(WITH_SPIKE).scale > 10 * fit_k_sigma(STABLE).scale
    assert fit_mad(WITH_SPIKE).scale == pytest.approx(fit_mad(STABLE).scale)


def test_flags_values_beyond_k_scales():
    baseline = fit_mad(STABLE)

    assert baseline.flag(pd.Series([10.0, 14.0, 15.0, 100.0])).tolist() == [False, False, True, True]


def test_zero_scale_scores_zero_at_the_center_and_infinite_elsewhere():
    baseline = fit_mad(pd.Series([5.0] * 10))

    assert baseline.score(pd.Series([5.0, 6.0])).tolist() == [0.0, np.inf]


def test_lab_error_spikes_inflate_k_sigma_more_than_mad():
    error_rate = generate_dataset()["error_rate"]

    assert fit_mad(error_rate).scale < fit_k_sigma(error_rate).scale / 2
