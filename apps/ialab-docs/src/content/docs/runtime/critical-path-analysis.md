---
title: "Critical Path Analysis (37C)"
summary: "Análisis híbrido del critical-path: file-level import graph + agregación por dominio (runtime/<folder>/). Metadata-only, bounded y determinista."
order: 60
---

## Objetivo

- Detectar **archivos runtime críticos** (fan-in/fan-out/centralidad) y agregarlos por **dominio** (carpeta bajo `runtime/`).
- Correlacionar, de forma **explicable** y **fail-safe**, con señales runtime existentes (37A Health, 37B Correlation, SLO, guards, triage) sin mutar routing.

## Propiedades

- **Read-only**: no escribe en `runtime/state/*`.
- **Bounded**: número de archivos escaneados, edges, top_n y recomendaciones capados.
- **Determinista**: orden estable, thresholds fijos, sin heurísticas no acotadas.

## Endpoints (Gateway :8008)

- `GET /runtime/critical-path`
- `GET /runtime/critical-path?top_n=10`
- `GET /runtime/critical-path/summary`
- `GET /runtime/critical-path/modules?top_n=10`
- `GET /runtime/critical-path/routes`
- `GET /runtime/critical-path/dependencies?file=runtime/gateway/openai_gateway.py`
- `GET /runtime/critical-path/recommendations`
- `GET /runtime/critical-path/reset`

Todos responden **HTTP 200** (fail-safe) con `status: ok|degraded`.

## Métricas

Expuestas en `GET /metrics` (sin cardinalidad dinámica):

- `ailab_critical_path_score`
- `ailab_critical_path_top_modules_total`
- `ailab_critical_path_high_total`
- `ailab_critical_path_critical_total`
- `ailab_critical_path_unknowns_total`
- `ailab_critical_path_routes_critical_total`
- `ailab_critical_path_recommendations_total`

## Notas

- La granularidad primaria es **file-level** (paths `runtime/*.py`).
- La agregación secundaria es por **dominio** (carpeta inmediata bajo `runtime/`).
