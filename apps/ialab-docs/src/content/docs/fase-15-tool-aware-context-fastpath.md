---
title: "FASE 15 - Tool-Aware Context Fastpath and Latency Validation"
summary: "Optimizacion de tool_use y saludos triviales; test y produccion local convergen en ~3s y el gateway devuelve tool_calls estructurado."
order: 31
---

## Hito

Se introdujo un fastpath tool-aware para `tool_use` en el router y el gateway. El objetivo era cortar contexto pesado, mantener `tool_calls` estructurado y medir si la mejora era real.

## Implementacion

- `runtime/gateway/tool_request_classifier.py`
- `runtime/llm/router_api.py`
- `runtime/gateway/openai_gateway.py`

## Bateria de latencia

Comparacion entre una instancia temporal de prueba y la produccion local activa.

| Ruta | Test | Produccion local |
|---|---:|---:|---|
| `router` tool_use | `2992.5 ms` | `2986.0 ms` |
| `gateway` tool_use | `2983.0 ms` | `2995.7 ms` |
| `router` normal | `16337.7 ms` | `21993.1 ms` |
| `gateway` normal | `39463.4 ms` | `37793.4 ms` |

### Baseline previo

Antes del fastpath y del routing tool-aware, la misma peticion `tool_use` sobre el servicio desplegado seguia cerca de `29.5s` de media.

## Hallazgos

- El fastpath del router si reduce la latencia de `tool_use` de forma fuerte.
- `qwen/qwen3.6-27b` en `rx9070` ya queda priorizado para `tool_use`.
- Test y produccion local convergen en el mismo comportamiento.
- El gateway devuelve `tool_calls` estructurado sin romper el bridge OpenAI-native.
- Los saludos triviales van por ruta breve, sin `HARD_FACTS`.
- `sudo reboot` y variantes peligrosas quedan bloqueadas por policy.
- Los saludos triviales ganan incluso si el cliente manda `tools` por defecto.
- Los bloques `<system-reminder>` se eliminan de entrada y salida.

## Resultado

La fase queda alcanzada.

- `router`: exito.
- `gateway`: exito.
- `tool_use` estable con fastpath.
