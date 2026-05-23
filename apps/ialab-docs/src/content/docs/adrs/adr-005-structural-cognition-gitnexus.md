---
title: "ADR-005 — Structural Cognition (GitNexus)"
summary: "Adoptar GitNexus como verdad estructural grounded para blast radius, coupling y drift, sin reemplazar autoridad operacional."
order: 45
---

# ADR-005 — Structural Cognition (GitNexus)

## Contexto

AI-LAB necesita entender el impacto de cambios y riesgos de acoplamiento, no solo métricas runtime.

## Problema

- Sin cognición estructural, el análisis de blast radius y coupling es manual.
- Un runtime gateway-centric tiende a singularity y fan-out alto.

## Decisión

- Usar GitNexus para indexar la codebase y producir señales deterministas.
- Integrar signals de codebase (ownership, hotspots, blast radius) en reporting/validation/incidents.
- Gobernar `.gitnexusignore` y evitar indexar `runtime/state/*`.

## Consecuencias

- Se puede hacer review estructural reproducible.
- Se detecta drift y hubs peligrosos.

## Tradeoffs

- Coste de indexación.
- Riesgo de confundir structural truth con authority (se evita con truth layers).

## Riesgos evitados

- Cambios “seguros” que rompen blast radius.
- Crecimiento silencioso de singularities.
