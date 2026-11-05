# Configuración de Prometheus para Microservicios

## Resumen

Prometheus recibe todas las métricas a través del OpenTelemetry Collector. Los servicios no exponen `/metrics`: envían sus métricas por OTLP al collector, que además scrapea node-exporter y cAdvisor y lo reexporta todo en un único endpoint.

## Arquitectura de Métricas

```
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ API Gateway │ │Users Service│ │Pharmacy Svc │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       └───────────────┼───────────────┘
                       │ OTLP gRPC :4317
                       ▼
┌─────────────────────────────────────────────┐      ┌───────────────┐
│          OTLP Collector :8889 /metrics      │◀─────│ node-exporter │
│  (receivers: otlp + prometheus)             │◀─────│ cAdvisor      │
└──────────────────────┬──────────────────────┘      └───────────────┘
                       │ scrape
                       ▼
┌─────────────────────────────────────────────┐
│               Prometheus :9090              │
└─────────────────────────────────────────────┘
```

En Compose no hay node-exporter ni cAdvisor: el collector solo reexporta las métricas OTLP de los servicios.

## Origen de las métricas

Prometheus scrapea al collector con `honor_labels: true`, así cada serie conserva el `job` de su origen:

| `job` | Origen | Métricas |
|---|---|---|
| `PharmaGo.ApiGateway` | OTLP | Solicitudes HTTP entrantes, llamadas a los servicios, métricas de negocio |
| `PharmaGo.UsersService` | OTLP | Solicitudes HTTP, login, usuarios, invitaciones, llamadas a Pharmacy |
| `PharmaGo.PharmacyService` | OTLP | Solicitudes HTTP, medicamentos, stock, compras, llamadas a Users |
| `node-exporter` | Scrape del collector (solo Kubernetes) | CPU, memoria, disco y red del nodo |
| `kubernetes-cadvisor` | Scrape del collector (solo Kubernetes) | CPU, memoria, disco y red por pod y contenedor |

## Configuración

Prometheus (`k8s/configmaps/prometheus-config.yaml` y `Backend/prometheus.yml`) tiene un único target:

```yaml
scrape_configs:
  - job_name: 'otlp-collector'
    honor_labels: true
    metrics_path: /metrics
    static_configs:
      - targets: ['otlp-collector:8889']
```

El collector (`k8s/configmaps/otel-collector-config.yaml`) recibe OTLP en `:4317`, scrapea node-exporter y cAdvisor con el receiver `prometheus` y expone todo con el exporter `prometheus` en `:8889`. Para leer cAdvisor usa la ServiceAccount `otlp-collector`, con permiso sobre `nodes` y `nodes/proxy`.

## OpenTelemetry en los servicios

La extensión `AddPharmaGoOpenTelemetry` (`Backend/Instrumentation/OpenTelemetryExtensions.cs`) configura:

- **Exporter OTLP**: envía las métricas al collector. El endpoint sale de `OTEL_EXPORTER_OTLP_ENDPOINT`.
- **ASP.NET Core Instrumentation**: métricas de HTTP requests, responses, latencia.
- **HTTP Client Instrumentation**: métricas de llamadas HTTP salientes entre servicios.
- **Custom Metrics**: métricas de negocio del meter `PharmaGo.CustomMetrics` (ej: LoginInvocations).

## Acceso a Métricas

### Prometheus UI
- **URL**: http://localhost:9090
- **Queries de ejemplo**:
  ```promql
  # Tasa de requests por servicio
  sum by (job) (rate(http_server_request_duration_seconds_count[1m]))

  # Latencia P95 del API Gateway
  histogram_quantile(0.95, sum by (le) (rate(http_server_request_duration_seconds_bucket{job="PharmaGo.ApiGateway"}[5m])))

  # Total de logins
  pharmago_login_invocations_total

  # Requests por endpoint
  http_server_request_duration_seconds_count{job="PharmaGo.UsersService"}
  ```

### Grafana
- **URL**: http://localhost:3000
- **Credenciales**: admin / admin
- **Data Source**: Prometheus (http://prometheus:9090)

### Métricas en el collector (para debugging)
- http://localhost:8889/metrics en Compose. En Kubernetes: `kubectl port-forward svc/otlp-collector 8889:8889 -n pharmago`.

## Métricas Disponibles

### Métricas Estándar de ASP.NET Core

```
# Duración de requests HTTP
http_server_request_duration_seconds_bucket
http_server_request_duration_seconds_sum
http_server_request_duration_seconds_count

# Requests activos
http_server_active_requests

# Tamaño de responses
http_server_response_body_size_bytes
```

### Métricas de HTTP Client (Comunicación entre servicios)

```
# Duración de llamadas HTTP salientes
http_client_request_duration_seconds_bucket
http_client_request_duration_seconds_sum
http_client_request_duration_seconds_count

# Requests activos salientes
http_client_active_requests
```

### Métricas Personalizadas

```
# Login invocations (Users Service)
pharmago_login_invocations_total
```

## Dashboards Recomendados para Grafana

### 1. Dashboard de Overview
- Total de requests por servicio
- Tasa de errores
- Latencia P50, P95, P99
- Requests activos

### 2. Dashboard de Users Service
- Logins por minuto
- Creación de usuarios
- Gestión de invitaciones
- Errores de autenticación

### 3. Dashboard de Pharmacy Service
- Operaciones de medicamentos
- Gestión de stock
- Compras procesadas
- Exportaciones

### 4. Dashboard de API Gateway
- Distribución de tráfico por servicio
- Latencia de proxy
- Errores de enrutamiento

### 5. Dashboard de Comunicación entre Servicios
- Llamadas Users → Pharmacy
- Llamadas Pharmacy → Users
- Latencia de comunicación inter-servicio
- Errores de comunicación

## Alertas Recomendadas

```yaml
# Alta tasa de errores
- alert: HighErrorRate
  expr: rate(http_server_request_duration_seconds_count{http_response_status_code=~"5.."}[5m]) > 0.05
  for: 5m
  annotations:
    summary: "Alta tasa de errores en {{ $labels.job }}"

# Alta latencia
- alert: HighLatency
  expr: histogram_quantile(0.95, sum by (job, le) (rate(http_server_request_duration_seconds_bucket[5m]))) > 1
  for: 5m
  annotations:
    summary: "Alta latencia en {{ $labels.job }}"

# Componente de telemetría caído
- alert: TelemetryTargetDown
  expr: up{job=~"otlp-collector|node-exporter|kubernetes-cadvisor"} == 0
  for: 1m
  annotations:
    summary: "{{ $labels.job }} no responde"
```

Los servicios envían sus métricas por OTLP y no tienen serie `up`: su caída se detecta por la falta de tráfico o por las métricas de pods de cAdvisor.

## Verificación

1. **Accede a Prometheus**: http://localhost:9090
2. **Ve a Status → Targets**: http://localhost:9090/targets
3. **Verifica que `otlp-collector` esté UP** (es el único target).
4. **Verifica que lleguen todos los orígenes**:
   ```promql
   count by (job) ({job!=""})
   ```
   Tienen que aparecer los tres servicios y, en Kubernetes, `node-exporter` y `kubernetes-cadvisor`.

## Troubleshooting

### Falta un servicio en Prometheus
1. Verifica que el servicio esté ejecutándose y tenga `OTEL_EXPORTER_OTLP_ENDPOINT` apuntando al collector.
2. Verifica que el collector reciba métricas:
   ```bash
   kubectl logs deploy/otlp-collector -n pharmago --tail=50
   ```
3. Busca la métrica en el endpoint del collector:
   ```bash
   curl -s http://localhost:8889/metrics | grep 'job="PharmaGo.UsersService"' | head
   ```

### Faltan métricas de nodo o de pods
1. Revisa los errores del receiver `prometheus` en los logs del collector.
2. Si aparece `forbidden`, verifica que existan la ServiceAccount `otlp-collector` y el ClusterRole `otlp-collector-cadvisor` con `get`, `list` y `watch` sobre `nodes` y `nodes/proxy`.

### No se ven métricas personalizadas
1. Verifica que el código esté llamando a `_customMetrics.LoginInvocations()`
2. Verifica que el servicio tenga configurado `AddMeter("PharmaGo.CustomMetrics")`
3. Reinicia el servicio después de cambios

### Prometheus no hace scraping
1. Verifica la configuración en `prometheus.yml`
2. Reinicia Prometheus:
   ```bash
   docker-compose restart prometheus
   ```
3. Verifica los logs de Prometheus:
   ```bash
   docker logs prometheus
   ```
