"""Exportación de las métricas de PharmaGo desde la API HTTP de Prometheus.

Las features son las mismas métricas que vigilan las alertas de Grafana, agregadas a una sola
serie por feature: tráfico, errores y latencia de todos los servicios, y el peor pod de la app
en CPU, memoria y escritura a disco.
"""

import json
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

_SERVICES = 'job=~"PharmaGo.*"'
_APP_PODS = 'namespace="pharmago",container!="",pod=~"pharmago-(api-gateway|users-service|pharmacy-service|ui)-.*"'

FEATURE_QUERIES = {
    "requests_per_s": f"sum(rate(http_server_request_duration_seconds_count{{{_SERVICES}}}[1m]))",
    "error_5xx_pct": (
        f'100 * (sum(rate(http_server_request_duration_seconds_count{{{_SERVICES},http_response_status_code=~"5.."}}[1m])) or vector(0))'
        f" / sum(rate(http_server_request_duration_seconds_count{{{_SERVICES}}}[1m]))"
    ),
    "latency_p95_s": (
        f"histogram_quantile(0.95, sum by (le) (rate(http_server_request_duration_seconds_bucket{{{_SERVICES}}}[1m])))"
    ),
    "cpu_pct_of_limit": (
        f"max(sum by (pod) (rate(container_cpu_usage_seconds_total{{{_APP_PODS}}}[1m]))"
        ' / sum by (pod) (kube_pod_container_resource_limits{namespace="pharmago",resource="cpu"}) * 100)'
    ),
    "memory_pct_of_limit": (
        f"max(sum by (pod) (container_memory_working_set_bytes{{{_APP_PODS}}})"
        ' / sum by (pod) (kube_pod_container_resource_limits{namespace="pharmago",resource="memory"}) * 100)'
    ),
    "disk_writes_bytes_per_s": f"max(sum by (pod) (rate(container_fs_writes_bytes_total{{{_APP_PODS}}}[1m])))",
}


class PrometheusQueryError(Exception):
    pass


def series_from_response(payload: dict, name: str) -> pd.Series:
    if payload.get("status") != "success":
        raise PrometheusQueryError(payload.get("error", "respuesta sin status success"))
    results = payload["data"]["result"]
    if len(results) > 1:
        raise PrometheusQueryError(f"{name}: la consulta devolvió {len(results)} series y se esperaba una")
    values = results[0]["values"] if results else []
    timestamps = pd.to_datetime([float(timestamp) for timestamp, _ in values], unit="s", utc=True)
    return pd.Series([float(value) for _, value in values], index=timestamps, name=name, dtype=float)


def query_range(base_url: str, query: str, start: pd.Timestamp, end: pd.Timestamp, step: str, name: str) -> pd.Series:
    parameters = urlencode({"query": query, "start": start.timestamp(), "end": end.timestamp(), "step": step})
    with urlopen(f"{base_url}/api/v1/query_range?{parameters}") as response:
        return series_from_response(json.load(response), name)


def export_features(base_url: str, start: pd.Timestamp, end: pd.Timestamp, step: str = "15s") -> pd.DataFrame:
    series = [query_range(base_url, query, start, end, step, name) for name, query in FEATURE_QUERIES.items()]
    return pd.concat(series, axis=1).rename_axis("timestamp").reset_index()
