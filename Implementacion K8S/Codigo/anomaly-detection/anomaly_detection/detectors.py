"""Detectores multivariados no supervisados: IsolationForest y One-Class SVM con núcleo RBF.

Los dos se entrenan sobre features escaladas y exponen el mismo contrato: un score donde
mayor es más anómalo y una flag que vale True cuando el score es positivo.
"""

from dataclasses import dataclass

import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM


@dataclass(frozen=True)
class Detection:
    score: pd.Series
    flag: pd.Series


def fit_isolation_forest(
    features: pd.DataFrame,
    contamination: float = 0.10,
    n_estimators: int = 300,
    random_state: int = 42,
) -> Pipeline:
    forest = IsolationForest(
        n_estimators=n_estimators,
        max_samples=min(256, len(features)),
        contamination=contamination,
        random_state=random_state,
    )
    return make_pipeline(StandardScaler(), forest).fit(features)


def fit_one_class_svm(features: pd.DataFrame, nu: float = 0.10, gamma: float | str = "scale") -> Pipeline:
    return make_pipeline(StandardScaler(), OneClassSVM(kernel="rbf", nu=nu, gamma=gamma)).fit(features)


def detect(model: Pipeline, features: pd.DataFrame) -> Detection:
    score = pd.Series(-model.decision_function(features), index=features.index)
    return Detection(score=score, flag=score > 0)
