---
title: "Agentic Runtime"
summary: "Documentación del runtime agentic gobernado de AI-LAB: simulation, planner, readonly executor, sandbox write y rollback."
order: 3
---

## Qué contiene

- **FASE 28 — Governed Agentic Runtime** — plan técnico completo con 10 capas: Action Intent Layer, planner, risk scoring determinista, dry-run, governance, approval gate con tickets HMAC, sandbox, verifier, rollback, replay
- **FASE 28.0** — Simulation-only mode
- **FASE 28.1** — Planner runtime skeleton
- **FASE 28.2** — Readonly executor
- **FASE 28.3** — Sandbox write runtime

## Principio fundacional

```
LLM PROPONE  →  runtime EVALÚA  →  humano APRUEBA  →  sandbox EJECUTA
```

Nunca al revés. No hay ejecución directa del LLM. No hay autonomía sin approval explícito.

## Checkpoint actual

**CP-28.3-SANDBOX-WRITE-STABLE** — sandbox write runtime estable con burn-in validado.
