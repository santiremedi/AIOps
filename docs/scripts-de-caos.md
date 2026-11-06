# Scripts de caos

Cómo cumple PharmaGo el ítem "Scripts de caos" de la rúbrica: un script que prueba inyección de requests, sobrecarga de CPU, memoria y storage, interrupción de tráfico de red y desconexión de componentes internos.

El punto de entrada es [`chaos-engineering/chaos.sh`](../Implementacion%20K8S/Codigo/chaos-engineering/chaos.sh). Cada escenario delega en un script chico que también se puede correr solo.

## Escenarios

| Requisito | Comando | Qué hace | Efecto esperado | Dónde se ve |
|---|---|---|---|---|
| Inyección de requests | `chaos.sh requests` | 500 `POST /api/login` en paralelo al gateway (`load-requests.sh`) | Pico de tráfico; el rate limit por IP responde 429 | "Tráfico por servicio" y "Rate Limit Errors (429) por Endpoint" |
| Sobrecarga de CPU | `chaos.sh cpu` | 4 loops ocupados durante 60 s en un pod del gateway (`cpu-spike.sh`) | El pod llega al límite de CPU y lo throttlea; la latencia sube | "CPU por pod (pharmago)"; alerta *CPU de un pod de la app cerca del límite* |
| Sobrecarga de memoria | `chaos.sh memory` | Retiene 200 MB durante 60 s en un pod del gateway (`ram-spike.sh`) | Sube el working set; si pasa el límite, OOMKill y reinicio | "Memoria por pod (pharmago)"; alertas de memoria y de reinicios |
| Sobrecarga de storage | `chaos.sh storage` | Escribe 300 MB en `/tmp` del gateway y los borra a los 60 s (`volume-spike.sh`) | Pico de escritura a disco | "Escritura a disco por pod (pharmago)"; alerta *Escritura a disco anómala* |
| Interrupción de tráfico de red | `chaos.sh network` | Descarta todo el tráfico de entrada y salida de un pod de pharmacy durante 30 s (`network-chaos.sh cut`) | La readiness falla y el pod sale del Service; la otra réplica atiende. Al restaurar vuelve a `READY` | "Red recibida/enviada por pod (pharmago)" en cero; "Réplicas disponibles por deployment" |
| Desconexión de componentes internos | `chaos.sh disconnect` | Descarta el tráfico de un pod de pharmacy hacia `pharmago-db` durante 30 s, sin tocar la base (`network-chaos.sh disconnect`) | `/health/ready` falla por la base y el pod sale del Service; users y la otra réplica siguen sanos | "Errores 5xx por servicio (%)"; logs de EF Core en Kibana |

## Interrupción de red con iptables

`network-chaos.sh` usa `kubectl debug --profile=netadmin` para agregar al pod un contenedor efímero (`nicolaka/netshoot`) con la capability `NET_ADMIN`. Ese contenedor comparte el network namespace del pod, así que las reglas de `iptables` que aplica afectan al microservicio real.

- `cut` inserta `DROP` en `INPUT` y `OUTPUT`: el pod queda aislado, incluidas las probes del kubelet.
- `disconnect` inserta `DROP` en `OUTPUT` solo hacia la ClusterIP del Service y las IPs de los pods del componente destino. Es una partición de red: la base sigue arriba para todos los demás.

Las reglas se agregan y se quitan **dentro** del contenedor efímero, con un `trap` sobre la salida del `sleep`. Si se corta el script local, la red igual se restaura sola al terminar el tiempo.

Se eligió esta técnica porque funciona con cualquier CNI de minikube. Una `NetworkPolicy` necesitaría un CNI que la aplique (por ejemplo Calico).

## Registro de ejecuciones

Cada escenario agrega una línea a `chaos-engineering/chaos-runs.log` (ignorado por git):

```
escenario,inicio,fin
network,2026-11-06T14:02:10Z,2026-11-06T14:03:05Z
```

Sirve para ubicar la ventana exacta en Grafana y para etiquetar el dataset de métricas de la detección de anomalías.

## Cómo correrlo en la defensa

Requiere la app en Kubernetes y el port-forward del gateway en `127.0.0.1:5000`. Desde `Implementacion K8S/Codigo/`:

```bash
sh chaos-engineering/chaos.sh all
```

Corre los seis escenarios en orden con 60 s de pausa entre ellos, para que se vean separados en los dashboards. La pausa se cambia con `PAUSE=30 sh chaos-engineering/chaos.sh all`.

Para un escenario solo:

```bash
sh chaos-engineering/chaos.sh network
```

Los escenarios de red apuntan a pharmacy y no al gateway: el port-forward queda atado a un pod del gateway y se cortaría.

## Fallas complementarias

- [`pod-failure.sh`](../Implementacion%20K8S/Codigo/chaos-engineering/pod-failure.sh): mata el proceso o borra un pod, y baja la base entera. Ver [alta-disponibilidad.md](alta-disponibilidad.md).
- [`db-freeze.sh`](../Implementacion%20K8S/Codigo/chaos-engineering/db-freeze.sh): congela SQL Server para simular una base degradada (latencia, no desconexión).
