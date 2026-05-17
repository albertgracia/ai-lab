---
title: "Plan de pruebas - AI-LAB Cognitive Operations Runtime v1 RC"
summary: "Runbook de validacion operativa para grounding, routing, memoria, execute safety y aprendizaje adaptativo."
status: stable
category: operations
date: "2026-05-17"
---

# Plan de pruebas

## Objetivo

Validar estabilidad, grounding, routing, memoria cognitiva, execute safety y aprendizaje adaptativo del runtime.

## Checklist operativa

| Fase | Test | Estado | Evidencia | Observaciones |
|---|---|---|---|---|
| 1 | Servicios base | ✅ | `active` en los 4 servicios | Precheck limpio. |
| 1 | APIs base | ✅ | `200 OK` y JSON valido | `health`, `watchdog`, `learning/patterns`. |
| 2 | FAST profile | ✅ | `model=llama-3.1-8b-instruct` | Respuesta corta y razonable. |
| 2 | CODING profile | ⚠️ | `model=qwen2.5-coder-14b-instruct` | Falto detalle sobre `execute_v1_policy.py`. |
| 2 | REASONING profile | ✅ | `[HARD_FACTS]` + `[INFERIDO]` | Buena separacion de contexto. |
| 2 | Context stress | ✅ | `100000` chars, `prompt_tokens=7749` | Sin 502, truncamiento correcto. |
| 2 | OpenCode / Gateway | ❌ | `opencode-ialab` y `:8008` fallan para `auto` | Mapeo de modelo invalido. |
| 3 | Propose safe command | ✅ | Proposal `pending` creada | `ls /opt/ai-lab`. |
| 3 | Approve safe command | ❌ | `Empty reply from server` | No pasa a `executed`. |
| 3 | Reject | ✅ | `status=rejected` | Correcto. |
| 3 | Blocked command | ✅ | Bloqueo de `docker` por policy | Sin ejecucion. |
| 4 | Incident recall | ⚠️ | Respuesta prudente | Sin match claro de context overflow. |
| 4 | Routing recall | ✅ | Modelo y contexto recuperados | Coherente. |
| 4 | Recall quality | ✅ | `precision=1.0`, `noise=0.0` | `:8083`. |
| 4 | Prompt inflation | ✅ | `chars_injected=773` | Dentro de presupuesto. |
| 5 | Patterns | ✅ | `count=2` | Patrones reales. |
| 5 | Recommendations | ✅ | `count=1` | `penalize_model_weight`. |
| 5 | Context efficiency | ✅ | `30 samples`, `100% good` | Coherente. |
| 5 | Recall threshold | ✅ | `suggested_threshold=0.0` | Sin ruido. |
| 6 | RX7900XT offline | ⏳ | Pendiente | Ejecutar luego. |
| 6 | RX7900XT online | ⏳ | Pendiente | Ejecutar luego. |
| 7 | Reboot y persistencia | ✅ | Ya verificado | Persistencia real ya validada. |

## Hallazgos

- `opencode-ialab` no arranca con el modelo actual de `ailab-router`.
- El endpoint de aprobacion de comandos no consolida ejecuciones permitidas.
- El resto del stack responde y mantiene presupuestos de contexto correctos.
