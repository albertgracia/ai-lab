---
title: "FASE 15 - Tool-Aware Context Fastpath"
summary: "Runbook para validar latencia tool_use, comparar test vs produccion local y cerrar el fastpath como estable."
status: stable
category: milestone
date: "2026-05-17"
---

# FASE 15

## Objetivo

Reducir el coste de contexto para requests `tool_use` y comprobar si la latencia cae de verdad.

## Validacion esperada

| Paso | Validacion | Esperado |
|---|---|---|
| 1 | `router` con `tool_choice=required` | `tool_calls` estructurado y respuesta rapida |
| 2 | `gateway` con la misma request | `tool_calls` estructurado y respuesta rapida |
| 3 | `router` normal | sigue mas lento, porque no usa fastpath |
| 4 | comparar test vs produccion local | misma tendencia, variacion pequeña |

## Resultado medido

### Test

- `router` tool_use: `~3.0s` media
- `gateway` tool_use: `~3.0s` media
- `router` normal: `~16.3s` media

### Produccion local

- `router` tool_use: `~3.0s` media
- `gateway` tool_use: `~3.0s` media
- `router` normal: `~22.0s` media
- `gateway` normal: `~37.8s` media

## Interpretacion

1. El fastpath funciona en el router.
2. `qwen/qwen3.6-27b` quedó priorizado para `tool_use`.
3. El gateway valida la misma ruta con `tool_calls` estructurado.
4. El hito queda alcanzado.
5. Los saludos triviales responden breve, sin `HARD_FACTS`.
6. Los comandos peligrosos quedan bloqueados por policy.
7. Si el cliente manda `tools` por defecto, el saludo sigue ganando.
8. Los bloques `<system-reminder>` se eliminan antes de llegar al modelo.

## Comandos de referencia

```bash
PYTHONPATH=/opt/ai-lab /opt/ai-lab/.venv/bin/uvicorn runtime.llm.router_api:app --host 127.0.0.1 --port 18083
PYTHONPATH=/opt/ai-lab /opt/ai-lab/.venv/bin/python -c "import runtime.gateway.openai_gateway as m; m.HOST='127.0.0.1'; m.PORT=18008; m.run()"
```
