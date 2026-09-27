# AGENTS.md

Obligatorio de AIOps (Universidad ORT). Partimos de PharmaGo, un sistema de gestión de farmacias en microservicios, y le agregamos disponibilidad, despliegues seguros, telemetría, detección de anomalías, plan de contención de incidentes y scripts de caos. La letra y la rúbrica están en `Obligatorio AIOps.pdf`.

## Estructura

Todo el código vive en `Implementacion K8S/Codigo/` (la ruta tiene espacios: siempre entre comillas).

- `Backend/` — .NET 6. Solución `PharmaGo.sln`: `PharmaGo.ApiGateway`, `PharmaGo.UsersService`, `PharmaGo.PharmacyService`, capas de dominio/negocio/datos, `Instrumentation` (OpenTelemetry, logs y métricas). Tests en `PharnaGo.Test/` (MSTest + Moq).
- `Frontend/` — Angular 14, servido con nginx.
- `k8s/` — manifiestos y scripts (`build-images`, `apply-k8s`, `port-forward`, `cleanup`), en `.sh` y `.ps1`.
- `chaos-engineering/` — scripts de caos (requests, CPU, RAM, storage).
- `grafana/`, `docker-compose.yml` — observabilidad y stack local.

## Comandos

Desde `Implementacion K8S/Codigo/`:

- Backend: `dotnet build Backend/PharmaGo.sln` y `dotnet test Backend/PharmaGo.sln`. Durante el loop, filtrar: `dotnet test Backend/PharmaGo.sln --filter "FullyQualifiedName~<Clase>"`.
- Frontend: `npm ci` y `npm run build` dentro de `Frontend/`. Karma está configurado pero no hay specs: la UI se verifica en el browser.
- Stack local: `docker-compose up --build` (gateway en `localhost:5000`, frontend en `localhost:4200`, Grafana en `localhost:3000`).
- Kubernetes: `k8s/build-images.sh` y luego `k8s/apply-k8s.sh` (o los `.ps1` en Windows).

## Verificación completa

Es el check que corre antes de cada PR y al final de cada implementación. Incluye solo lo que aplica a lo que se tocó:

- Backend: `dotnet build Backend/PharmaGo.sln` y `dotnet test Backend/PharmaGo.sln`.
- Frontend: `npm run build` en `Frontend/`.
- Manifiestos de `k8s/`: `kubectl apply --dry-run=client -R -f k8s/`.
- Scripts `.sh`: `bash -n <script>`.

No se abre una PR con la verificación en rojo.

## Flujo de trabajo: GitHub Flow

- `main` siempre desplegable. No se commitea directo a `main`.
- Cada cambio sale de una rama creada desde `main` actualizada, con prefijo `feature/`, `fix/`, `chore/` o `docs/` y nombre corto en inglés con guiones: `feature/circuit-breaker`.
- Commits chicos, uno por paso lógico, en español, imperativo, una línea: `Agrega readiness probe al gateway`.
- Ni commits ni PRs llevan atribución a agentes de IA: sin `Co-Authored-By` ni firmas tipo "Generated with".
- Se integra solo por pull request contra `main`, con revisión y CI en verde. La PR se abre en draft; sacarla de draft y mergearla lo decide un humano.
- Después del merge se borra la rama.

## Clean code

- Nombres que revelen intención; si hace falta un comentario para explicar un nombre, el nombre está mal.
- Funciones cortas que hacen una sola cosa, con pocos parámetros y un solo nivel de abstracción.
- Sin código duplicado, sin código muerto, sin abstracciones especulativas.
- Clases con una sola responsabilidad; depender de interfaces, no de implementaciones (como ya hace la solución con los proyectos `I*`).
- Errores con excepciones de dominio, nunca silenciados.
- Seguir el estilo y las convenciones del código existente en cada proyecto.

## Comentarios

Mínimos; idealmente ninguno. El código tiene que explicarse solo mediante nombres, funciones extraídas y tipos. No comentar qué hace el código ni dejar código comentado. Solo se acepta un comentario cuando explica un *por qué* no evidente que el código no puede expresar (una restricción externa, un workaround de una librería).

## Idioma

Issues, PRs, commits y documentación en español. Identificadores de código y términos técnicos en inglés.

## Uso de IA

La letra exige declarar las herramientas de IA usadas y el contexto de uso. Todo lo generado por IA se revisa y verifica antes de commitearlo.

## Agent skills

Las skills están en `.agents/skills/` (`.claude/skills` es un symlink a esa carpeta).

### Issue tracker

Las issues viven en GitHub Issues de `santiremedi/AIOps`. Ver `docs/agents/issue-tracker.md`.
