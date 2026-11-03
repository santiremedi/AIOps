"""Evaluación de detectores contra etiquetas, cuando el dataset las trae."""

import pandas as pd
from sklearn.metrics import average_precision_score, precision_recall_fscore_support


def classification_metrics(labels: pd.Series, flag: pd.Series, score: pd.Series) -> pd.Series:
    precision, recall, f1, _ = precision_recall_fscore_support(labels, flag, average="binary", zero_division=0)
    return pd.Series({
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "average_precision": average_precision_score(labels, score),
        "alerts": int(flag.sum()),
    })


def alerts_by_group(groups: pd.Series, flags: pd.DataFrame) -> pd.DataFrame:
    counts = flags.groupby(groups).sum().astype(int)
    counts.insert(0, "minutes", groups.value_counts())
    return counts


def first_alert(timestamps: pd.Series, flag: pd.Series) -> pd.Timestamp | None:
    flagged = timestamps[flag]
    return flagged.iloc[0] if len(flagged) else None
