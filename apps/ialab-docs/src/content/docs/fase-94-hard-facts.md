---
title: "FASE 9.4 — HARD FACTS Engine y Control de Contexto"
summary: "Generación de contexto en vivo, truncamiento inteligente, limpieza de archivos obsoletos."
order: 19
---

El motor **HARD FACTS** es el sistema que inyecta datos reales del runtime
AI-LAB en el system prompt de cada inferencia. Su objetivo es doble:

1. **Eliminar alucinaciones** — el modelo solo recibe datos verificables
2. **Reducir el tamaño del prompt** — solo la información necesaria

## Problema resuelto

El router API enviaba a LM Studio el **historial completo de la conversación**
de OpenCode (incluyendo tool results con archivos enteros), acumulando hasta
**476.000 tokens** para un modelo cargado con **n_ctx=16.384**.
Resultado: error `n_keep >= n_ctx` y respuesta 502.

## Cambios principales

### 1. `runtime/llm/router_api.py` — Truncamiento por presupuesto

- **`get_last_user_message()`** — extrae solo el último mensaje del usuario,
  ignorando historial de assistant, tool results y system messages que
  OpenCode ya gestiona por su cuenta.
- **`truncate_text()`** — corta el texto en el último espacio antes del
  límite de caracteres, sin romper palabras.
- **Cálculo de presupuesto**: `(LM_STUDIO_MAX_CONTEXT - OVERHEAD) × 2.8 chars/token - system_prompt`
- **Garantía**: nunca se envía un prompt que exceda `n_ctx=16384`.

### 2. `runtime/agent/context_shaper.py` — HARD FACTS en vivo

La función `_build_hard_facts()` se reescribió para consultar **12 fuentes
de datos**, todas dentro de `try/except` para aislamiento de fallos:

| Sección | Fuente | Datos |
|---|---|---|
| GPU NODES | `cluster_state.json` + `inference_nodes.json` | Nombre, IP, estado, VRAM, modelos cargados |
| SYSTEM RESOURCES | `free`, `df`, `uptime`, `/proc/loadavg`, `docker ps` | RAM, disco, uptime, load, contenedores |
| DOCKER CONTAINERS | `docker ps --format json` | 16 containers con nombre, imagen, puertos |
| SYSTEMD SERVICES | `systemctl list-units ailab-*` | 8 servicios con estado activo |
| CLUSTER HEALTH | `:8084/api/analytics` | Score, razones, requests, errores, nodos |
| WATCHDOG | `:8084/api/watchdog` | 6 checks de salud |
| MODEL PERFORMANCE | `:8084/api/model-performance` | Requests, success rate, PI por modelo |
| ROUTING HISTORY | `routing_history.jsonl` | Total de rutas registradas |
| ROUTER MODELS | Hardcoded | 4 modelos del router |
| SITES | Config | URLs público y privado |
| MAINTENANCE | `maintenance_nodes.json` | Nodos en mantenimiento |
| FORBIDDEN | Hardcoded | Referencias prohibidas |

### 3. Límite efectivo de contexto

`context_shaper.py` ahora forza `_EFFECTIVE_MAX_CONTEXT = 16384`,
independientemente del valor declarado en `MODEL_REGISTRY` para cada modelo.

### 4. Limpieza de archivos de contexto

Tres archivos fueron limpiados para redirigir al HARD FACTS como fuente
de verdad única para datos de infraestructura:

- **`AI_LAB_CONTEXT.md`** — eliminada la sección Environment con IPs y
  servicios obsoletos. Ahora solo contiene directrices de comportamiento.
- **`MODEL_STRATEGY.md`** — eliminados modelos concretos desactualizados
  (`gemma-4-e4b`, `moondream2`, `flux.2-klein-9b`). Redirige al registry
  y al HARD FACTS para conocer los modelos realmente cargados.
- **`OPENCODE.md`** — eliminadas referencias a roadmaps y archivos
  inexistentes. Simplificado a instrucciones de comportamiento.

## Arquitectura

```
OpenCode
  │ POST /v1/chat/completions (solo último mensaje usuario)
  ▼
Router API (:8083)
  │
  ├── shape_context(task, model)
  │     ├── _build_hard_facts()  ← datos en vivo
  │     └── source files (limpios, redirigen a HARD FACTS)
  │
  ├── system_prompt = BASE + agent_context[:6000]
  ├── budget = (16384 - 500) × 2.8 - len(system_prompt)
  ├── final_instruction = truncate(user_text, budget)
  │
  ▼
LM Studio (RX9070:1234, n_ctx=16384)
  ✓ prompt siempre dentro del límite
```

## Verificación

```bash
# Test básico
curl -X POST http://192.168.1.30:8083/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"ailab-router/auto","messages":[{"role":"user","content":"estado del cluster"}],"max_tokens":200}'

# Test con contexto grande (500K chars)
python3 -c "
import requests
resp = requests.post('http://192.168.1.30:8083/v1/chat/completions',
  json={'model': 'ailab-router/auto',
        'messages': [{'role': 'user', 'content': 'A' * 500_000}],
        'max_tokens': 10})
print(resp.json()['usage']['prompt_tokens'])  # Debe ser < 16384
"
```

## Archivos modificados

- `runtime/llm/router_api.py` — truncamiento, `get_last_user_message()`, `truncate_text()`
- `runtime/agent/context_shaper.py` — `_build_hard_facts()` reescrito, `EFFECTIVE_MAX_CONTEXT`
- `config/opencode/AI_LAB_CONTEXT.md` — limpiado
- `config/opencode/MODEL_STRATEGY.md` — limpiado
- `OPENCODE.md` — limpiado
