"""Dataset del obligatorio que dieron los docentes: un servicio de checkout, una fila por minuto.

Las anomalías se inyectan en el mismo orden que en el cuaderno de los docentes, así la misma
semilla reproduce exactamente los mismos datos.
"""

import numpy as np
import pandas as pd

FEATURES = ["requests", "error_rate", "latency_ms", "cpu_pct"]
ANOMALOUS_KINDS = frozenset({
    "spike_error", "incidente_5xx", "timeouts", "latencia_silenciosa",
    "combo_sutil", "degradacion", "cpu_latencia", "micro_burst",
})


class _CheckoutService:
    def __init__(self, seed: int):
        self.rng = np.random.default_rng(seed)
        self.minutes = pd.date_range("2026-06-03 08:00", periods=300, freq="min")
        self.kind = np.full(len(self.minutes), "normal", dtype=object)
        self._generate_normal_traffic()

    def _generate_normal_traffic(self):
        n = len(self.minutes)
        hour = self.minutes.hour.to_numpy() + self.minutes.minute.to_numpy() / 60.0
        traffic = 70 + 90 * np.clip(np.sin((hour - 8) * np.pi / 6), 0, None)
        self.requests = np.maximum(25, np.rint(traffic + self.rng.normal(0, 8, n))).astype(float)
        self.error_rate = np.clip(0.0035 + 0.000045 * self.requests + self.rng.normal(0, 0.0010, n), 0.0008, None)
        self.latency_ms = np.clip(68 + 0.22 * self.requests + self.rng.normal(0, 6.5, n), 40, None)
        self.cpu_pct = np.clip(16 + 0.17 * self.requests + self.rng.normal(0, 4.0, n), 8, None)

    def window(self, start: str, minutes: int, kind: str) -> np.ndarray:
        begin = pd.Timestamp(start)
        mask = np.asarray((self.minutes >= begin) & (self.minutes < begin + pd.Timedelta(minutes=minutes)))
        self.kind[mask] = kind
        return mask

    def to_frame(self) -> pd.DataFrame:
        data = pd.DataFrame({
            "timestamp": self.minutes,
            "requests": self.requests,
            "error_rate": self.error_rate,
            "latency_ms": self.latency_ms,
            "cpu_pct": self.cpu_pct,
            "kind": self.kind,
        })
        data["is_anomaly"] = data["kind"].isin(ANOMALOUS_KINDS)
        return data


def _inject_batch_jobs(service: _CheckoutService):
    for start in ("2026-06-03 08:25", "2026-06-03 09:12", "2026-06-03 10:30", "2026-06-03 11:42"):
        mask = service.window(start, 5, "batch")
        size = mask.sum()
        service.cpu_pct[mask] = service.rng.uniform(70, 84, size)
        service.requests[mask] = np.maximum(25, service.requests[mask] - service.rng.integers(8, 14, size))
        service.error_rate[mask] = np.clip(
            0.0035 + 0.000045 * service.requests[mask] + service.rng.normal(0, 0.0008, size), 0.0008, None)
        service.latency_ms[mask] = np.clip(68 + 0.22 * service.requests[mask] + service.rng.normal(0, 5.0, size), 40, None)


def _inject_error_spikes(service: _CheckoutService):
    for start in ("2026-06-03 08:18", "2026-06-03 08:41", "2026-06-03 09:05"):
        mask = service.window(start, 1, "spike_error")
        service.error_rate[mask] = service.rng.uniform(0.021, 0.025, mask.sum())


def _inject_5xx_incident(service: _CheckoutService):
    mask = service.window("2026-06-03 09:50", 8, "incidente_5xx")
    size = mask.sum()
    service.requests[mask] = service.rng.integers(30, 44, size)
    service.error_rate[mask] = service.rng.uniform(0.036, 0.048, size)
    service.latency_ms[mask] = service.rng.uniform(210, 260, size)
    service.cpu_pct[mask] = service.rng.uniform(28, 40, size)


def _inject_timeouts(service: _CheckoutService):
    mask = service.window("2026-06-03 09:22", 4, "timeouts")
    service.error_rate[mask] = service.rng.uniform(0.023, 0.028, mask.sum())
    service.latency_ms[mask] = service.rng.uniform(175, 200, mask.sum())


def _inject_load_peak(service: _CheckoutService):
    mask = service.window("2026-06-03 11:18", 8, "pico_carga")
    size = mask.sum()
    service.requests[mask] = service.rng.integers(165, 185, size)
    service.error_rate[mask] = 0.0035 + 0.000045 * service.requests[mask] + service.rng.normal(0, 0.0007, size)
    service.latency_ms[mask] = 68 + 0.22 * service.requests[mask] + service.rng.normal(0, 5.0, size)
    service.cpu_pct[mask] = 16 + 0.17 * service.requests[mask] + service.rng.normal(0, 3.5, size)


def _inject_silent_latency(service: _CheckoutService):
    mask = service.window("2026-06-03 10:40", 6, "latencia_silenciosa")
    service.latency_ms[mask] = service.rng.uniform(195, 230, mask.sum())


def _inject_subtle_combo(service: _CheckoutService):
    mask = service.window("2026-06-03 10:08", 7, "combo_sutil")
    size = mask.sum()
    service.requests[mask] = service.rng.integers(50, 62, size)
    service.error_rate[mask] = service.rng.uniform(0.0132, 0.0140, size)
    service.latency_ms[mask] = service.rng.uniform(118, 128, size)
    service.cpu_pct[mask] = 16 + 0.17 * service.requests[mask] + service.rng.normal(0, 3.5, size)


def _inject_degradation(service: _CheckoutService):
    mask = service.window("2026-06-03 11:50", 18, "degradacion")
    service.latency_ms[mask] = service.latency_ms[mask] + np.linspace(8, 95, mask.sum())


def _inject_cpu_latency(service: _CheckoutService):
    mask = service.window("2026-06-03 12:22", 5, "cpu_latencia")
    service.cpu_pct[mask] = service.rng.uniform(78, 90, mask.sum())
    service.latency_ms[mask] = service.rng.uniform(180, 215, mask.sum())


def _inject_micro_burst(service: _CheckoutService):
    mask = service.window("2026-06-03 12:41", 2, "micro_burst")
    service.error_rate[mask] = service.rng.uniform(0.055, 0.070, mask.sum())
    service.latency_ms[mask] = service.rng.uniform(240, 280, mask.sum())


_INJECTIONS_IN_ORDER = (
    _inject_batch_jobs,
    _inject_error_spikes,
    _inject_5xx_incident,
    _inject_timeouts,
    _inject_load_peak,
    _inject_silent_latency,
    _inject_subtle_combo,
    _inject_degradation,
    _inject_cpu_latency,
    _inject_micro_burst,
)


def generate_dataset(seed: int = 42) -> pd.DataFrame:
    service = _CheckoutService(seed)
    for inject in _INJECTIONS_IN_ORDER:
        inject(service)
    return service.to_frame()
