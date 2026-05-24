---
title: "Cognitive Health Layer (37A)"
summary: "Capa bounded, read-only y metadata-only que puntúa nodos, estima confianza de routing y emite triggers watchdog sin remediación."
order: 30
---

## Objetivo

FASE `37A-COGNITIVE-HEALTH-LAYER-01` introduce una capa **observacional** (sin cambiar routing) para responder 3 preguntas operativas de forma determinista:

- ¿Qué tan saludable está el runtime *para servir peticiones ahora* (score 0-100)?
- ¿Qué confianza tenemos en el routing (redundancia + scores)?
- ¿Hay señales watchdog (latencia p95 alta, TTFB p95 alta, success_rate bajo, sin nodos online)?

## Reglas

- **Read-only**: no escribe en `runtime/state/*`.
- **Bounded**: stores en memoria con ventanas pequeñas (máx 256 muestras por clave).
- **Metadata-only**: no usa prompts, no usa tools, no deriva acciones.
- **Fail-safe**: endpoints siempre responden `200` con `status=ok|degraded`.
- **No routing changes**: no afecta selección de modelo/nodo (solo observabilidad).

## Endpoints (ailab-gateway :8008)

- `GET /runtime/health`
- `GET /runtime/health/score`
- `GET /runtime/health/nodes`
- `GET /runtime/health/routing-confidence`
- `GET /runtime/health/watchdog`
- `GET /runtime/health/latency`

Nota: en esta fase **no** se exponen endpoints equivalentes en `ailab-router` (8083); el router permanece como orquestación interna.

## Métricas Prometheus

Expuestas en `GET /metrics` (gateway):

- `ailab_cognitive_health_score` (gauge, 0-100)
- `ailab_cognitive_health_routing_confidence` (gauge, 0-1)
- `ailab_cognitive_health_nodes_online` (gauge)
- `ailab_cognitive_health_watchdog_triggers_total` (counter)
- `ailab_gateway_latency_p50_ms{kind="request_total"|"ttfb"}` (gauge)
- `ailab_gateway_latency_p95_ms{kind="request_total"|"ttfb"}` (gauge)

## Fuentes de datos

- `runtime/control/control_plane.py` (estado agregado de nodos online).
- `runtime/routing/routing_history.py` (success_rate/latencia por nodo, ventana temporal).
- `runtime/telemetry/gateway_metrics.py` (latencias p50/p95 bounded in-memory para `ttfb` y `request_total`).
