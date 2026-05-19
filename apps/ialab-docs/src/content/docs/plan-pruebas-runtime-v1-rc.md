---
title: "Plan de pruebas - AI-LAB v1 RC (HISTORICO)"
summary: "RESULTADOS DE PRUEBAS — AI-LAB v1 RC (marzo 2026). No reflejan el estado actual CP-22B+. Varios bugs aqui documentados ya fueron resueltos en FASEs 20-22. Conservado como referencia historica."
order: 28
---

> **ESTE DOCUMENTO ES HISTORICO — v1 RC (marzo 2026).**
> Bugs resueltos desde entonces:
> - `fast` ahora usa qwen2.5-14b (no llama-3.1-8b) — FASE 20A
> - `reasoning` ahora usa qwen2.5-32b (no 14b) — FASE 20A
> - ProviderModelNotFoundError en OpenCode/Gateway — resuelto FASE 21
> - Empty reply from server en approve command — reemplazado por 428 confirmation gate FASE 22B
> - HARD_FACTS ya no es universal — FASE 20B+20C
> - Plan Mode eliminado — FASE 20B

---## Objetivo

Validar estabilidad, grounding, routing, memoria cognitiva, execute safety y aprendizaje adaptativo del runtime.

## Checklist

| Fase | Test | Estado | Evidencia | Observaciones |
|---|---|---|---|---|
| 1 | Servicios base | ✅ | `ailab-router`, `ailab-live-api`, `ailab-gateway`, `ailab-docs` en `active` | Precheck limpio. |
| 1 | APIs base | ✅ | `GET /health` 200, `GET /api/watchdog` 200, `GET /api/learning/patterns` 200 | JSON valido. |
| 2 | FAST profile en Router / Open WebUI | ✅ | `model=llama-3.1-8b-instruct`, respuesta corta, `prompt_tokens=1573` | Buena latencia y sin inflacion. |
| 2 | CODING profile en Router / Open WebUI | ⚠️ | `model=qwen2.5-coder-14b-instruct` | Respuesta demasiado defensiva: no describio `execute_v1_policy.py` con el detalle esperado. |
| 2 | REASONING profile en Router / Open WebUI | ✅ | `model=qwen2.5-coder-14b-instruct`, incluye `[HARD_FACTS]` e `[INFERIDO]` | Grounding correcto. |
| 2 | Context stress en Router | ✅ | prompt de 100k chars, `prompt_tokens=7749`, 200 OK | Sin 502, truncamiento correcto. |
| 2 | OpenCode / Gateway smoke test | ❌ | `opencode-ialab` falla con `ProviderModelNotFoundError`; `POST /v1/chat/completions` en `:8008` devuelve `400 model_not_found` | El wrapper resuelve `ailab-router/ailab-router/auto` y el gateway intenta `qwen2.5-coder-32b-instruct`. |
| 3 | Propose safe command | ✅ | `POST /api/commands/propose` con `ls /opt/ai-lab` -> `pending` | `id=bdbc507e-712`. |
| 3 | Approve safe command | ❌ | `POST /api/commands/approve?id=bdbc507e-712` devuelve `Empty reply from server` y sigue `pending` | Handler de aprobacion no consolida el cambio. |
| 3 | Reject command | ✅ | `POST /api/commands/reject?id=d2d2ae42-8fe` -> `rejected` | Audit trail correcto. |
| 3 | Blocked command | ✅ | `approve?id=c98de553-ac2` -> `EXECUTE v1 policy blocked: docker` | No ejecuto nada peligroso. |
| 4 | Incident recall | ⚠️ | Prompt: "Ha habido problemas de context overflow anteriormente?" | No habia matches claros; respuesta prudente y corta. |
| 4 | Routing recall | ✅ | Prompt: "Que modelos han dado mejor resultado en reasoning?" | Recupero datos de modelos y contexto. |
| 4 | Recall quality | ✅ | `GET /api/memory/quality?q=high latency&collection=incidents&limit=10` -> `precision=1.0`, `noise=0.0`, `contamination_risk=0.0` | `memory/quality` vive en `:8083`. |
| 4 | Prompt inflation | ✅ | `chars_injected=773` en respuesta de reasoning | Dentro de presupuesto (~500-1500 chars). |
| 5 | Patterns | ✅ | `GET /api/learning/patterns` -> `count=2` | `peak_failure_hour` y `high_latency_model`. |
| 5 | Recommendations | ✅ | `GET /api/learning/recommendations` -> `count=1` | `penalize_model_weight` para `qwen2.5-coder-14b-instruct`. |
| 5 | Context efficiency | ✅ | `samples=30`, `avg_efficiency=5.0`, `pct_good=100%` | Sin ruido absurdo. |
| 5 | Recall threshold | ✅ | `suggested_threshold=0.0`, `expected_precision=1.0`, `expected_noise=0.0` | Coherente con la distribucion actual. |
| 6 | RX7900XT offline | ⏳ | Pendiente de tu ventana para apagar el nodo | No ejecutado aun. |
| 6 | RX7900XT online | ⏳ | Pendiente de tu ventana para reactivar el nodo | No ejecutado aun. |
| 7 | Reboot y persistencia | ✅ | Validado tras corte de suministro inesperado | AI-LAB volvió a levantar completo tras el reboot forzado por apagón. |

## Evidencias clave

- Router API: `http://192.168.1.30:8083/v1/chat/completions`
- Live API: `http://192.168.1.30:8084`
- `memory/quality`: `http://192.168.1.30:8083/api/memory/quality`
- `learning/patterns`: `http://192.168.1.30:8084/api/learning/patterns`

## Resultado actual

Validacion mayormente exitosa, con dos puntos de hardening pendientes y un reboot/persistencia validado tras corte electrico inesperado:

- OpenCode/Gateway sigue resolviendo un modelo invalido para `auto`.
- El handler de aprobacion de comandos no consolida la aprobacion de comandos permitidos.
- El reinicio completo por corte de suministro confirmo persistencia de servicios base y del runtime.
