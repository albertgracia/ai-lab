---
title: "FASE 20B — Limpieza de Wrappers Legacy en Rutas No Cognitivas"
summary: "Eliminacion de HARD_FACTS automaticos, Plan Mode, reasoning wrappers, structured JSON y tool forcing de las rutas fast, general y coding. Las rutas reasoning y tool_use mantienen su comportamiento."
order: 41
---

## Hito

Se completo la limpieza defensiva de wrappers legacy en las rutas no cognitivas del AI-LAB Router y Gateway. Las rutas `fast`, `general` y `coding` ahora responden con texto natural, sin HARD_FACTS forzado, sin Plan Mode, sin reasoning wrappers y sin tool forcing.

## Cambios aplicados

### Router API (`runtime/llm/router_api.py`)

| Cambio | Efecto |
|--------|--------|
| `build_system_context()` solo se usa en `reasoning` | fast/general/coding usan prompt ligero |
| `final_instruction` simplificado para fast/general | Sin formato obligatorio de secciones |
| Inyeccion de `reasoning={"effort":"none"}` solo para reasoning | fast/general/coding no reciben wrapper |
| Proteccion qwen2.5-14b: pop de reasoning/tools/tool_choice | Mantenida de FASE 20A |

### Gateway (`runtime/gateway/openai_gateway.py`)

| Cambio | Efecto |
|--------|--------|
| `max_tokens` no machaca rutas minimal/observe | Las rutas ligeras respetan su max_tokens original |
| Prioridad `route_family` sobre `task_type` en modelo | minimal/observe gana a fast/general |
| `task_type` fast/general/coding fuerza qwen2.5-14b | Coherente con FASE 20A |

## Routing final (FASE 20A + 20B)

| Ruta | Modelo | HARD_FACTS | Wrappers |
|------|--------|-----------|----------|
| `minimal/casual` | llama-3.1-8b | NO | NO |
| `minimal/greeting` | llama-3.1-8b | NO | NO |
| `minimal/report` | llama-3.1-8b | NO | NO |
| `observe` | llama-3.1-8b | NO | NO |
| `fast` | qwen2.5-14b | NO | NO |
| `general` | qwen2.5-14b | NO | NO |
| `coding` | qwen2.5-14b | NO | NO |
| `reasoning` | qwen2.5-32b | SI | SI (controlado) |
| `tool_use` | qwen3.6-27b | SI | SI (controlado) |

## Que NO se toco

- Routing de modelos (FASE 20A)
- Seleccion de agentes
- Memoria semantica
- Perfiles CHAT/AGENT (FASE 21)
- Workflows
- Observabilidad

## Validacion

| Prueba | Modelo | Resultado |
|--------|--------|-----------|
| casual "que puedes hacer" con tools | llama-3.1-8b | texto natural, sin tools |
| general "que es docker" | qwen2.5-14b | contenido real, sin wrappers |
| minimal "hola" | llama-3.1-8b | respuesta breve |

## Rollback

```bash
cp /opt/ai-lab/snapshots/fase20b-backup/* /opt/ai-lab/runtime/llm/
cp /opt/ai-lab/snapshots/fase20b-backup/openai_gateway.py /opt/ai-lab/runtime/gateway/
sudo systemctl restart ailab-router ailab-gateway
```

## Siguiente fase

FASE 21 — Perfiles CHAT/AGENT/ANALYSIS/CODING con payload builders aislados.
