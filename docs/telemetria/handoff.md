# Handoff: telemetría

Estado al 2026-10-22. El plan completo está en [plan.md](plan.md); las reglas de trabajo, en `AGENTS.md`.

## Dónde quedó

- Rama: `chore/unify-otel-setup` (creada desde `main` en `0cc754f`).
- Paso 1 del plan: **implementado, sin commitear**. Falta commitear, pushear y abrir la PR en draft.
- Pasos 2 a 6: sin empezar.

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
- No se probó en ejecución (ni compose ni cluster): falta confirmar que las métricas del gateway llegan al collector.

## Para cerrar el paso 1

1. Commits sugeridos, en español, imperativo y sin atribución de IA:
   - `Centraliza la configuración de OpenTelemetry en Instrumentation`
   - `Alinea versiones de paquetes OpenTelemetry y Microsoft.Extensions`
   - `Configura el endpoint OTLP por variable de entorno`
   - `Agrega plan y handoff de telemetría` (estos dos documentos)
2. Push y PR en draft contra `main`. En la descripción de la PR mencionar:
   - El test que ya fallaba en `main`.
   - Que el dry-run de `kubectl` queda pendiente de un cluster.
   - La advertencia NU1902 (ver abajo).
3. Si hay cluster o Docker disponible: levantar el stack y confirmar en Prometheus métricas con `service_name="PharmaGo.ApiGateway"` que entren por el job `otlp-collector`.

## Decisiones tomadas

- **Línea OpenTelemetry 1.8.x.** Ya estaba en uso en el proyecto y apunta explícitamente a `net6.0`. Las versiones posteriores van dejando net6.0; antes de subir, verificar los target frameworks de cada paquete en NuGet.
- **Advertencia NU1902 aceptada.** `OpenTelemetry.Exporter.OpenTelemetryProtocol` 1.8.1 está afectado por GHSA-4625-4j76-fww9. Solo es explotable con el disk retry experimental (`OTEL_DOTNET_EXPERIMENTAL_OTLP_RETRY=disk`), que no usamos. La versión corregida (1.15.3) no soporta net6.0. No activar esa variable.
- **WebApi incluido.** Es el monolito original y no se despliega, pero los tests lo referencian; se migró a la extensión compartida para no dejar código duplicado.
- **El exporter Prometheus sigue activo.** Se quita en el paso 4, cuando todo pase por el collector.

## Uso de inteligencia artificial

- Herramienta: Codex de OpenAI.
- Contexto de uso: análisis del punto de telemetría, planificación, revisión e implementación asistida de la configuración de OpenTelemetry.
- Revisión: los cambios generados se inspeccionan y verifican antes de commitearlos.

## Trampas del entorno (Windows)

- `git pull` / `push` fallan con "unable to get local issuer certificate". Usar `git -c http.sslBackend=schannel pull`.
- Solo está el SDK de .NET 8, sin runtime 6. Los tests corren con `DOTNET_ROLL_FORWARD=Major dotnet test Backend/PharmaGo.sln`.
- `kubectl` no tiene cluster configurado (apunta a `localhost:8080`): el dry-run falla incluso con `--validate=false`.
- La ruta `Implementacion K8S/Codigo` tiene espacios: siempre entre comillas.

## Siguiente paso: 2, trazas (`feature/otlp-tracing`)

Rama nueva desde `main` actualizado, después de mergear la PR del paso 1 (o desde `chore/unify-otel-setup` si todavía no se mergeó, avisando en la PR).

- En `OpenTelemetryExtensions.AddPharmaGoOpenTelemetry`, agregar `.WithTracing(...)` con `AddAspNetCoreInstrumentation`, `AddHttpClientInstrumentation`, instrumentación de SqlClient o EF Core y `AddOtlpExporter()`. Agregar los paquetes a `Instrumentation.csproj` en versiones compatibles con 1.8.x y net6.0. Las instrumentaciones de SqlClient y EF Core son beta: elegir la más reciente que restaure sin NU1605.
- Collector: pipeline `traces` con receiver `otlp` y exporter hacia el backend elegido, en `k8s/configmaps/otel-collector-config.yaml` y `Backend/otel-collector-config.yaml`.
- Backend de trazas: Jaeger all-in-one (Deployment + Service en `k8s/deployments/ops` y `k8s/services/ops`, y servicio en compose), con datasource en Grafana (`k8s/configmaps/grafana-provisioning.yaml` y `grafana/provisioning/datasources/`).
- Verificar que una request al gateway genera una traza con spans gateway → servicio → BD.
- Ojo con los recursos: los deployments tienen límites bajos ("nodos ~5GB").
