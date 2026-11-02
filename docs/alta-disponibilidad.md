# Alta disponibilidad

Cómo cumple PharmaGo el ítem "Alta disponibilidad" de la rúbrica:

1. **Self-healing:** cuando una réplica que ya llegó a `READY` sufre una excepción, vuelve sola a `READY`.
2. **Resiliencia ante fallas reiteradas:** un patrón que mitiga un volumen alto de requests fallidas.

Se apoya en las tácticas de disponibilidad de Bass:

- **Detectar:** health checks y probes.
- **Recuperarse:** reinicio del contenedor, ReplicaSet y reintentos con backoff.
- **Aislar:** circuit breaker.
- **Prevenir:** el rate limiting por IP que ya existía.

Todas apuntan a bajar el MTTRestore (`Availability = MTBF / (MTBF + MTTRestore)`).

## Self-healing en Kubernetes

### Health checks: liveness separada de readiness

El gateway, users-service y pharmacy-service exponen tres endpoints, definidos en [`HealthCheckExtensions.cs`](../Implementacion%20K8S/Codigo/Backend/Instrumentation/HealthCheckExtensions.cs).

| Endpoint | Qué chequea | Lo usa |
|---|---|---|
| `/health/live` | Solo que el proceso responda | `startupProbe` y `livenessProbe` |
| `/health/ready` | En users y pharmacy, además, la conexión a la base (`AddDbContextCheck`) | `readinessProbe` |
| `/health` | Alias de `/health/ready` | Compatibilidad (`/test-health` del gateway, whitelist del rate limit) |

La liveness **no** mira la base de datos. Si la mirara, con la base caída Kubernetes reiniciaría todas las réplicas en loop sin ganar nada. Una base caída es un caso de readiness: el pod sigue vivo pero sale del Service.

El gateway tampoco depende de los backends para estar ready. Si dependiera, la caída de un backend cortaría también las rutas que siguen sanas.

### Probes y réplicas

Están en los manifiestos de [`k8s/deployments/backend/`](../Implementacion%20K8S/Codigo/k8s/deployments/backend).

| Pieza | Configuración | Efecto |
|---|---|---|
| `replicas: 2` | ReplicaSet del Deployment | Si un pod falla, el otro sigue atendiendo, y el ReplicaSet vuelve a crear los que falten (`desired = actual`). |
| `startupProbe` | `/health/live`, cada 10 s, 15 intentos | Evita que la liveness reinicie el pod mientras arranca, incluida la migración de la base. |
| `livenessProbe` | `/health/live`, cada 10 s, timeout 3 s, 3 fallas | Si el proceso se cuelga, el kubelet reinicia el contenedor en unos 30 s. |
| `readinessProbe` | `/health/ready`, cada 5 s, timeout 3 s, 2 fallas | Si se pierde la base, el pod sale del Service sin reiniciarse y vuelve solo. |
| `restartPolicy: Always` | Default del pod | Si el proceso termina por una excepción no controlada, el contenedor se reinicia. |

La estrategia de rollout (`maxUnavailable: 0`, `maxSurge: 1`, `preStop`) está en [despliegues-seguros.md](despliegues-seguros.md).

### Reintentos ante fallas transitorias de la base

Los `ServiceFactory` de users y pharmacy usan `EnableRetryOnFailure`: 5 reintentos, con un delay máximo de 10 s. Es backoff exponencial con jitter de EF Core, y se aplica solo a errores transitorios de SQL Server.

También cubre la migración de arranque de users-service, que antes dejaba el pod en `CrashLoopBackOff` si la base tardaba en levantar.

## Circuit breaker en el API Gateway

### Dónde y por qué

Va en el borde del sistema, en el cliente HTTP con el que YARP llega a cada cluster. Así corta el exceso de fallas antes de que llegue a los servicios y a la base compartida.

Hay un circuito independiente por cluster (`users-cluster` y `pharmacy-cluster`). Si un ataque hace fallar pharmacy, users sigue funcionando.

El estado del circuito vive en memoria de cada réplica del gateway. Con 2 réplicas, cada una evalúa sus propias fallas y puede abrir el circuito en momentos distintos. Por eso, en la demo con `kubectl port-forward` (que queda atado a un solo pod) las transiciones aparecen en los logs de un solo pod.

El código está en [`PharmaGo.ApiGateway/Resilience/`](../Implementacion%20K8S/Codigo/Backend/PharmaGo.ApiGateway/Resilience), con Polly (`AdvancedCircuitBreaker` + `Timeout`).

### Estados

```
Closed --(>= 50% de fallas en 30 s, mínimo 10 requests)--> Open
Open   --(30 s)--> Half-Open --(request de prueba OK)--> Closed
                             --(falla)-----------------> Open
```

Qué cuenta como falla:

- Respuestas 5xx.
- Errores de conexión.
- Requests que tardan más de 10 s. En ese caso el gateway responde 504.

**Los 4xx no cuentan.** Son errores del cliente: si contaran, un atacante podría mandar requests inválidos para abrir el circuito y dejar sin servicio a todos los demás.

Con el circuito abierto, el gateway responde **503 al instante**, sin llegar al backend, con dos headers:

- `Retry-After: 30`
- `X-Circuit-Breaker: open`

En el gateway **no hay reintentos**. Ante un ataque o una dependencia degradada multiplicarían la carga (retry storm).

### Parámetros

Están en la sección `CircuitBreaker` de `appsettings.json` del gateway. Se pueden sobreescribir por variable de entorno, por ejemplo `CircuitBreaker__DurationOfBreak=00:00:10`.

| Clave | Default | Qué controla |
|---|---|---|
| `FailureRatio` | 0.5 | Proporción de fallas que abre el circuito |
| `SamplingDuration` | 00:00:30 | Ventana de medición |
| `MinimumThroughput` | 10 | Requests mínimos en la ventana antes de evaluar |
| `DurationOfBreak` | 00:00:30 | Tiempo abierto antes de pasar a Half-Open |
| `RequestTimeout` | 00:00:10 | Timeout por request al backend |

### Observabilidad

- **Métrica:** `pharmago_circuit_breaker_transitions_total_1{cluster, state}`, con `state` en `open`, `half_open` o `closed`. El exporter agrega el sufijo `_1` por la unidad, igual que en `pharmago_http_requests_total_1`. Ejemplo: `increase(pharmago_circuit_breaker_transitions_total_1{state="open"}[5m])`.
- **Logs del gateway:** `Circuit breaker opened for cluster ...`, seguido de las transiciones a `half_open` y `closed`.

### Defensa en profundidad

El rate limit por IP frena el volumen por origen. El circuit breaker protege a los backends cuando las fallas se acumulan igual, por ejemplo con muchos orígenes o con una dependencia caída.

## Cómo demostrarlo

Requiere la app en Kubernetes y el port-forward del gateway en `127.0.0.1:5000`. El script es [`chaos-engineering/pod-failure.sh`](../Implementacion%20K8S/Codigo/chaos-engineering/pod-failure.sh).

Primero, matar el proceso de un pod. El contenedor se reinicia y `RESTARTS` sube en 1:

```bash
sh chaos-engineering/pod-failure.sh kill pharmago-pharmacy-service
```

Después, borrar un pod entero. El ReplicaSet crea uno nuevo:

```bash
sh chaos-engineering/pod-failure.sh delete pharmago-users-service
```

Por último, bajar la base, enviar 30 requests y restaurarla:

```bash
sh chaos-engineering/pod-failure.sh db-down 30
```

No hay que usar `kill` ni `delete` sobre el gateway mientras el port-forward está abierto: el port-forward queda atado a un pod y se corta.

Para ver las transiciones del circuito en los logs:

```bash
for p in $(kubectl get pod -n pharmago -l app=pharmago-api-gateway -o name); do kubectl logs -n pharmago $p | grep -i "circuit breaker"; done
```

### Resultados en minikube

| Prueba | Resultado |
|---|---|
| `kill` sobre pharmacy, con 120 requests en paralelo | El contenedor se reinicia (`RESTARTS` +1) y vuelve a `READY` en unos 40 s. Los 120 requests responden `200`. |
| `delete` sobre users | El ReplicaSet crea un pod nuevo, que llega a `READY` en unos 35 s, sin cortes. |
| `db-down` 30 | Los 4 pods de users y pharmacy quedan `0/1` sin reiniciarse. Las respuestas son `10 502` y `20 503 open`. Al restaurar la base, todo vuelve a `READY` en unos 65 s. |
| Logs del gateway | `opened` → `half_open` → `closed`, y la misma secuencia en la métrica de Prometheus. |

Las primeras fallas pueden llegar como 500 o como 502, aunque los pods ya estén NotReady. La readiness solo saca el pod del balanceo de conexiones nuevas, y YARP reutiliza las conexiones keep-alive que ya tenía abiertas. El circuit breaker cubre ese hueco.
