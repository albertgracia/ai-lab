---
title: "ADR-001 — Runtime Governance"
summary: "Decidir que la gobernanza es parte del runtime: evidencia, límites de confianza, trazabilidad git y disciplina de publicación."
order: 41
---

# ADR-001 — Runtime Governance

## Contexto

AI-LAB evolucionó de prompts/routing reactivo a un runtime observacional con múltiples capas de verdad y decisiones que afectan operación.

## Problema

Sin reglas explícitas:

- el LLM puede afirmar cosas no observadas,
- los cambios se mezclan con estado vivo,
- y la operación pierde trazabilidad.

## Decisión

- Definir governance como disciplina transversal del runtime.
- Imponer precedencia: authority (Prometheus) > operational truth > signals estructurales.
- Separar estado vivo (`runtime/state/*`) de cambios versionables.

## Consecuencias

- Más validación (tests, evidence guards) antes de cerrar checkpoints.
- Los reportes pueden responder `NO DISPONIBLE` en vez de inventar.

## Tradeoffs

- Menos “comodidad” para responder rápido sin evidencia.
- Mayor complejidad conceptual (pero reducimos drift).

## Riesgos evitados

- Operational drift.
- Falsos positivos de “operational truth”.
- Checkpoints sin reproducibilidad.
