---
name: pull-request
description: Abrir una pull request siguiendo el formato corto en bullets del repo. Usar cuando el trabajo de una rama está terminado y hay que publicarla en GitHub, o cuando el usuario pide "abrir PR", "publicar la rama", "armar la pull request".
---

# Pull Request

Abre una PR de la rama actual contra `main`, con la descripción en el formato corto de este repo.

## Proceso

### 1. Verificar que la rama está lista

- La rama tiene el prefijo correcto (`feature/`, `fix/`, `chore/`, `docs/`) y un nombre corto del cambio.
- Corre en verde la verificación completa de `AGENTS.md`. Si falla, detenerse y arreglarlo antes de abrir la PR. No se abre una PR con la verificación en rojo.
- Los cambios están commiteados (revisar `git status` y `git log origin/main..HEAD --oneline`).

### 2. Armar el cuerpo de la PR

Escribir la descripción con este formato:

```markdown
## Qué

- bullet 1
- bullet 2

## Por qué

Resuelve #<issue> — una línea de contexto.

## Cómo se probó

- `dotnet test Backend/PharmaGo.sln` — OK (solo los comandos que aplicaban al cambio)
- (opcional) el flujo de browser, el rollout o la métrica/alerta observada que verificó el cambio

## Notas

- (opcional) solo si hace falta
```

Reglas del formato:

- **Bullets cortos**, sin párrafos largos. Máximo 5 bullets en `Qué`.
- `Qué` describe el comportamiento resultante, no el detalle de implementación que el diff ya muestra.
- `Por qué` referencia la issue con `Resolves #N` o `Closes #N` si la rama viene de una issue de GitHub. Si el tracker es markdown local, citar el path del ticket (`.scratch/<feature>/issues/01-….md`) en vez de `#N`.
- `Cómo se probó` lleva los comandos reales que corriste con su resultado.
- `Notas` solo si hay algo que el reviewer debe saber: decisiones de diseño, tradeoffs, deuda técnica. Si no hay nada, la sección se omite.
- El título de la PR: `tipo: resumen corto` en español (`fix:`, `feat:`, `chore:`, `docs:`).

### 3. Abrir la PR

- Push de la rama: `git push -u origin <rama>`.
- Crear la PR en draft con la descripción armada: `gh pr create --draft --base main --head <rama> --title "<título>" --body "<cuerpo>"`. Preferir un heredoc para el body.

### 4. Confirmar

- Mostrar la URL de la PR.
- Verificar que los checks de CI arranquen si existen. Si un check falla, avisar con la salida y ofrecer arreglarlo en la misma rama.
- La PR queda en draft: sacarla de draft y mergearla son decisiones del humano, no del agente.
