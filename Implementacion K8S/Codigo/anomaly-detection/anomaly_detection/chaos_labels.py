"""Etiquetas de un dataset a partir del registro de los escenarios de caos ejecutados."""

import pandas as pd

NORMAL = "normal"


def load_chaos_log(path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["start", "end"])


def label_by_scenario(timestamps: pd.Series, chaos_log: pd.DataFrame, effect_tail: pd.Timedelta) -> pd.Series:
    """Asigna a cada instante el escenario de caos activo, o "normal".

    `effect_tail` extiende cada escenario después de su fin: las métricas usan `rate(...[1m])`
    y siguen reflejando el caos durante esa ventana.
    """
    labels = pd.Series(NORMAL, index=timestamps.index, dtype=object)
    for scenario in chaos_log.itertuples():
        active = (timestamps >= scenario.start) & (timestamps < scenario.end + effect_tail)
        labels[active] = scenario.scenario
    return labels
