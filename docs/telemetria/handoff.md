# Handoff: telemetría

Estado al 2026-10-23. El plan completo está en [plan.md](plan.md); las reglas de trabajo, en `AGENTS.md`.

## Dónde quedó

- Rama actual: `feature/otlp-tracing`, creada desde `chore/unify-otel-setup` mientras la PR #5 sigue abierta.
- Paso 1 del plan: **implementado y publicado** en la PR draft [#5](https://github.com/santiremedi/AIOps/pull/5).
- Paso 2 del plan: **implementado y publicado** en la PR draft [#6](https://github.com/santiremedi/AIOps/pull/6), dependiente de la PR #5.
- Pasos 3 a 6: sin empezar.

## Qué se hizo en el paso 1

Rutas relativas a `Implementacion K8S/Codigo/`.

- Nueva `Backend/Instrumentation/OpenTelemetryExtensions.cs` con `AddPharmaGoOpenTelemetry(serviceName)`: métricas AspNetCore + HttpClient + meter `PharmaGo.CustomMetrics`, exporter Prometheus y exporter OTLP. El exporter OTLP no recibe endpoint en código: lo lee de `OTEL_EXPORTER_OTLP_ENDPOINT` (gRPC por defecto).
- `CustomMetrics` usa la constante `OpenTelemetryExtensions.CustomMetricsMeterName`.
- Borradas las tres copias de `TelemetryExtensions.cs` (`PharmaGo.Factory`, `PharmaGo.UsersService.Factory`, `PharmaGo.PharmacyService.Factory`).
- `Program.cs` de gateway, Users, Pharmacy y WebApi llaman a `AddPharmaGoOpenTelemetry("<servicio>")`. El gateway antes no exportaba por OTLP; ahora sí.
- Paquetes OTel centralizados en `Instrumentation.csproj` (1.8.1; Prometheus exporter 1.8.0-rc.1) y eliminados del resto de los `.csproj`.
- Para evitar el error NU1605 (downgrade), porque OTel 1.8 trae `Microsoft.Extensions.*` 8.0:
  - `Instrumentation.csproj`: quitado `Microsoft.Extensions.Logging.Abstractions` (lo provee el `FrameworkReference` de ASP.NET Core).
  - `PharmaGo.DataAccess.csproj`: `Logging.Abstractions` 6.0.0 → 8.0.0.
  - Factories de Users y Pharmacy: `Configuration`, `DependencyInjection` y `Hosting.Abstractions` 6.0.0 → 8.0.0.
- `OTEL_EXPORTER_OTLP_ENDPOINT=http://otlp-collector:4317` agregado a los tres deployments de `k8s/deployments/backend/` y a los tres servicios del `docker-compose.yml`. El gateway en compose ahora depende de `otlp-collector`.

## Verificación hecha

- `dotnet build Backend/PharmaGo.sln`: OK, 0 errores.
- `dotnet test`: 290 pasan, 1 falla. Es el mismo resultado que en `main` antes del cambio: falla `PurchasesDetailRepositoryTest.Test_GetOneByExpression` (acceso a datos, ajeno a telemetría). No se tocó.
- Manifiestos: no se pudo correr `kubectl apply --dry-run=client` porque no hay un cluster accesible. Se validó con un parser YAML que los tres deployments editados parsean y tienen la variable. `docker compose config -q` OK.
- Smoke test con Compose: Prometheus recibe 108 series del gateway a través del job `otlp-collector`, identificadas con `exported_job="PharmaGo.ApiGateway"`.

## Pendiente del paso 1

- Ejecutar `kubectl apply --dry-run=client -R -f k8s/` cuando haya un cluster accesible.

## Qué se hizo en el paso 2

- La extensión compartida configura trazas AspNetCore, HttpClient y SqlClient, y las exporta por OTLP.
- `OpenTelemetry.Instrumentation.SqlClient` quedó fijado en `1.8.0-beta.1`, que apunta a `net6.0` y es compatible con OpenTelemetry 1.8.x.
- El collector recibe trazas por OTLP y las reenvía con el exporter `otlp_grpc` a Jaeger, tanto en Kubernetes como en Compose.
- Jaeger all-in-one `2.14.1` usa almacenamiento transitorio en memoria y recursos acotados en Kubernetes.
- Grafana provisiona Jaeger como datasource. Los scripts de despliegue y port-forward incluyen el nuevo servicio.
- Se mantiene `X-Correlation-ID` por compatibilidad; W3C `traceparent` se propaga en paralelo mediante la instrumentación de HttpClient. La correlación de logs con `trace_id` queda para el paso 3.

## Verificación del paso 2

- `dotnet build Backend/PharmaGo.sln`: OK, 0 errores; sin NU1605. Permanece NU1902 ya documentada.
- `dotnet test Backend/PharmaGo.sln --no-build`: 290 pasan, 1 falla. Es el mismo baseline de `PurchasesDetailRepositoryTest.Test_GetOneByExpression`.
- `docker compose config -q`: OK.
- Parser YAML: 46 archivos válidos, incluidos los manifiestos y las configuraciones embebidas.
- `bash -n k8s/apply-k8s.sh` y `bash -n k8s/port-forward.sh`: OK con Git Bash. Parser de PowerShell sobre `apply-k8s.ps1`: OK.
- Smoke test con Compose: `GET /api/roles` devolvió 200 y produjo la traza `d23042e3fbf26d65cf6fdcf8a2819356`, con 4 spans y el recorrido `PharmaGo.ApiGateway` → `PharmaGo.UsersService` → `SqlClient` (`PharmaDb`).
- Jaeger expone los tres servicios en `/api/services`. El datasource provisionado en Grafana respondió `Data source is working`.
- Durante el smoke se reemplazó Jaeger v1, fuera de soporte, por Jaeger `2.14.1`. Se mantuvo esa versión porque Jaeger `2.15.0` eliminó la API query v1 que consume el datasource de Grafana.
- Los logs del collector confirmaron la recepción de métricas y trazas sin errores de exportación. El alias deprecado `otlp/jaeger` se reemplazó por `otlp_grpc/jaeger`.
- `kubectl apply --dry-run=client -R -f k8s/` sigue pendiente porque no hay cluster accesible.

## Decisiones tomadas

- **Línea OpenTelemetry 1.8.x.** Ya estaba en uso en el proyecto y apunta explícitamente a `net6.0`. Las versiones posteriores van dejando net6.0; antes de subir, verificar los target frameworks de cada paquete en NuGet.
- **Advertencia NU1902 aceptada.** `OpenTelemetry.Exporter.OpenTelemetryProtocol` 1.8.1 está afectado por GHSA-4625-4j76-fww9. Solo es explotable con el disk retry experimental (`OTEL_DOTNET_EXPERIMENTAL_OTLP_RETRY=disk`), que no usamos. La versión corregida (1.15.3) no soporta net6.0. No activar esa variable.
- **WebApi incluido.** Es el monolito original y no se despliega, pero los tests lo referencian; se migró a la extensión compartida para no dejar código duplicado.
- **El exporter Prometheus sigue activo.** Se quita en el paso 4, cuando todo pase por el collector.
- **Jaeger 2.14.1 por compatibilidad con Grafana.** Es la última versión v2 anterior a la eliminación de la API query v1 en Jaeger 2.15. El datasource actual de Grafana usa esa API.

## Uso de inteligencia artificial

- Herramienta: Codex de OpenAI.
- Contexto de uso: análisis del punto de telemetría, planificación, revisión e implementación asistida de la configuración de OpenTelemetry.
- Revisión: los cambios generados se inspeccionan y verifican antes de commitearlos.

## Trampas del entorno (Windows)

- `git pull` / `push` fallan con "unable to get local issuer certificate". Usar `git -c http.sslBackend=schannel pull`.
- Solo está el SDK de .NET 8, sin runtime 6. Los tests corren con `DOTNET_ROLL_FORWARD=Major dotnet test Backend/PharmaGo.sln`.
- `kubectl` no tiene cluster configurado (apunta a `localhost:8080`): el dry-run falla incluso con `--validate=false`.
- Los puertos 5001 y 3000 estaban ocupados por contenedores ajenos (`phonetec-backend` y `phonetec-frontend`). Para el smoke, Users y Grafana se ejecutaron sin publicar esos puertos; no se detuvieron los contenedores ajenos.
- La ruta `Implementacion K8S/Codigo` tiene espacios: siempre entre comillas.

## Siguiente paso: 3, correlación de logs (`feature/trace-log-correlation`)

- Crear la rama desde el paso 2 una vez mergeada su PR, o apilarla dejando explícita la dependencia.
- Incluir `trace_id` y `span_id` en los logs JSON mediante `ActivityTrackingOptions`.
- Configurar el formatter JSON de consola en el gateway.
- Verificar en Kibana que ambos campos lleguen como campos consultables.
