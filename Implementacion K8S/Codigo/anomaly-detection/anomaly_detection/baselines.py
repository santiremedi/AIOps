"""Detectores univariados de línea base: k-sigma y z-score robusto (MAD)."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

MAD_TO_SIGMA = 1.4826


@dataclass(frozen=True)
class UnivariateBaseline:
    center: float
    scale: float

    def score(self, values: pd.Series) -> pd.Series:
        distance = (values - self.center).abs()
        if self.scale > 0:
            return distance / self.scale
        return distance.where(distance == 0, np.inf)

    def flag(self, values: pd.Series, k: float = 3.0) -> pd.Series:
        return self.score(values) > k


def fit_k_sigma(values: pd.Series) -> UnivariateBaseline:
    return UnivariateBaseline(center=values.mean(), scale=values.std(ddof=1))


def fit_mad(values: pd.Series) -> UnivariateBaseline:
    median = values.median()
    mad = (values - median).abs().median()
    return UnivariateBaseline(center=median, scale=MAD_TO_SIGMA * mad)
