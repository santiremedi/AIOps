# Plan de telemetría

Punto "Telemetría" de la rúbrica (5 puntos) de `Obligatorio AIOps.pdf`. Es la base de los puntos de detección de anomalías (las 5 alertas de Grafana se arman sobre estas métricas) y de la defensa (hay que mostrar con telemetría el efecto del script de caos).

## Qué pide la letra

1. Logs estructurados en JSON, consultables en una herramienta de logs (Kibana + Elasticsearch).
2. Trazas según OTLP, con propagación de contexto entre servicios.
3. Métricas a nivel de pod/contenedor y de nodo físico: CPU, memoria, storage y red.
4. Métricas recolectadas con OTLP hacia Prometheus y visualizadas en Grafana.

## Punto de partida (proyecto base)

| Requisito | Estado inicial |
|---|---|
| Logs JSON | Casi listo en Users y Pharmacy: formatter `json` de consola con scopes y `correlation_id`. El gateway no tiene formatter JSON. |
| Logs → Kibana | Fluent Bit (DaemonSet) → Elasticsearch → Kibana, ya configurado en `k8s/`. |
| Trazas | No existen: solo `WithMetrics`, sin pipeline `traces` en el collector ni backend de trazas. |
| Propagación de contexto | Manual, con el header `X-Correlation-ID`; no usa W3C `traceparent`. |
| Métricas de app por OTLP | Users y Pharmacy exportan por OTLP y además exponen `/metrics`. El gateway solo expone `/metrics`. |
| Métricas de nodo/pod | node-exporter y cAdvisor existen, pero Prometheus los scrapea directo (no pasan por OTLP). |
| Dashboards | CPU, memoria y disco. Falta red y storage por pod. |

## Pasos

Cada paso es una rama desde `main` y una PR en draft (GitHub Flow, ver `AGENTS.md`).

### 1. `chore/unify-otel-setup`: unificar la configuración de OpenTelemetry

- Una sola extensión `AddPharmaGoOpenTelemetry(serviceName)` en `Backend/Instrumentation`, usada por gateway, Users, Pharmacy y WebApi.
- Eliminar las copias de `TelemetryExtensions.cs` de las factories.
- Alinear los paquetes OpenTelemetry en la línea 1.8.x.
- Endpoint OTLP tomado de `OTEL_EXPORTER_OTLP_ENDPOINT` (env en deployments y compose), no hardcodeado.
- Resultado: el gateway pasa a exportar métricas por OTLP.

### 2. `feature/otlp-tracing`: trazas distribuidas

- Agregar `WithTracing` a la extensión compartida: instrumentación AspNetCore, HttpClient y SqlClient/EF Core; exporter OTLP.
- La propagación W3C `traceparent` entre gateway (YARP) y servicios sale de la instrumentación de HttpClient; verificar que el gateway la propaga.
- Collector: agregar pipeline `traces` (k8s `configmaps/otel-collector-config.yaml` y `Backend/otel-collector-config.yaml` del compose).
- Backend de trazas: Jaeger (recomendado por simplicidad), con datasource en Grafana. Alternativa: Grafana Tempo.
- Decidir si `X-Correlation-ID` se mantiene o se reemplaza por `trace_id`.

### 3. `feature/trace-log-correlation`: correlación logs ↔ trazas

- `TraceId` y `SpanId` ya llegan a cada log JSON como scope: el host de .NET habilita `ActivityTrackingOptions` por defecto y el formatter JSON usa `IncludeScopes`. No hace falta código.
- Configurar el formatter JSON de consola en el gateway (`PharmaGo.ApiGateway/appsettings.json`).
- Documentar la búsqueda por `Scopes.TraceId` en Kibana (`tutoriales/como-revisar-logs-kibana.md`).
- Verificar en Kibana, con Fluent Bit en el cluster, que `Scopes.TraceId` es consultable. Requiere que Fluent Bit parsee el formato CRI de containerd (`multiline.parser docker, cri`).

### 4. `feature/otlp-infra-metrics`: métricas de infraestructura por OTLP

- Que el collector sea el único camino hacia Prometheus.
- Opción elegida (a): el collector scrapea node-exporter y cAdvisor con el receiver `prometheus` y los reexporta. Mantiene las queries actuales.
- Opción (b), descartada por ahora: receivers `hostmetrics` y `kubeletstats`, eliminando node-exporter y cAdvisor.
- Quitar los scrapes directos de Prometheus a los servicios y el exporter Prometheus de la app (`AddPrometheusExporter` y `MapPrometheusScrapingEndpoint`).
- Consulta pendiente con el docente: si las métricas de nodo/pod también deben pasar por OTLP. La opción (a) cubre ambos casos.

### 5. `feature/grafana-dashboards`: dashboards

- Infra: red rx/tx por pod y por nodo, storage por pod, reinicios de pods.
- App: señales doradas por servicio (rate, errores, latencia p95).
- Dejar identificadas las métricas sobre las que irán las 5 alertas del paso 7.
- Un solo origen por dashboard en `grafana/provisioning/dashboards/`: Compose lo monta como carpeta y los scripts de `k8s/` generan el ConfigMap `grafana-dashboards` desde ahí.
- Reinicios y réplicas salen de kube-state-metrics, scrapeado por el collector. En containerd, cAdvisor no publica `container_fs_usage_bytes`: el storage por pod se mide como escritura (`container_fs_writes_bytes_total`) junto con el disco disponible del nodo.

Métricas candidatas para las alertas del paso 7:

| Escenario | Script de caos | Métrica | Dashboard |
|---|---|---|---|
| Errores del servicio | — | `http_server_request_duration_seconds_count{http_response_status_code=~"5.."}` sobre el total, por `job` | Servicios |
| Sobrecarga / rate limit | `load-requests.sh` | latencia p95 de `http_server_request_duration_seconds_bucket` y tasa de 429 | Servicios, Overview |
| CPU | `cpu-spike.sh` | `rate(container_cpu_usage_seconds_total{namespace="pharmago"}[1m])` por pod | Infra |
| Memoria | `ram-spike.sh` | `container_memory_working_set_bytes{namespace="pharmago"}` por pod; si hay OOMKill, `kube_pod_container_status_restarts_total` | Infra |
| Storage | `volume-spike.sh` | `rate(container_fs_writes_bytes_total[1m])` por pod y `node_filesystem_avail_bytes` | Infra |
| Servicio caído | borrar o escalar a 0 un deployment | `kube_deployment_status_replicas_available == 0` | Infra |

### 6. `docs/telemetry`: documentación

- Diagrama del flujo: app → collector → Prometheus/Jaeger → Grafana; stdout → Fluent Bit → Elasticsearch → Kibana.
- Cómo consultar cada señal. Insumo directo para la sección del informe.

### 7. `feature/grafana-alerts`: alertas de anomalías

Corresponde al ítem "Técnicas de detección de anomalías" de la rúbrica, no a Telemetría, pero se apoya directamente en estas métricas.

- Al menos 5 alertas en Grafana sobre las métricas ya definidas, provisionadas como código (compose y `k8s/configmaps`).
- Cubrir los escenarios del script de caos: tasa de errores 5xx, latencia p95, CPU y memoria por pod, storage disponible, reinicios de pods o caída de tráfico de red.
- Hacerlo después del paso 4: hasta entonces Prometheus recibe las métricas de app dos veces (scrape directo y collector) y las agregaciones con `sum` cuentan doble.
- Verificar que cada alerta se dispara con el script de caos correspondiente.
- Desde el paso 4 los servicios no tienen serie `up` (envían por OTLP, nadie los scrapea). La caída de un servicio se detecta con `kube_deployment_status_replicas_available` (paso 5) o por caída de tráfico. El exporter `prometheus` del collector sigue publicando las series de un servicio caído durante `metric_expiration` (5 minutos por defecto): evaluar bajarlo si demora las alertas.

## Verificación de cada paso

- `dotnet build Backend/PharmaGo.sln` y `dotnet test Backend/PharmaGo.sln`.
- `kubectl apply --dry-run=client -R -f k8s/` (requiere un cluster accesible).
- En el cluster: ver la métrica, la traza o el log aparecer en Grafana, Jaeger o Kibana.
