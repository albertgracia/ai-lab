---
title: "Cognitive SLO Governance"
summary: "SLO framework del runtime: salud, degradación, enforcement (dry-run) y endpoint always-on."
order: 41
---

El SLO framework define salud operacional y degradación segura basada en métricas (TTFB/timeouts/GPU pressure).

## Endpoints

```text
GET /slo/health
GET /runtime/slo/summary
GET /runtime/slo/status
GET /runtime/slo/violations?limit=50
```

## Semántica

- `enabled=false` devuelve payload “disabled” (si enforcement está apagado), pero **siempre 200**.
- `dry_run` permite validar dashboards sin bloquear requests.

## Relación con governance

- SLO no “decide” arquitectura.
- SLO alimenta degradación y rutas de protección (por ejemplo forced llama en presión).
