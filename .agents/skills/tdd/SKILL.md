---
name: tdd
description: Desarrollo guiado por tests. Usar cuando el usuario quiere construir features o arreglar bugs test-first, menciona "red-green-refactor" o quiere tests de integración.
---

# Test-Driven Development

TDD is the red → green loop. This skill is the reference that makes that loop produce tests worth keeping: what a good test is, where tests go, the anti-patterns, and the rules of the loop. Every section applies on every cycle — consult them before and during the loop, not after.

When exploring the codebase, read `CONTEXT.md` (if it exists) so test names and interface vocabulary match the project's domain language, and respect ADRs in the area you're touching.

## What a good test is

Tests verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't. A good test reads like a specification — "user can checkout with valid cart" tells you exactly what capability exists — and survives refactors because it doesn't care about internal structure.

See [tests.md](tests.md) for examples and [mocking.md](mocking.md) for mocking guidelines.

## Seams — where tests go

A **seam** is the public boundary you test at: the interface where you observe behavior without reaching inside. Tests live at seams, never against internals.

**Test only at pre-agreed seams.** Before writing any test, write down the seams under test and confirm them with the user. No test is written at an unconfirmed seam. You can't test everything — agreeing the seams up front is how testing effort lands on the critical paths and complex logic instead of every edge case.

Ask: "What's the public interface, and which seams should we test?"

## Anti-patterns

- **Implementation-coupled** — mocks internal collaborators, tests private methods, or verifies through a side channel (querying the database instead of using the interface). The tell: the test breaks when you refactor but behavior hasn't changed.
- **Tautological** — the assertion recomputes the expected value the way the code does (`expect(add(a, b)).toBe(a + b)`, a snapshot derived by hand the same way, a constant asserted equal to itself), so it passes by construction and can never disagree with the code. Expected values must come from an independent source of truth — a known-good literal, a worked example, the spec.
- **Horizontal slicing** — writing all tests first, then all implementation. Bulk tests verify _imagined_ behavior: you test the _shape_ of things rather than user-facing behavior, the tests go insensitive to real changes, and you commit to test structure before understanding the implementation. Work in **vertical slices** instead — one test → one implementation → repeat, each test a **tracer bullet** that responds to what the last cycle taught you.

## Rules of the loop

- **Red before green.** Write the failing test first, then only enough code to pass it. Don't anticipate future tests or add speculative features.
- **One slice at a time.** One seam, one test, one minimal implementation per cycle.
- **Refactoring is not part of the loop.** It belongs to the review stage (see the `code-review` skill), not the red → green implementation cycle.

## Este repo

Rutas relativas a `Implementacion K8S/Codigo/`.

- **Backend** (`Backend/`): MSTest + Moq. Los tests viven en `Backend/PharnaGo.Test/`, espejando la capa (`BusinessLogic.Test/`, `DataAccess.Test/`, `WebApi.Test/`), con `[TestClass]` y `[TestMethod]`. Durante el loop: `dotnet test Backend/PharmaGo.sln --filter "FullyQualifiedName~<Clase>"`. Al final: `dotnet test Backend/PharmaGo.sln`.
- **Límite de mocks**: los `IRepository<T>` son el borde con la base de datos; se mockean con Moq o se usa EF Core InMemory (ya referenciado). No mockear managers ni otras clases propias.
- **Frontend** (`Frontend/`): Karma está configurado pero no hay specs. No agregar un framework de pasada. El TDD de reglas de negocio va en el backend. Si hay que verificar UI, hacerlo en el browser y dejar constancia en la PR.
- **Infraestructura** (`k8s/`, chaos scripts, observabilidad): no aplica TDD. Se verifica aplicando el cambio y observando el comportamiento esperado.
- Al final: la verificación completa de `AGENTS.md`.
