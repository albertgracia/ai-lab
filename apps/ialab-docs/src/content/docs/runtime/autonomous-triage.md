---
title: "Autonomous Runtime Triage"
summary: "FASE 36D: triage observacional bounded, determinista y always-on. Incidents, recommendations y métricas."
order: 40
---

El triage autónomo es **observacional**: no ejecuta remediación. Clasifica señales y genera contexto operacional.

## Endpoints

```text
GET /runtime/triage/snapshot
GET /runtime/triage/summary
GET /runtime/triage/incidents
GET /runtime/triage/recommendations
GET /runtime/triage/snapshots?limit=20
```

## Métricas

- `ailab_triage_incidents_total`
- `ailab_triage_critical_total`
- `ailab_triage_high_total`
- `ailab_triage_warning_total`

## Propiedades

- Bounded stores (no crecen sin límite).
- Determinista (misma señal → misma clasificación).
- Fail-safe (no rompe el gateway).
