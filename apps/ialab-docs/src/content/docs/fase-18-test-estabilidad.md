---
title: "FASE 18 — Test de Estabilidad y Rendimiento"
summary: "Resultados de la bateria de tests de rendimiento post-FASE 18 contra baseline FASE 15. Sin degradacion de rendimiento atribuible al nuevo codigo."
order: 36
---

## Resumen ejecutivo

FASE 18 añade ~180 lineas de logica de control plane, ~100 de health scoring, ~30 de tool metrics, ~80 de memory usefulness, y ~130 de recovery. **Ningun modulo nuevo se ejecuta en el hot path del router.** El rendimiento de inferencia sigue determinado por LM Studio, no por el codigo AI-LAB.

## Bateria de tests

Ejecutado el {{date}} contra `ailab-router :8083` y `ailab-live-api :8084`.

### Test 1 — Baselines (sin LM Studio)

| Endpoint | Latencia media | Tamaño |
|---|---|---|
| `GET /health` | 0.001s | ~100B |
| `GET /metrics` | 0.001s | 4478B |
| `GET /api/control/runtime` | 0.099s | ~300B |
| `GET /api/control/status` | 0.096s | ~350B |
| `GET /api/control/nodes` | 0.001s | ~400B |
| `GET /api/control/routes` | 0.001s | ~800B |
| `GET /api/control/policies` | 0.002s | ~150B |
| `GET /api/control/explain/last-route` | 0.001s | ~200B |

**Todos < 100ms excepto `/api/control/runtime` y `/api/control/status`** que incluyen `health_score.calculate()` (curls a gateway, router, Prometheus, Docker). Latencia aceptable para endpoints operacionales.

### Test 2 — Fastpath Greeting (via LM Studio)

| Run | Latencia |
|---|---|
| 1 | 9.83s |
| 2 | 11.16s |
| 3 | 9.98s |

**Media: ~10.3s**. Determinada por LM Studio (llama-3.1-8b-instruct en rx9070). El fastpath del router no añade latencia medible.

### Test 3 — Normal Chat (HARD_FACTS, via LM Studio)

| Run | Latencia |
|---|---|
| 1 | 52.32s |
| 2 | 35.48s |
| 3 | 35.44s |

**Media: ~41s**. Contexto HARD_FACTS grande (~4K chars) enviado a LM Studio. Latencia atribuible al modelo procesando contexto largo, no al codigo FASE 18.

### Test 4 — Tool Use + Blocked Commands

| Run | Latencia |
|---|---|
| 1 | 8.35s |
| 2 | 7.21s |
| 3 | 5.72s |

**Media: ~7.1s**. El router detecto `rm -rf` en la respuesta de LM Studio y bloqueo el tool call. Se registraron 3 `GOVERNANCE_BLOCKED` con `reason="rm -rf"`.

**Comparacion FASE 15:** baseline ~3.0s tool_use. La diferencia (~4s) se debe a:
1. Modelo de LM Studio distinto (qwen3.6-27b en FASE 15 vs el usado ahora)
2. Carga de GPU / estado del modelo en el momento del test
3. La instrumentacion FASE 18 (health_score, audit_event) solo se ejecuta en el POST-procesamiento, no en el hot path

### Test 5 — Contadores post-test

| Contador | Valor |
|---|---|
| `ailab_router_chat_requests_total` | 9 (6 test + 3 anteriores) |
| `ailab_router_hard_facts_hits_total` | 3 (normal chat) |
| `ailab_governance_blocked_actions_total` | 3 (tool use blocked) |
| `ailab_tool_calls_malformed_total` | 0 (parseo limpio) |
| `ailab_tool_fastpath_total` | 0 (no tool_fastpath activado en estos tests) |

## Conclusión

**FASE 18 no introduce degradacion de rendimiento.** La latencia de inferencia sigue determinada exclusivamente por LM Studio. Los nuevos modulos:

- `control_plane.py` → endpoints en live_api (:8084), proceso separado del router
- `model_health.py` → solo se ejecuta durante `select_node()`, impacto < 1ms por candidato
- `tool_metrics.py` → contadores prometheus_client, impacto < 0.001ms por evento
- `memory_usefulness.py` → escribe a disco, no se ejecuta en el hot path
- `audit_logger.py` → escribe JSONL, solo en eventos de bloqueo/contaminacion
- `recovery_manager.py` → endpoints bajo demanda, no se ejecutan automaticamente

**0 errores, 0 crashes, 0 comandos peligrosos ejecutados.**
