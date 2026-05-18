---
title: "FASE 20C — Normalizacion de Prompts Runtime"
summary: "Extraccion de prompts hardcoded a archivos versionados y declarativos en runtime/prompts/. Loader con validacion de wrappers prohibidos y fallback legacy."
order: 43
---

## Hito

Se completo la normalizacion de prompts del runtime AI-LAB. Todos los prompts de sistema estan ahora en archivos `.md` versionados bajo `runtime/prompts/`, cargados por un loader centralizado con validacion de wrappers prohibidos.

## Estructura

```
runtime/prompts/
├── manifest.json           # Mapeo route_family → prompt file + marcadores prohibidos
├── prompt_loader.py        # Loader unico con validacion
├── minimal_prompt.md       # Para minimal/casual/greeting/report
├── chat_prompt.md          # Para fast/general/chat
├── coding_prompt.md        # Para coding
├── reasoning_prompt.md     # Para reasoning
├── observe_prompt.md       # Para observe
└── tool_use_prompt.md      # Para tool_use/tool_fastpath
```

## Loader (`prompt_loader.py`)

| Funcion | Descripcion |
|---------|-------------|
| `load_prompt(name)` | Carga un .md desde disco, cachea en memoria |
| `get_prompt_name(route_family, capability)` | Resuelve que archivo usar segun ruta |
| `get_prompt_for_route(route_family, capability)` | Carga + valida, devuelve (texto, warnings) |
| `validate_prompt(text, route_key)` | Busca marcadores prohibidos definidos en manifest |

## Validacion de wrappers prohibidos

El loader rechaza marcadores legacy en rutas no cognitivas:

| Ruta | Marcadores bloqueados |
|------|----------------------|
| minimal | HARD_FACTS, follow_ups, Plan Mode, CRITICAL, STRICTLY FORBIDDEN, reasoning_content, tool_calls, FORMATO OBLIGATORIO |
| chat | HARD_FACTS, follow_ups, Plan Mode, CRITICAL, STRICTLY FORBIDDEN, FORMATO OBLIGATORIO |
| coding | HARD_FACTS, follow_ups, Plan Mode, CRITICAL, STRICTLY FORBIDDEN |
| observe | HARD_FACTS, follow_ups, Plan Mode, CRITICAL, STRICTLY FORBIDDEN, reasoning_content, tool_calls, FORMATO OBLIGATORIO |

## Integracion

### Router API (`runtime/llm/router_api.py`)

El loader se usa en la rama `else` (cognitive) para `fast`/`general`. Si falla, usa el prompt legacy como fallback.

### Gateway (`runtime/gateway/openai_gateway.py`)

El loader se usa en `inject_agent_context()` para la rama `else` (cognitive/general). Si falla, usa `load_agent_prompt()` como fallback.

## Que NO se toco

- Prompts de `minimal/casual/greeting/observe` (ya estaban limpios)
- Prompts de `reasoning` y `tool_use` (mantienen comportamiento)
- `build_system_context()` (se usa como fallback para reasoning)

## Validacion

| Prueba | Modelo | Prompt tokens | Resultado |
|--------|--------|--------------|-----------|
| minimal "hola" | llama-3.1-8b | 64 | texto natural |
| general "que es docker" | qwen2.5-14b | 90 | contenido real, sin wrappers |
| casual "que puedes hacer" | llama-3.1-8b | 69 | texto natural |
| observe | llama-3.1-8b | 150 | resumen correcto |

La ruta general bajo de ~635 a ~90 prompt tokens al usar el prompt declarativo en vez de `load_agent_prompt()`.

## Rollback

```bash
cp /opt/ai-lab/snapshots/fase20c-backup/router_api.py /opt/ai-lab/runtime/llm/
cp /opt/ai-lab/snapshots/fase20c-backup/openai_gateway.py /opt/ai-lab/runtime/gateway/
sudo systemctl restart ailab-router ailab-gateway
```

## Siguiente fase

FASE 21 — Perfiles cognitivos: CHAT, CODING, AGENT, ANALYSIS, OBSERVE con prompts aislados.
