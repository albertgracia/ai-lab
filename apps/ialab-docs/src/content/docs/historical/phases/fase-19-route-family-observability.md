---
title: "FASE 19.4 — Route Family Observability"
summary: "Documentacion de la observabilidad por route family: metricas Prometheus, lectura en Grafana, interpretacion de anomalias y validacion operativa del runtime." 
order: 36
---

## Hito

Se formalizo la observabilidad de `route families` para que el runtime pueda medirse por tipo de flujo, no solo por volumen global. Esto permite detectar regresiones de contexto, latencia y coste de tokens en rutas simples como `minimal` y `observe`.

## Que es una route family

Las `route families` son la segmentacion operativa del runtime:

| Family | Significado |
|---|---|
| `minimal` | Flujo minimo: saludos, informes, resúmenes, respuestas cortas |
| `observe` | Inspeccion tecnica/operativa sin contexto pesado |
| `tool_fastpath` | Peticiones que deben resolver herramientas con contexto minimo |
| `cognitive` | Flujo cognitivo general con contexto, recall y shaping |
| `learning` | Endpoints internos de aprendizaje y analitica |

## Metricas Prometheus añadidas

| Metrica | Tipo | Labels | Uso |
|---|---|---|---|
| `ailab_route_family_total` | Counter | `family` | Distribucion de solicitudes por familia |
| `ailab_route_family_latency_ms` | Histogram | `family` | Latencia observada por familia |
| `ailab_route_family_prompt_tokens_total` | Counter | `family` | Tokens de prompt acumulados por familia |
| `ailab_route_family_completion_tokens_total` | Counter | `family` | Tokens de completion acumulados por familia |
| `ailab_route_family_errors_total` | Counter | `family` | Errores acumulados por familia |
| `ailab_route_family_blocked_total` | Counter | `family` | Bloqueos de policy por familia |

Tambien se añadieron:

- `ailab_embedding_input_chars`
- `ailab_embedding_truncations_total`
- `ailab_recall_query_chars`

## PromQL recomendado

```text
sum by (family) (ailab_route_family_total)
```

```text
histogram_quantile(0.95, sum by (le, family) (rate(ailab_route_family_latency_ms_bucket[5m])))
```

```text
avg by (family) (ailab_route_family_latency_ms)
```

```text
sum by (family) (rate(ailab_route_family_prompt_tokens_total[5m]))
```

```text
sum by (family) (rate(ailab_route_family_completion_tokens_total[5m]))
```

```text
sum by (family) (rate(ailab_route_family_errors_total[5m]))
```

```text
sum by (family) (rate(ailab_route_family_blocked_total[5m]))
```

## Paneles Grafana sugeridos

| Panel | Tipo | Query |
|---|---|---|
| Route Family Distribution | Stat / Bar | `sum by (family) (ailab_route_family_total)` |
| Latency by Route Family | Time series | `sum by (family) (rate(ailab_route_family_latency_ms_sum[5m])) / sum by (family) (rate(ailab_route_family_latency_ms_count[5m]))` |
| Prompt Tokens by Family | Time series | `sum by (family) (rate(ailab_route_family_prompt_tokens_total[5m]))` |
| Completion Tokens by Family | Time series | `sum by (family) (rate(ailab_route_family_completion_tokens_total[5m]))` |
| Errors by Family | Time series | `sum by (family) (rate(ailab_route_family_errors_total[5m]))` |
| Blocked by Family | Time series | `sum by (family) (rate(ailab_route_family_blocked_total[5m]))` |

Grafana: `http://192.168.1.40:3000`

## Como interpretar anomalías

- Si `minimal` o `observe` suben en tokens, hay regresion de contexto.
- Si `minimal` sube en latencia, alguien volvió a meter contexto pesado o recall innecesario.
- Si `tool_fastpath` sube en errores, el clasificador de herramientas o el parser de tool calls se degradó.
- Si `cognitive` domina demasiado, el runtime esta cayendo en la ruta pesada por defecto.
- Si `learning` crece sin cambios de aprendizaje, puede haber un job o dashboard consultando demasiado.

## Checklist de validacion

- `ailab_route_family_total` tiene al menos una serie por family.
- `minimal` y `observe` muestran menos tokens que `cognitive`.
- `route_family_selected` aparece en audit/log.
- `ailab_route_family_errors_total` no crece en `minimal` durante requests triviales.
- `ailab_embedding_truncations_total` permanece bajo o en cero para queries normales.
- `ailab_recall_query_chars` se mantiene en valores cortos.
- La latencia del panel es promedio real basada en `_sum/_count`, no p95.

## Baseline operativo

La referencia a mantener es:

- ruta minima y observacion ligera
- tokens bajos en solicitudes simples
- latencia contenida en `minimal`/`observe`
- recall controlado y acotado

## Siguiente fase

FASE 19.5 — Operational Alerts Baseline

Objetivo: detectar degradaciones automaticas sin depender de abrir Grafana.
