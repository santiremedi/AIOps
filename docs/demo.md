# Guía de la demo

Cómo levantar PharmaGo y mostrar cada falla de la rúbrica con su telemetría y la respuesta del sistema, de la forma más simple posible. Los comandos se corren desde `Implementacion K8S/Codigo`, en Git Bash.

## 1. Levantar todo

```bash
minikube start --memory=6144 --cpus=4
sh k8s/build-images.sh
sh k8s/apply-k8s.sh
minikube image pull nicolaka/netshoot:v0.13
kubectl get pods -n pharmago
sh k8s/port-forward.sh
```

Esperar a que todos los pods estén `Running` y `READY` antes de seguir. La imagen `netshoot` se baja antes para que el corte de red no dependa de internet durante la demo.

Dejar abiertos, uno por pestaña:

| Herramienta | URL | Qué mirar |
|---|---|---|
| Grafana | http://127.0.0.1:3000 (admin/admin) | Dashboards **PharmaGo - Infra** y **PharmaGo - Servicios**, y Alerting → Alert rules (carpeta PharmaGo) |
| Kibana | http://127.0.0.1:5601 | Logs del índice `pharmago-logs-*` |
| Jaeger | http://127.0.0.1:16686 | Trazas de cada servicio |

Y una terminal con `kubectl get pods -n pharmago -w` para ver reinicios y réplicas en vivo.

## 2. Una falla por escenario

Cada escenario se corre por separado con `sh chaos-engineering/chaos.sh <escenario>`, o todos seguidos con `all`. Qué hace cada uno y en qué panel se ve está en [scripts-de-caos.md](scripts-de-caos.md). Las alertas tardan entre 30 segundos y 1 minuto en pasar a `firing`.

| Falla de la rúbrica | Comando | Qué mostrar |
|---|---|---|
| Inyección de requests | `sh chaos-engineering/chaos.sh requests` | Respuestas 429 del rate limit en "Rate Limit Errors (429) por Endpoint" |
| Sobrecarga de CPU | `sh chaos-engineering/chaos.sh cpu` | "CPU por pod" y la alerta **CPU de un pod de la app cerca del límite** |
| Sobrecarga de memoria | `sh chaos-engineering/chaos.sh memory` | "Memoria por pod" del gateway |
| Sobrecarga de storage | `sh chaos-engineering/chaos.sh storage` | "Escritura a disco por pod" y la alerta **Escritura a disco anómala** |
| Interrupción de tráfico de red | `sh chaos-engineering/chaos.sh network` | Un pod de pharmacy pasa a `0/1`, sale del Service y vuelve a `READY` sin reiniciarse |
| Desconexión de componentes internos | `sh chaos-engineering/chaos.sh disconnect` | Un pod de pharmacy pierde la base y queda `0/1` mientras users sigue sano |

Para mostrar también la alta disponibilidad:

| Falla | Comando | Qué mostrar |
|---|---|---|
| Caída de un pod | `sh chaos-engineering/pod-failure.sh delete` | El ReplicaSet crea otro pod de pharmacy y la otra réplica sigue atendiendo |
| Caída de la base | `sh chaos-engineering/pod-failure.sh db-down 30` | Respuestas `503` con `X-Circuit-Breaker: open` y las alertas **Deployment sin réplicas disponibles** y **Errores 5xx por servicio** |
| Base degradada | `sh chaos-engineering/db-freeze.sh 60` | Latencia p95 y errores 5xx en **PharmaGo - Servicios** |

No correr `kill` ni `delete` sobre el gateway con el port-forward abierto, porque el port-forward queda atado a un pod y se corta.

## 3. Despliegue sin cortes

En una terminal, 300 requests al gateway desde adentro del cluster:

```bash
kubectl run trafico -n pharmago --rm -i --restart=Never --image=curlimages/curl --command -- sh -c 'for i in $(seq 1 300); do curl -s -o /dev/null -w "%{http_code}\n" --max-time 2 http://pharmago-api-gateway/api/roles/ping; sleep 0.5; done | sort | uniq -c'
```

Mientras corre, en otra:

```bash
kubectl rollout restart deployment/pharmago-users-service deployment/pharmago-api-gateway -n pharmago
```

Resultado esperado: `300 200`. El detalle está en [despliegues-seguros.md](despliegues-seguros.md).

## 4. Si algo queda roto

Seguir el plan de contención de incidentes: identificar el componente en Grafana y con `kubectl get pods -n pharmago`, y aplicar la mitigación que corresponda.

```bash
kubectl rollout restart deployment/<deploy> -n pharmago
kubectl rollout undo deployment/<deploy> -n pharmago
kubectl scale deployment/<deploy> --replicas=1 -n pharmago
```

El primero reinicia sin cortes, el segundo vuelve a la versión anterior y el tercero levanta un componente que quedó en 0 réplicas.

## 5. Apagar

```bash
sh k8s/port-forward.sh --stop
minikube stop
```
