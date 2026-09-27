---
name: implement
description: Implementar un trabajo basado en una spec o un conjunto de tickets.
disable-model-invocation: true
---

Implement the work described by the user in the spec or tickets.

Use `/tdd` where possible, at pre-agreed seams.

During the loop, run only the test class you are touching (`dotnet test Backend/PharmaGo.sln --filter "FullyQualifiedName~<Clase>"`). Do not invent a frontend test command — that package has no specs. Infrastructure changes (`k8s/`, `docker-compose.yml`, chaos scripts, Grafana) are verified by applying them and observing the result.

Once done, run the full verification described in `AGENTS.md`, then use `/code-review` to review the work.

Commit your work to the current branch. Messages in Spanish, imperative, one line.
