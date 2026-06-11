---
title: "Cognitive Health Layer (37A)"
summary: "Contrato 37A-COGNITIVE-HEALTH-LAYER-01: capa liviana, determinista y metadata-only para salud del runtime. Always-on, fail-safe, bounded."
order: 12
---

## Versión del contrato

`37A-COGNITIVE-HEALTH-LAYER-01`

Implementado en `runtime/health/cognitive_health_layer.py`.

## Principios de diseño

| Principio | Descripción |
|---|---|
| **Read-only** | Solo lee runtime state. No modifica estado ni comportamiento de routing. |
| **Fail-safe** | Toda función pública retorna un payload válido aunque falle una dependencia. |
| **Bounded** | Sin loops, sin IO externa, sin dependencias circulares. |
| **Metadata-only** | No expone configuración ni secrets. Solo scores, estados y razones. |

## Endpoints que consume

| Endpoint | Propósito |
|---|---|
| `GET /runtime/health` | Snapshot completo de salud cognitiva |
| `GET /runtime/health/degradations` | Vista de degradaciones (offline, scores bajos, watchdog) |
| `GET /metrics` (gateway) | Métricas Prometheus de salud cognitiva |

## Componentes

### `build_cognitive_health_snapshot(window_minutes=60)`

Top-level health snapshot. Retorna:

| Campo | Descripción |
|---|---|
| `status` | `"ok"` o `"degraded"` |
| `score` | Score general 0-100 |
| `overall_health` | `{score, status}` con niveles: healthy ≥80, warning ≥60, degraded ≥40, critical <40 |
| `routing_confidence` | `{confidence 0-1, nodes_online, avg_node_score, reasons}` |
| `nodes` | Array de `NodeHealth` por nodo |
| `nodes_total` / `nodes_online` | Conteo de nodos |
| `watchdog` | Snapshot del watchdog interno |
| `gpu_states` | `{rx9070, rx7900xt}` con estado operacional |
| `unavailable_fields` | Campos que no pudieron resolverse |
| `unknowns` | Estados no determinables |
| `contract_version` | Siempre `37A-COGNITIVE-HEALTH-LAYER-01` |

### `build_node_scores(window_minutes=60)`

Por nodo: `NodeHealth{node, online, score 0-1, reasons[], stats{models, avg_latency_ms, success_rate, total_requests, last_updated}}`.

Score base 0.50, +0.20 si online, se ajusta por success_rate y latencia:

| Latencia | Ajuste |
|---|---|
| ≤1s | +0.20 |
| ≤5s | +0.12 |
| ≤15s | +0.05 |
| ≤30s | +0.00 |
| >30s | -0.20 |

Fuentes: `control_plane.get_control_nodes()` + `routing_history.stats_by_node()` + backend aliases.

### `build_routing_confidence(node_scores)`

Confianza 0-1 basada en nodos online:

- 0 nodos online → `confidence: 0.0`
- 1 nodo → penalización -0.10 (single_node)
- ≥2 nodos → bonificación +0.15 (redundancy_ok)
- Fórmula: `0.50 + (avg_score - 0.5) * 0.60 + bonificación/penalización`

### `build_watchdog_snapshot(node_scores)`

Watchdog interno que emite triggers metadata-only. Sin remediación. Solo clasificación.

Triggers posibles:

| Trigger | Severidad | Condición |
|---|---|---|
| `no_nodes_online` | critical | nodes_online == 0 |
| `latency_p95_high` | warning | p95 ≥60s y count ≥10 |
| `ttfb_p95_high` | warning | TTFB p95 ≥15s y count ≥10 |
| `success_rate_low` | warning | success rate <90% |

### `build_degradations_snapshot(window_minutes=60)`

Vista de degradaciones para `/runtime/health/degradations`. Degradaciones por:
- Nodos offline (critical)
- Nodos online con score <0.60 (warning)
- Watchdog triggers activos

### `build_cognitive_health_prometheus_metrics()`

Renderiza métricas Prometheus para el endpoint `/metrics`:

```
ailab_cognitive_health_score
ailab_cognitive_health_routing_confidence
ailab_cognitive_health_nodes_online
ailab_cognitive_health_watchdog_triggers_total
ailab_gateway_latency_p50/p95_ms (request_total, ttfb)
```

## Fórmula del health score

```
overall = 100 * (0.60 * avg_node_score + 0.40 * routing_confidence)
```

Donde:
- `avg_node_score` = promedio de scores de nodos online
- `routing_confidence` = confianza derivada de nodos online y redundancia

Esto es **independiente** del `validation_score` (56.3 actual, calculado por `runtime_validation_framework.py`). El health score mide disponibilidad operacional de nodos; el validation score mide integridad de invariantes + safety gates.

## Relación con health_score actual

En la auditoría más reciente (2026-06-11):

| Componente | Valor | Estado |
|---|---|---|
| Cognitive health score | 79.6 | Warning (≥60, <80) |
| Nodos online | 1 (.50) | Single node penalty |
| Routing confidence | 0.64 | Reducido por single_node |
| GPU RX9070 | active_inference_backend | Online |
| GPU RX7900XT | unknown | Sin datos de sensor |

## Always-on guarantee

El endpoint `GET /runtime/health` responde **siempre 200** aunque el control_plane, routing_history o sensor_fusion fallen. Cada sub-función tiene su propio try/except con fallback a valores seguros.

## Dependencias

| Dependencia | Opcional | Fallback |
|---|---|---|
| `control_plane.get_control_nodes()` | Sí | `nodes = {}` |
| `routing_history.stats_by_node()` | Sí | `hist = {}` |
| `routing_history.read_route_history()` | Sí | `records = []` |
| `gateway_metrics.get_latency_stats()` | Sí | `{count: 0, p95_ms: 0}` |
| `sensor_fusion.SensorFusionEngine()` | Sí | `gpu_states = unknown` |
