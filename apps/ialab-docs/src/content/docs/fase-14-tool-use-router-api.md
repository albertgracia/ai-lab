---
title: "FASE 14 - Tool-Use Native Routing and OpenAI Tool Call Bridging"
summary: "Hito del router AI-LAB para detectar requests con tools, priorizar modelos tool_use descubiertos y emitir tool_calls estructurado."
order: 30
---

## Hito

AI-LAB Router API ya puede detectar peticiones que requieren herramientas, priorizar modelos `tool_use` descubiertos en vivo y convertir respuestas de LM Studio con `<tool_call>` a `tool_calls` OpenAI-native.

## Alcance implementado

- `runtime/models/model_classifier.py`
- `runtime/models/model_registry.py`
- `runtime/llm/model_router.py`
- `runtime/llm/router_api.py`
- `runtime/router/capability_router.py`
- `runtime/distributed/token_router.py`
- `runtime/gateway/tool_call_parser.py`
- `runtime/gateway/openai_gateway.py`
- `runtime/gateway/stream_sanitizer.py`

## Comportamiento nuevo

- detecta `tools` y `tool_choice` en la request
- activa `tool_use` como capability de routing
- prioriza candidatos `tool_use` en discovery vivo
- convierte `<tool_call>` en `tool_calls` estructurado
- mantiene intacto el forwarding de `tools` y `tool_choice`

## Evidencias

| Verificacion | Resultado |
|---|---|
| Router `tool_use` | `qwen/qwen3.6-35b-a3b` |
| Gateway `tool_use` | `qwen/qwen3.6-35b-a3b` |
| `tool_choice=required` | `tool_calls` estructurado, `content=null` |
| RX9070 tool latency | ~`2.4s` promedio |
| RX7900XT tool latency | ~`0.37s` promedio |
| Router/Gateway bridge | `tool_calls` estructurado en ambas APIs; el router sigue siendo la ruta mas pesada por contexto inyectado |

## Resultado

El router ya es tool-aware y el bridge de tool calls funciona en el borde sin romper el resto del pipeline.
