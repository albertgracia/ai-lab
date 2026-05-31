---
title: "FASE 12.1 — Disciplina de prompting"
summary: "Refuerzo de disciplina semántica en INFERIDO/HARD_FACTS, reglas 11-15, profile en HARD FACTS JSON y DEBUG template dinámico."
order: 28
---

Se detectaron 5 problemas en la autoevaluación del LLM durante el ciclo de auditoría cognitiva:

1. **"no hay inferencias no verificadas"** — falso positivo, el LLM usaba lenguaje inferencial sin marcarlo como tal
2. **`routing_mode: adaptive`** — contradice `adaptive_scoring: NO DISPONIBLE`
3. **`latencia estimada 2.25 ms`** — confunde `node_latency_ms` con `inference_latency_ms`
4. **"motivo REAL"** — afirmación inferida pero etiquetada como REAL
5. **qdrant_recall en DEBUG** — aparecía como número suelto (`5`) sin semántica

## Archivos modificados

| Archivo | Cambio |
|---|---|
| `runtime/llm/router_api.py` | Reglas 11-15 en `build_system_context()`, DEBUG template dinámico |
| `runtime/agent/context_shaper.py` | `profile` inyectado en HARD FACTS JSON, `routing_mode` soportado |
| `runtime/llm/model_router.py` | `mode` añadido al node dict |

## Reglas añadidas

Se añadieron 5 reglas a `build_system_context()` en `router_api.py`:

```
11. Palabras clave (due to, based on, probablemente, etc.) → INFERIDO + self-critique
12. routing_mode solo 'adaptive' si HARD FACTS lo contiene. Valores: primary/fallback
13. latency_ms en GPU nodes = latencia de red, NO de inferencia
14. Afirmaciones con "REAL" deben tener fuente explícita en HARD FACTS
15. "REAL" solo si existe literalmente en HARD FACTS o routing.reason_codes
```

## DEBUG template

**Antes**: template hardcodeado con `NO DISPONIBLE` para todo.
```
[AI-LAB DEBUG] task model node context_size:NO DISPONIBLE budget_used:NO DISPONIBLE
adaptive_scoring:NO DISPONIBLE working_memory:NO DISPONIBLE
qdrant_enabled:NO DISPONIBLE watchdog:NO DISPONIBLE health:NO DISPONIBLE
```

**Ahora**: template dinámico que instruye al LLM a poblar desde HARD FACTS.
```
[AI-LAB DEBUG] profile=<profile del JSON>, task=<inferido de la solicitud>,
model=<model_id>, node=<node_name>, budget_used=<del sistema>,
adaptive_scoring=<si en HARD FACTS>, working_memory=<si en HARD FACTS>,
qdrant_recall=<matches, collections, chars del semantic_recall en JSON>,
watchdog=<health.watchdog>, health=<health.score>
```

## profile en HARD FACTS JSON

El campo `profile` (task_type: reasoning/coding/fast) ahora se inyecta en el JSON de HARD FACTS vía `_hard_extra` en `context_shaper.py`. El LLM puede referenciarlo sin inferirlo.

## routing_mode en HARD FACTS JSON

El modo de enrutamiento (primary/fallback) ahora se incluye como `routing.mode` en el JSON de HARD FACTS. Se obtiene de `task_router.select_node()` en lugar de ser inferido por el LLM.

## Commit

```
8e78dce fix: prompt discipline rules 15, profile in HARD FACTS, qdrant_recall estructura
```
