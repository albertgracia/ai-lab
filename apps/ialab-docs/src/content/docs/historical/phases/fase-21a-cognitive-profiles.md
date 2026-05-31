---
title: "FASE 21A — Cognitive Profiles (Profile Loader + Routing)"
summary: "Introduccion de perfiles cognitivos como policy bundles declarativos. Cada perfil define modelo, inferencia, tools, memoria, razonamiento y streaming. Jerarquia: cliente > perfil > sistema."
order: 44
---

## Hito

Se completo la FASE 21A: introduccion del sistema de perfiles cognitivos como **policy bundles** declarativos en `runtime/profiles/`. El loader aplica los parametros del perfil a cada peticion sin machacar overrides explicitos del cliente.

## Arquitectura

```
runtime/profiles/
├── manifest_profiles.json   # Mapeo route_family -> perfil + overrides
├── profile_loader.py        # Loader unico con apply_profile()
├── chat_profile.json        # Chat conversacional (fast/general)
├── coding_profile.json      # Programacion
├── analysis_profile.json    # Analisis profundo (reasoning)
├── observe_profile.json     # Observacion ligera (minimal/casual/greeting/observe)
└── agent_profile.json       # Operativo con herramientas (tool_use)
```

## Perfiles

| Perfil | Modelo | max_tokens | temp | Tools | Memory | Reasoning |
|--------|--------|------------|------|-------|--------|-----------|
| chat | qwen2.5-14b | 512 | 0.4 | NO | light | disabled |
| coding | qwen2.5-14b | 1024 | 0.2 | NO | light | disabled |
| analysis | qwen2.5-32b | 2048 | 0.3 | NO | full | enabled |
| observe | llama-3.1-8b | 256 | 0.1 | NO | minimal | disabled |
| agent | qwen3.6-27b | 2048 | 0.2 | SI | full | enabled |

## Overrides para rutas ligeras

`minimal`, `casual`, `greeting` y `report` usan `observe_profile.json` con override `max_tokens: 96`.

## Jerarquia de prioridad

```
cliente explicito > perfil cognitivo > default del sistema
```

- Si el cliente manda `max_tokens: 32`, se respeta.
- Si el cliente manda `temperature: null`, se usa el default del perfil.
- Si el cliente manda `tools`, se respetan solo si el perfil lo permite (agent).

## Loader API

| Funcion | Descripcion |
|---------|-------------|
| `load_profile(name)` | Carga un .json de perfil |
| `get_profile_for_route(route_family)` | Resuelve ruta -> perfil con overrides |
| `apply_profile(payload, route_family)` | Aplica perfil al payload, inyecta metadatos |

## Metadatos de observabilidad

Cada payload recibe:

- `_profile` = nombre del perfil aplicado (`"chat"`, `"coding"`, etc.)
- `_profile_version` = version del perfil (`"21.1"`)

Para futura observabilidad por perfil en Grafana.

## Integracion

### Router API

`apply_profile()` se llama justo despues de `classify_chat_route()`, antes de los bloques `if/elif`. Si el loader falla, se continua con el comportamiento legacy.

### Gateway

Igual que en router: `apply_profile()` en `inject_agent_context()` tras `classify_chat_route()`.

## Que NO se toco

- Logica legacy de `if/elif` en router y gateway (se preserva como fallback)
- `runtime/prompts/` (FASE 20C)
- `runtime/profiles/sandbox.py`, `pilot.py`, etc. (perfiles de seguridad)
- `runtime/modes/` (modos operacionales)
- `runtime/memory/` (recall)

## Validacion

| Ruta | Modelo | Funciona |
|------|--------|----------|
| minimal "hola" | llama-3.1-8b | SI |
| casual "que puedes hacer" con tools | llama-3.1-8b | SI |
| general "que es docker" | qwen2.5-14b | SI |
| observe | llama-3.1-8b | SI |

## Rollback

```bash
cp /opt/ai-lab/snapshots/fase21a-backup/router_api.py /opt/ai-lab/runtime/llm/
cp /opt/ai-lab/snapshots/fase21a-backup/openai_gateway.py /opt/ai-lab/runtime/gateway/
sudo systemctl restart ailab-router ailab-gateway
```

## Siguiente fase

FASE 21B — Eliminacion progresiva de hardcodes legacy, reemplazados por el profile loader.
