---
title: "Graph-Runtime Correlation (37B)"
summary: "Primera capa de correlación explicable entre hotspots topológicos (GitNexus) y degradación runtime real (health/SLO/triage/federation)."
order: 31
---

## Qué es

FASE `37B-GRAPH-RUNTIME-CORRELATION-01` cruza señales de topología (GitNexus graph reasoning) con señales runtime observacionales:

- **Graph hotspots / blast radius / governance risk** (GitNexus topology)
- **Cognitive Health Layer (37A)**: `health_score`, `routing_confidence`, `nodes`
- **SLO**: `overall_status`, `violations_total`
- **Autonomous triage**: severidad agregada
- **Federation guards**: estado y counters
- **Evidence lineage**: replay/stale/invalid

El resultado permite afirmar (con disciplina epistemológica):

"Este hotspot arquitectónico coincide con una degradación runtime real".

## Qué NO hace

- No cambia routing.
- No ejecuta remediación.
- No escribe en `runtime/state/*`.
- No hace scans infinitos ni polling agresivo.
- No convierte inferencias en hard facts.

## HARD_FACTS vs Inferido vs Unknowns

- **hard_facts**: lecturas directas de snapshots/metrics disponibles.
- **inferred**: correlaciones derivadas (p.ej. fan-in alto + replay detections + health warning).
- **unknowns**: fuentes ausentes o no accesibles.

La fase expone explícitamente `unknowns` y `unavailable_fields`.

## Correlation Score

Score determinista `0.0–1.0` basado en weighted sum de:

- centrality/fan-in/fan-out
- blast radius + governance risk
- health degradation + routing confidence degradation
- SLO status
- triage severity
- federation guard state
- evidence replay/stale/invalid

Clasificación:

- `0.00–0.24` INFO
- `0.25–0.49` LOW
- `0.50–0.69` MEDIUM
- `0.70–0.84` HIGH
- `0.85–1.00` CRITICAL

## Endpoints (gateway 8008)

- `GET /runtime/correlation`
- `GET /runtime/correlation/summary`
- `GET /runtime/correlation/hotspots`
- `GET /runtime/correlation/blast-radius`
- `GET /runtime/correlation/findings`
- `GET /runtime/correlation/recommendations`

## Métricas Prometheus

Expuestas en `GET /metrics` (gateway):

- `ailab_correlation_score`
- `ailab_correlation_hotspots_total`
- `ailab_correlation_high_risk_total`
- `ailab_correlation_critical_total`
- `ailab_correlation_unknowns_total`
- `ailab_correlation_recommendations_total`
- `ailab_correlation_runtime_health_linked_total`
- `ailab_correlation_graph_health_linked_total`
