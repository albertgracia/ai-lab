---
title: "FASE 19.5 — Operational Alerts Baseline"
summary: "Reglas de alerta para detectar degradaciones del runtime por route family antes de abrir Grafana."
order: 38
---

## Hito

Se definio un baseline de alertas para detectar drift arquitectonico, inflacion de contexto y degradacion de latencia sin inspeccion manual.

## Alertas minimas

| Alerta | Expresion | Detecta |
|---|---|---|
| Minimal Route Regression | `increase(ailab_route_family_prompt_tokens_total{family="minimal"}[10m]) > 500` | `minimal` contaminada con contexto pesado |
| Tool Fastpath Latency Spike | `sum(rate(ailab_route_family_latency_ms_sum{family="tool_fastpath"}[5m])) / sum(rate(ailab_route_family_latency_ms_count{family="tool_fastpath"}[5m])) > 8000` | `tool_fastpath` roto o LM Studio degradado |
| Cognitive Route Explosion | `increase(ailab_route_family_prompt_tokens_total{family="cognitive"}[10m]) > 12000` | recall runaway o context inflation |
| Error Rate | `increase(ailab_route_family_errors_total[5m]) > 0` | errores recientes por family |
| Governance Blocks Spike | `increase(ailab_route_family_blocked_total[10m]) > 10` | prompt abuse, loop tool-use o agente roto |

## Por que estas reglas

- `prompt_tokens` y `latency` ya miden coste real por family.
- `errors` y `blocked` permiten detectar fallos operativos sin revisar dashboards.
- `minimal` y `observe` son la señal mas sensible para ver regresiones de contexto.

## Recomendaciones operativas

- Alertar primero por `minimal` y `tool_fastpath`.
- Tratar `cognitive` como ruta pesada esperada, pero vigilada.
- Mantener `learning` separado para no ensuciar la señal operativa.

## Validacion

- Las reglas deben aparecer en Prometheus como `up`.
- `Error Rate` y `Governance Blocks Spike` deben mostrar serie `0` hasta que haya eventos.
- `Tool Fastpath Latency Spike` debe depender de `_sum` y `_count` del histogram.

## Siguiente fase

FASE 20 — Runtime Drift Prevention

Objetivo: detectar automaticamente inflacion de prompts, recall inutil, crecimiento de contexto y rutas mal clasificadas antes de que el usuario lo note.
