---
title: "Governance Drift Detection (37E)"
summary: "Detección de drift entre expectativas de governance y comportamiento real del runtime mediante señales de 37B/37C/37D, SLO y triage."
order: 62
---

## Qué es

**Governance Drift Detection (37E)** es el módulo que **cruza señales de governance** (violaciones de arquitectura, hotspots de governance, correlación con runtime) con el **estado operacional** (critical-path, chokepoints, SLO, triage) para detectar cuándo el runtime se desvía de lo que governance espera.

## Relación con fases anteriores

- **37B Correlation**: aporta `correlation_score` y hotspots correlacionados.
- **37C Critical Path**: aporta `top_files`, `chokepoints` y `blast-radius` por dominio.
- **37D Hotspot History**: aporta `drift_score`, tendencias y recurrencias históricas.
- **SLO + Triage**: aportan estado de salud operacional.

37E **consume estos inputs internamente** (llamadas Python directas, no HTTP).

## Endpoints (Gateway :8008)

- `GET /runtime/governance-drift` — snapshot completo con dominios y recomendaciones.
- `GET /runtime/governance-drift/summary` — resumen ligero.
- `GET /runtime/governance-drift/events` — eventos de drift recientes (bounded).
- `GET /runtime/governance-drift/domains` — detalle por dominio.
- `GET /runtime/governance-drift/recommendations` — recomendaciones de governance.
- `GET /runtime/governance-drift/reset` — reset del estado en memoria.

Todos responden **HTTP 200** con payload bounded/fail-safe.

## overall_drift

Score determinista 0–1 basado en:

| Componente | Peso | Descripción |
|-----------|------|-------------|
| avg CP score | 25% | Media de scores de critical-path por dominio |
| health_delta | 15% | Diferencia entre CP score y correlación esperada |
| chokepoint count | 10% | Normalizado a 5 chokepoints máximos |
| recurring count | 10% | Normalizado a 3 recurrencias máximas |
| trend count | 10% | Normalizado a 5 tendencias máximas |
| blast radius | 10% | Máximo blast radius presente |
| governance risk | 10% | Violaciones de arquitectura / hotspots |
| slo_impact | 10% | Impacto de estado SLO |

## governance_confidence

Score 0–1 que mide cuánto podemos confiar en los datos de governance:

```
governance_confidence = 1.0 - overall_drift - penalty(unknowns)
```

- Si hay ≥5 unknowns → penalización máxima 0.10.
- Si overall_drift es alto → confianza baja.

## Métricas Prometheus

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| `ailab_governance_drift_score` | gauge | Drift overall (0-1) |
| `ailab_governance_drift_governance_confidence` | gauge | Confianza en datos de governance (0-1) |
| `ailab_governance_drift_events_total` | gauge | Eventos de drift registrados |
| `ailab_governance_drift_domains_total` | gauge | Dominios analizados |
| `ailab_governance_drift_critical_domains_total` | gauge | Dominios con drift HIGH/CRITICAL |
| `ailab_governance_drift_unknowns_total` | gauge | Fuentes de señal no disponibles |
| `ailab_governance_drift_recommendations_total` | gauge | Recomendaciones activas |
| `ailab_governance_drift_health_delta_avg` | gauge | Media de health_delta entre dominios |
