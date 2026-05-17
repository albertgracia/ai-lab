---
title: "FASE 14 - Tool-Use Router API"
summary: "Runbook para validar routing tool-aware y conversion de tool calls OpenAI-native."
status: stable
category: milestone
date: "2026-05-17"
---

# FASE 14

## Objetivo

Permitir que AI-LAB Router API detecte requests con herramientas y traduzca las salidas de LM Studio a `tool_calls` validos.

## Check operativo

| Paso | Validacion | Estado | Evidencia |
|---|---|---|---|
| 1 | Requests con `tools` | ✅ | se detectan como `tool_use` |
| 2 | Prioridad tool-aware | ✅ | `qwen/qwen3.6-35b-a3b` en el nodo adecuado |
| 3 | Bridge de tool call | ✅ | `<tool_call>` -> `tool_calls` |
| 4 | Content final | ✅ | `content=null` cuando hay tool call |
| 5 | Streaming | ✅ | sanitizador conserva el bridge |

## Pruebas reales

### RX9070

- modelo: `qwen/qwen3.6-27b`
- `tool_choice=required`
- emite `<tool_call><function=noop></function></tool_call>`
- latencia media aproximada: `2.4s`

### RX7900XT

- modelo: `qwen/qwen3.6-35b-a3b`
- `tool_choice=required`
- emite `<tool_call><function=noop></function></tool_call>`
- latencia media aproximada: `0.37s`

## Resultado

La FASE 14 queda validada: el router y el gateway ya son tool-aware y devuelven tool calls estructurados.

## Nota de rendimiento

- La conversion a `tool_calls` no rompió el pipeline.
- La ruta `router` sigue siendo la mas pesada por el contexto que inyecta AI-LAB.
- La conversion estructural funciona en router y gateway; el gateway es el borde mas ligero para tool use.
