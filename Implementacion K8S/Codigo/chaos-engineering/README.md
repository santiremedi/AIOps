# Chaos Engineering

Requiere: app en K8s + port-forward activo.

| Script | Uso |
|--------|-----|
| `cpu-spike.sh` | `./cpu-spike.sh [deploy] [seg]` |
| `ram-spike.sh` | `./ram-spike.sh [deploy] [MB]` |
| `volume-spike.sh` | `./volume-spike.sh [deploy] [MB]` |
| `load-requests.sh` | `./load-requests.sh [N] [url]` |
| `pod-failure.sh` | `./pod-failure.sh kill\|delete [deploy]` o `./pod-failure.sh db-down [N] [url]` |

Default deploy: pharmago-api-gateway (en `pod-failure.sh`: pharmago-pharmacy-service, para no cortar el port-forward del gateway).

**Self-healing y circuit breaker:** ver [docs/alta-disponibilidad.md](../../../docs/alta-disponibilidad.md).

**Ver impacto en Grafana:** Dashboard "PharmaGo - Infra" → paneles "CPU por pod (pharmago)" y "Memoria por pod (pharmago)".
