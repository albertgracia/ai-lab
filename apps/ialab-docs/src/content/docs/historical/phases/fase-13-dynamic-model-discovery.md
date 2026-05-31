---
title: "FASE 13 - Dynamic Model Discovery for AI-LAB Auto Router"
summary: "Hito de descubrimiento dinámico de modelos en LM Studio para eliminar dependencias fijas en el auto router."
order: 29
---

## Hito

AI-LAB deja de depender de nombres fijos para enrutar modelos. El router ahora puede descubrir modelos reales en cada nodo LM Studio, clasificar candidatos desconocidos y aplicar fallback seguro si el discovery falla.

## Alcance implementado

- `runtime/models/model_discovery.py`
- `runtime/models/model_classifier.py`
- extensiones en `runtime/models/model_registry.py`
- `runtime/llm/model_router.py`
- `runtime/llm/router_api.py`
- `runtime/agent/context_shaper.py`
- `runtime/state/live_api.py`
- ajuste del wrapper `runtime/opencode_ialab.sh`

## Comportamiento nuevo

- consulta `GET /v1/models` en cada nodo LM Studio
- normaliza y clasifica modelos por heurística cuando no existen en el registry
- evita embeddings y vision en rutas de chat normales
- detecta modelos `tool_use` y prioriza esos candidatos cuando la request trae `tools` o `tool_choice`
- prioriza modelo real por tarea, disponibilidad y performance histórica
- expone `model_discovery`, `selected_model` y `reason_codes` en HARD FACTS

## Evidencias

| Verificacion | Resultado |
|---|---|
| `GET /api/models/discovery` | discovery cache con 2 nodos online y 9 modelos |
| `GET /api/models/catalog` | catalogo unificado registry + discovery |
| `ailab-router/fast` | `llama-3.1-8b-instruct` cuando el prompt es corto y el matcher entra en `fast` |
| `ailab-router/coding` | `qwen2.5-coder-14b-instruct` o `qwen2.5-coder-32b-instruct` segun discovery y scoring |
| `ailab-router/reasoning` | `qwen2.5-coder-32b-instruct` en `rx7900xt` |

## Validacion operativa adicional

- `rx9070` pudo caer a offline y el router mantuvo servicio con fallback.
- Al volver `rx9070`, discovery volvio a ver los dos nodos y los modelos cargados.
- `qwen2.5-coder-14b-instruct` se detecto en `rx7900xt` y quedo disponible para rutas de coding/fallback.

## Commit

`994c989c feat: FASE 13 - dynamic LM Studio model discovery for auto router`
