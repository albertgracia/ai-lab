---
title: "FASE 25 — OpenCode Production Profile"
summary: "Perfil de produccion para OpenCode: developer-first, sin Plan Mode, sin HARD_FACTS automatico, single ingress al router, guard duro contra tool_use y wrappers."
order: 50
---

## Hito

Se completo el perfil de produccion para OpenCode. Ahora OpenCode usa el AI-LAB Router como unico entrypoint, con protecciones explicitas contra tool_use accidental, HARD_FACTS no solicitado y wrappers internos.

## Principio

> **Separar "developer runtime" de "cognitive runtime".** OpenCode no debe sentirse como "estoy hablando con el runtime" sino como "tengo un coding assistant rapido".

## Cambios

### Config files limpiados

| Archivo | Cambio |
|---------|--------|
| `OPENCODE.md` | Reescrito: sin Plan Mode, sin HARD_FACTS, developer-first |
| `~/.config/opencode/opencode.jsonc` | Provider `lm` eliminado. Single ingress = AI-LAB Router |
| `opencode.ialab.memory.json` | Provider `lmstudio` disabled. Solo `ailab-router` |
| `runtime/prompts/opencode_prompt.md` | Nuevo: prompt limpio para desarrollo |

### Guard duro (router + gateway)

Ejecutado **ANTES** del clasificador general:

1. **Strip question tool** — siempre, no configurable
2. **No tool_use sin tools explicitas** — si no hay tools en el payload, se eliminan `tool_choice` y `tools`
3. **Suppress HARD_FACTS** — solo si el usuario pide explicitamente: razonamiento, auditoria, arquitectura, debug profundo
4. **Metadatos de replay** — `_client_profile: opencode`, `_wrapper_suppressed: true`

### Rutas explicitas en manifest_profiles.json

```json
{
  "opencode_minimal": "observe_profile.json",
  "opencode_chat": "chat_profile.json",
  "opencode_coding": "coding_profile.json",
  "opencode_reasoning": "analysis_profile.json"
}
```

## Validacion

| Escenario | Resultado |
|-----------|-----------|
| "hola" + tools (question, bash) | llama-3.1-8b, 64 tokens, tools eliminadas |
| "escribe un script python" | coding, qwen2.5-14b, sin HARD_FACTS |
| "analiza la arquitectura" | reasoning, con HARD_FACTS |
| "hola" sin tools | minimal/observe |

## Lo que NO se toco

- Router, gateway (solo se anadio guard, no se refactorizo)
- Politicas de tools, politicas de memoria
- `manifest_memory.json`, `manifest_tools.json`
- `profile_loader.py`, `model_router.py`

## Rollback

```bash
cp /opt/ai-lab/snapshots/fase25-backup/* /opt/ai-lab/
sudo systemctl restart ailab-router ailab-gateway
```

## Siguiente fase

FASE 26 — OpenWebUI Production Profile
