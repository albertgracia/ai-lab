---
title: "FASE 29.3 — Three-Model Runtime Simplification"
summary: "Simplificación del runtime a 3 modelos estables: llama-3.1-8b para tareas ligeras, qwen2.5-coder-14b para coding/report/reasoning, y nomic-embed para embeddings. qwen3.6-27b desactivado."
order: 70
---

## Objetivo

Simplificar AI-LAB a 3 modelos estables, eliminando qwen3.6-27b del runtime activo para reducir presión de VRAM, cache churn y latencia.

## Modelos activos

| Modelo | Uso | VRAM |
|--------|-----|------|
| **llama-3.1-8b-instruct** | minimal, greetings, observe, report_light | ~6GB |
| **qwen2.5-coder-14b-instruct** | coding, report_heavy, creative, reasoning, analysis | ~10GB |
| **text-embedding-nomic-embed-text-v1.5** | embeddings, semantic recall, RAG | ~1GB |

## Modelo desactivado

**qwen3.6-27b** — desactivado (FASE 29.3). Razones:
- Aumenta presión de VRAM (~16GB solo él)
- Genera cache churn compitiendo con qwen2.5-14b
- Incrementa latencia media
- No es necesario para los objetivos actuales
- qwen2.5-14b cubre coding/report/reasoning suficientemente

El modelo NO se borra del disco. Queda disponible para pruebas manuales futuras.

## Cambios realizados

| Archivo | Cambio |
|---------|--------|
| `model_registry.py` | `enabled: False` en entrada qwen3.6-27b + filtro en `get_best_model()` |
| `capability_router.py` | Eliminado de `MODEL_CAPABILITIES` |
| `token_router.py` | Eliminado de 3 `TASK_MODEL_PREFERENCES` + `infer_model_capabilities()` |
| `model_classifier.py` | Eliminado de `_TOOL_USE_MARKERS` |
| `agent_profile.json` | `default` → `qwen2.5-coder-14b-instruct` |
| `manifest_profiles.json` | `tool_use` → `chat_profile.json` |
| `openai_gateway.py` | Hard guard anti-qwen3.6 con redirect + métrica |
| `prometheus_metrics.py` | Nueva métrica `ailab_disabled_model_selection_total` |
| `profile_manifest_state.json` | `model_set: "29.3-three-model-runtime"` |

## Hard guard

```python
DISABLED_MODELS = {"qwen3.6-27b", "qwen/qwen3.6-27b", "lmstudio-community/qwen3.6-27b"}
if selected_model in DISABLED_MODELS or "qwen3.6" in (selected_model or "").lower():
    selected_model = "qwen2.5-coder-14b-instruct"
    record_disabled_model_selection(original, "disabled_model_redirect")
```

## Burn-in

57 requests, 3 workers concurrentes, 10 minutos, **0 usos de qwen3.6-27b**.

## Beneficios

- Menos presión VRAM (2 modelos compitiendo en vez de 3)
- Menos cache churn
- Routing más predecible
- Menor latencia media
- Base más estable antes de scheduler multi-GPU
