---
title: "Runbook — FASE 19.5 Operational Alerts Baseline"
summary: "Runbook para validar las alertas basicas por route family y comprobar degradaciones automaticas."
order: 39
---

# Runbook — FASE 19.5 Operational Alerts Baseline

## Objetivo

Detectar degradaciones del runtime sin esperar a abrir Grafana.

## Alertas

### 1. Minimal Route Regression

```text
increase(ailab_route_family_prompt_tokens_total{family="minimal"}[10m]) > 500
```

Se activa cuando `minimal` deja de ser ligera.

### 2. Tool Fastpath Latency Spike

```text
sum(rate(ailab_route_family_latency_ms_sum{family="tool_fastpath"}[5m])) / sum(rate(ailab_route_family_latency_ms_count{family="tool_fastpath"}[5m])) > 8000
```

Se activa cuando `tool_fastpath` se degrada o LM Studio responde lento.

### 3. Cognitive Route Explosion

```text
increase(ailab_route_family_prompt_tokens_total{family="cognitive"}[10m]) > 12000
```

Se activa cuando hay recall runaway o inflacion de contexto.

### 4. Error Rate

```text
increase(ailab_route_family_errors_total[5m]) > 0
```

Se activa ante cualquier error reciente por family.

### 5. Governance Blocks Spike

```text
increase(ailab_route_family_blocked_total[10m]) > 10
```

Se activa ante abuso de prompts, loops de tools o agentes rotos.

## Como interpretar

| Señal | Interpretacion |
|---|---|
| `minimal` sube en tokens | regresion de contexto |
| `observe` sube en tokens | observacion contaminada |
| `tool_fastpath` sube en latencia | fastpath roto o backend lento |
| `cognitive` explota en tokens | recall runaway |
| `errors` sube | degradacion operativa |
| `blocked` sube | prompt abuse o tool misuse |

## Checklist

- Verificar que Prometheus scrapea `ai-lab-gateway`, `ai-lab-router` y `ai-lab-live-api`.
- Confirmar que `Error Rate` y `Governance Blocks Spike` muestran serie `0` cuando no hay eventos.
- Confirmar que `minimal` y `observe` siguen por debajo de `cognitive` en tokens.
- Confirmar que `tool_fastpath` no arrastra contexto grande.

## Panel de soporte

- Dashboard: `AI-LAB Route Family Observability Baseline`
- URL: `http://192.168.1.40:3000/d/ai-lab-route-family/ai-lab-route-family-observability-baseline`
