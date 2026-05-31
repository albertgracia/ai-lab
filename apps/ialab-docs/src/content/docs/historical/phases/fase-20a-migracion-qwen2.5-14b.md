---
title: "FASE 20A — Migracion del AI-LAB Router a qwen/qwen2.5-coder-14b-instruct"
summary: "Migracion controlada del modelo principal del runtime AI-LAB hacia qwen/qwen2.5-coder-14b-instruct como modelo por defecto para fast, general y coding, manteniendo llama-3.1-8b para rutas minimal/casual/greeting/observe."
order: 40
---

## Hito

Se completo la migracion del modelo por defecto del AI-LAB Router hacia `qwen/qwen2.5-coder-14b-instruct` para las rutas `fast`, `general` y `coding`. Las rutas ligeras (`minimal`, `casual`, `greeting`, `observe`) mantienen `llama-3.1-8b-instruct`.

## Routing resultante

| Ruta | Modelo FASE 19 | Modelo FASE 20A |
|------|---------------|-----------------|
| `minimal/casual` | llama-3.1-8b | llama-3.1-8b (sin cambio) |
| `minimal/greeting` | llama-3.1-8b | llama-3.1-8b (sin cambio) |
| `minimal/report` | llama-3.1-8b | llama-3.1-8b (sin cambio) |
| `observe` | llama-3.1-8b | llama-3.1-8b (sin cambio) |
| `fast` | llama-3.1-8b | **qwen2.5-coder-14b** |
| `general` | llama-3.1-8b | **qwen2.5-coder-14b** |
| `coding` | qwen2.5-coder-14b | qwen2.5-coder-14b (sin cambio) |
| `reasoning` | qwen2.5-coder-32b | qwen2.5-coder-32b (sin cambio) |
| `tool_use` | qwen3.6-27b | qwen3.6-27b (sin cambio) |

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `runtime/llm/model_router.py` | `DEFAULT_MODELS`: fast y general pasan de llama-3.1-8b a qwen2.5-coder-14b. Fallback final tambien actualizado. |
| `runtime/router/capability_router.py` | `MODEL_CAPABILITIES`: entrada nueva para qwen2.5-coder-14b. Fallback fast/coding a 14b. |
| `runtime/llm/router_api.py` | Fallback ante Model unloaded a qwen2.5-14b. Protecciones: pop de reasoning/tools/tool_choice para qwen2.5-14b. |
| `runtime/models/model_registry.py` | qwen2.5-coder-14b: skills +fast/general/chat, scores speed 6->9, memory 6->8. |
| `config/inference_nodes.json` | `fast.model_id` en rx9070 cambia a qwen2.5-coder-14b. |

## Configuracion LM Studio

| Parametro | Valor |
|-----------|-------|
| Endpoint | `http://192.168.1.50:1234/v1` |
| Modelo principal | `qwen/qwen2.5-coder-14b-instruct` |
| Temperature | 0.2 |
| Top P | 0.95 |
| Min P | 0.05 |
| Context Window | 8192 (max 12288) |
| Thinking | OFF |
| Structured Output | OFF |

## Protecciones para qwen2.5-14b

En `router_api.py` se anadieron guardas explicitas cuando el modelo seleccionado es qwen2.5-coder-14b:

```python
if "qwen2.5-coder-14b" in str(upstream_payload.get("model", "")):
    upstream_payload.pop("reasoning", None)
    upstream_payload.pop("tool_choice", None)
    upstream_payload.pop("tools", None)
```

Esto evita que wrappers automaticos de reasoning o tool calling contaminen el payload hacia LM Studio.

## Validacion

| Prueba | Resultado |
|--------|-----------|
| `minimal` (hola) | llama-3.1-8b-instruct |
| `fast` (no greeting) | qwen/qwen2.5-coder-14b-instruct |
| `general/auto` | qwen/qwen2.5-coder-14b-instruct |
| `coding` | qwen/qwen2.5-coder-14b-instruct |
| LM Studio directo | Responde correctamente |

## Rollback

```bash
cp /opt/ai-lab/snapshots/fase20a-backup/* /opt/ai-lab/runtime/llm/
cp /opt/ai-lab/snapshots/fase20a-backup/inference_nodes.json /opt/ai-lab/config/
sudo systemctl restart ailab-router
```

## Siguiente fase

FASE 20B — Limpieza runtime prompts: remover wrappers legacy, HARD_FACTS automaticos, y Plan Mode de rutas no cognitivas.
