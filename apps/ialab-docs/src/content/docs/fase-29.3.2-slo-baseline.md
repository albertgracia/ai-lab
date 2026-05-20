---
title: "FASE 29.3.2 — SLO Baseline & Post-Routing Burn-In"
summary: "Burn-in de 45 minutos validando el impacto del routing tightening. TTFB p50 reducido a 804ms (-29%), 100% success rate, 0 crashes, 0 qwen3.6 usage. SLO baseline establecida."
order: 72
---

## Objetivo

Validar el impacto real del routing tightening de FASE 29.3.1 y establecer baseline SLO para el runtime de 3 modelos.

## Burn-in

- **Duración:** 45 minutos
- **Workers:** 3 concurrentes
- **Distribución:** 40% greetings/light, 25% coding, 15% architecture, 10% embeddings, 10% mixed
- **Streaming:** Real (AI_LAB_REAL_STREAMING=true)

## Resultados

### Latencia

| Métrica | 29.3-B (antes) | 29.3.2 (ahora) | Delta |
|---------|---------------|----------------|-------|
| **TTFB p50** | 1129ms | **804ms** | **-29%** |
| TTFB avg | 3947ms | 2446ms | -38% |
| Latency p50 | 6963ms | 11658ms | +67% |
| Latency p95 | 45010ms | 45028ms | +0% |

### Estabilidad

| Métrica | Valor |
|---------|-------|
| Requests totales | 306 |
| Success rate | **100%** |
| Gateway crashes | **0** |
| qwen3.6 usage | **0** |
| Orphan streams | **0** |

### Routing efficiency

| Métrica | Delta |
|---------|-------|
| Greeting fastpath hits | +87 |
| Llama lightweight hits | +116 |

## SLO Baseline

| SLO | Target | Actual | Status |
|-----|--------|--------|--------|
| TTFB p50 | ≤ 1.2s | 804ms | ✅ |
| Success rate | ≥ 99% | 100% | ✅ |
| Gateway stability | 0 crashes | 0 | ✅ |
| qwen3.6 usage | 0 | 0 | ✅ |

## Análisis

La reducción del 29% en TTFB p50 confirma que el routing tightening funciona: greetings y prompts ligeros van a llama-3.1-8b (TTFB más rápido). La latencia p50 subió porque el workload incluye más coding/architecture (25%+15%) que usa qwen2.5-14b (más lento por token pero más capaz).

El 100% de success rate en 45 minutos con 3 workers concurrentes valida la estabilidad completa del runtime.

**Checkpoint: CP-29.3.2-SLO-BASELINE-STABLE**
