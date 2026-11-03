"""Arma el dataset de una sesión de caos: métricas de Prometheus etiquetadas por escenario.

Uso: python -m anomaly_detection.export_chaos_dataset data/chaos-log.csv data/chaos.csv
"""

import argparse

import pandas as pd

from anomaly_detection.chaos_labels import NORMAL, label_by_scenario, load_chaos_log
from anomaly_detection.prometheus import export_features


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chaos_log", help="CSV con scenario,start,end que escribe run-chaos-session.sh")
    parser.add_argument("output", help="CSV de salida")
    parser.add_argument("--prometheus", default="http://127.0.0.1:9090")
    parser.add_argument("--step", default="15s")
    parser.add_argument("--baseline-minutes", type=int, default=10, help="tráfico normal antes del primer escenario")
    parser.add_argument("--effect-tail-seconds", type=int, default=60)
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    chaos_log = load_chaos_log(arguments.chaos_log)
    start = chaos_log["start"].min() - pd.Timedelta(minutes=arguments.baseline_minutes)
    end = chaos_log["end"].max() + pd.Timedelta(seconds=arguments.effect_tail_seconds)

    dataset = export_features(arguments.prometheus, start, end, arguments.step)
    dataset["kind"] = label_by_scenario(
        dataset["timestamp"], chaos_log, pd.Timedelta(seconds=arguments.effect_tail_seconds))
    dataset["is_anomaly"] = dataset["kind"] != NORMAL
    dataset.to_csv(arguments.output, index=False)
    print(f"{len(dataset)} filas, {dataset['is_anomaly'].sum()} con caos activo -> {arguments.output}")


if __name__ == "__main__":
    main()
