---
title: "FASE 13 - Dynamic Model Discovery"
summary: "Runbook operativo para validar discovery de modelos LM Studio, routing adaptativo y HARD FACTS enriquecidos."
status: stable
category: milestone
date: "2026-05-17"
---

# FASE 13

## Objetivo

Eliminar la dependencia de nombres de modelo fijos en el Auto Router.

## Check operativo

| Paso | Validacion | Estado | Evidencia |
|---|---|---|---|
| 1 | Discovery cache | ✅ | `GET /api/models/discovery` |
| 2 | Refresh discovery | ✅ | `GET /api/models/discovery/refresh` |
| 3 | Catalogo de modelos | ✅ | `GET /api/models/catalog` |
| 4 | Fast routing | ✅ | usa `llama-3.1-8b-instruct` |
| 5 | Coding routing | ✅ | usa `qwen2.5-coder-14b-instruct` o `qwen2.5-coder-32b-instruct` segun discovery |
| 6 | Reasoning routing | ✅ | usa `qwen2.5-coder-32b-instruct` |
| 7 | HARD FACTS | ✅ | incluye `model_discovery`, `selected_model` y `reason_codes` |

## Fallbacks confirmados

- si discovery falla, el router cae al registry actual
- si un nodo no responde, queda marcado como offline/degraded
- si el modelo no existe en el registry, se clasifica por heuristica
- si nada encaja, se usa el fallback fast seguro

## Resultado

FASE 13 documentada y validada en el runtime.

## Validacion extendida

- `rx9070` offline no rompe el router; el fallback cae a `rx7900xt`.
- `qwen2.5-coder-14b-instruct` en `rx7900xt` queda visible tras refresh.
- El matcher de intencion se alineo con el gateway para evitar divergencias entre `fast`, `coding` y `reasoning`.
- Los prompts con `tools` o `tool_choice` ya pueden priorizar modelos `tool_use` descubiertos en vivo.

## Nota de validacion

La validacion final del reboot/persistencia se produjo tras un corte de suministro electrico inesperado.
