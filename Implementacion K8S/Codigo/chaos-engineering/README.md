# Chaos Engineering

Requiere: app en K8s + port-forward activo.

Punto de entrada: `./chaos.sh requests|cpu|memory|storage|network|disconnect|all` (`PAUSE=60` entre escenarios con `all`). Registra cada ejecución en `chaos-runs.log`.

| Script | Uso |
|--------|-----|
| `chaos.sh` | `./chaos.sh <escenario>\|all` |
| `cpu-spike.sh` | `./cpu-spike.sh [deploy] [seg]` |
| `ram-spike.sh` | `./ram-spike.sh [deploy] [MB] [seg]` |
| `volume-spike.sh` | `./volume-spike.sh [deploy] [MB] [seg]` |
| `load-requests.sh` | `./load-requests.sh [N] [url]` |
| `network-chaos.sh` | `./network-chaos.sh cut [deploy] [seg]` o `./network-chaos.sh disconnect [deploy] [target] [seg]` |
| `db-freeze.sh` | `./db-freeze.sh [seg]` |
| `pod-failure.sh` | `./pod-failure.sh kill\|delete [deploy]` o `./pod-failure.sh db-down [N] [url]` |

`lib.sh` tiene las funciones comunes (namespace y búsqueda del pod); lo cargan los demás scripts.

Default deploy: pharmago-api-gateway (en `pod-failure.sh` y `network-chaos.sh`: pharmago-pharmacy-service, para no cortar el port-forward del gateway).

**Escenarios, efectos y dónde verlos:** ver [docs/scripts-de-caos.md](../../../docs/scripts-de-caos.md).

**Self-healing y circuit breaker:** ver [docs/alta-disponibilidad.md](../../../docs/alta-disponibilidad.md).

**Ver impacto en Grafana:** Dashboard "PharmaGo - Infra" → paneles "CPU por pod (pharmago)" y "Memoria por pod (pharmago)".
