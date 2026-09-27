# Issue tracker: GitHub

Las issues y specs de este repo viven como issues de GitHub en `santiremedi/AIOps`. Usar el CLI `gh` para todas las operaciones.

El clone tiene dos remotes (`origin` = `santiremedi/AIOps`, `upstream` = `jirabedra/AIOps`), así que pasar siempre `--repo santiremedi/AIOps` para no operar sobre el upstream.

## Convenciones

- **Crear una issue**: `gh issue create --repo santiremedi/AIOps --title "..." --body "..."`. Usar un heredoc para cuerpos multilínea.
- **Leer una issue**: `gh issue view <number> --repo santiremedi/AIOps --comments`.
- **Listar issues**: `gh issue list --repo santiremedi/AIOps --state open --json number,title,body,labels,comments`.
- **Comentar**: `gh issue comment <number> --repo santiremedi/AIOps --body "..."`
- **Cerrar**: `gh issue close <number> --repo santiremedi/AIOps --comment "..."`

Este repo no usa `/triage`. No crear ni exigir labels de triage.

## Cuando una skill dice "publicar en el issue tracker"

Crear una issue de GitHub en `santiremedi/AIOps`.

## Cuando una skill dice "traer el ticket relevante"

Correr `gh issue view <number> --repo santiremedi/AIOps --comments`.
