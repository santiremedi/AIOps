---
name: make
description: >
  Desarrollar una funcionalidad completa de principio a fin: aclarar el pedido,
  abrir la issue, crear la rama, implementar con TDD, correr code-review y abrir
  la pull request. Usar cuando el usuario dice "make ...", "haceme ...",
  "desarrollá ...", "implementá ..." seguido de una funcionalidad detallada, o
  quiere que una idea termine en una PR mergeable.
disable-model-invocation: true
---

# Make

Orquesta el flujo completo de desarrollo de una funcionalidad: desde el pedido hasta la PR abierta. Encadena las skills de ingeniería del repo; no las reimplementa.

Flujo: **aclarar → issue → rama → implementar (TDD) → revisar → PR**.

Si el pedido es un bug difícil (no se ve la causa, flake, regresión entre dos estados), usar `/diagnosing-bugs` en vez de arrancar este flujo a ciegas. Cuando el loop de diagnóstico ya está en rojo, volver acá o a `/implement` para el fix.

## 0. Pre-requisitos

- Leer `docs/agents/issue-tracker.md` para saber cómo operar con las issues. Este repo no usa `/triage`; no exigir `docs/agents/triage-labels.md`.
- Verificar `git status` limpio y estar sobre la rama correcta (típicamente `main`) antes de crear la rama de trabajo.

## 1. Aclarar el pedido

Separar dos tipos de decisión:

- **Producto / negocio** (comportamiento esperado, alcance, límites, casos borde): son del usuario.
- **Técnicas** (arquitectura, APIs, archivos, diseño de código, cómo implementar): las toma el agente sin preguntar. Elegir lo que mejor encaje con el repo (`AGENTS.md`, código existente, ADRs) y seguir.

Cómo aclarar:

- Si en la misma conversación ya hubo un `/grill-me` (o un grilling equivalente) y quedó cerrado: usar esas respuestas como fuente de verdad para alcance y comportamiento. No hacer preguntas técnicas ni volver a preguntar lo ya decidido. Si quedó algún hueco de **producto**, preguntar solo eso y seguir; si no, ir directo a la issue.
- Si el pedido viene detallado y aún no se grilló, usar `/grill-me` solo para afinar alcance y decisiones de producto ambiguas — no para diseño de implementación.
- Si está incompleto o vago y no hay grill previo, no arrancar: preguntar lo mínimo necesario de **negocio** (comportamiento esperado, límites, qué pasa con casos borde).
- Si el pedido es chico y claro, saltar directo a la issue; el grilling no es obligatorio.

Después de la issue: no volver a preguntar por técnica. Cualquier duda de implementación se resuelve explorando el repo y decidiendo.

## 2. Abrir la issue

- Usar `/to-tickets` si el trabajo se parte en slices.
- Para trabajo chico o mediano, crear la issue directamente con este template:

```markdown
## Qué construir

Comportamiento end-to-end desde la perspectiva del usuario.

## Criterios de aceptación

- [ ] Criterio 1
- [ ] Criterio 2
```

- Todo en español (título y cuerpo); solo términos técnicos en inglés. Publicar según `docs/agents/issue-tracker.md`. No aplicar labels de triage.
- Anotar el identificador de la issue (número de GitHub o path en `.scratch/`): se usa en la rama, los commits y la PR.

## 3. Crear la rama

- Prefijo según el tipo de cambio: `feature/`, `fix/`, `chore/`, `docs/`.
- Nombre corto en inglés del cambio, guiones: `feature/circuit-breaker`.
- Crearla desde `main` actualizada: `git checkout main && git pull && git checkout -b <rama>`.

## 4. Implementar

- Trabajar sobre la issue: `/implement`, que usa `/tdd` en las costuras donde corresponde.
- TDD en el backend (MSTest + Moq, en `Backend/PharnaGo.Test`). El frontend no tiene specs: no agregar un framework de pasada; la UI se verifica en el browser.
- Cambios de infraestructura (`k8s/`, `docker-compose.yml`, `chaos-engineering/`, Grafana): no llevan TDD; se verifican aplicándolos y observando el comportamiento (pods `READY`, métricas, logs), y se deja constancia en la PR.
- Durante el loop: el test que está en rojo (`dotnet test Backend/PharmaGo.sln --filter "FullyQualifiedName~<Clase>"`). Al final: la verificación completa de `AGENTS.md`.
- Commits cortos en español, imperativo, una línea: `Agrega readiness probe al gateway` — uno por paso lógico.

## 5. Revisar

- Correr `/code-review` sobre `origin/main...HEAD` antes de abrir la PR.
- Resolver los hallazgos reales: arreglar, o documentar en la PR si se decide no tocar.
- Si `/code-review` encontró problemas, re-implementar los fixes con `/tdd` y volver a revisar hasta que quede limpio.

## 6. Abrir la PR

- Correr la verificación completa de `AGENTS.md` una última vez.
- Abrir la PR con `/pull-request`.
- Verificar que CI de GitHub quede en verde si hay checks. No mergear salvo que el usuario lo pida.

## Al finalizar

Resumir al usuario: issue creada, rama, commits, hallazgos de code-review resueltos, URL de la PR y estado de CI.
