---
title: "Parche — OpenCode, Router y Gateway Streaming"
summary: "Documenta la correccion aplicada al flujo de OpenCode y al runtime AI-LAB: respuestas directas para informes, compatibilidad SSE, retry ante Model unloaded y limpieza de la integracion question tool."
order: 39
---

## Contexto

Durante las pruebas posteriores a FASE 18 aparecieron dos problemas distintos:

1. OpenCode intentaba usar la herramienta `question` con `questions` serializado como string JSON.
2. El flujo router/gateway hacia LM Studio mezclaba streaming de cliente con payloads no compatibles.

## Problema en OpenCode

El error observado fue:

```text
SchemaError(Expected array, got "[...]")
```

La causa era la invocación de `question` con un string en vez de un array nativo. Para informes y resúmenes abiertos, la respuesta correcta es directa, sin pasar por esa herramienta.

## Problema en Router/Gateway

El runtime presentaba síntomas encadenados:

- respuestas que no llegaban a OpenCode
- errores de JSON o SSE incompatibles
- fallos intermitentes con `Model unloaded`

## Corrección aplicada

### Router API (`runtime/llm/router_api.py`)

- mantiene la selección capability-aware de nodo y modelo
- reintenta ante `unloaded` o `invalid model identifier`
- genera SSE compatible para el cliente sin romper el formato OpenAI
- evita reenviar directamente payloads de streaming incompatibles a LM Studio

### Gateway (`runtime/gateway/openai_gateway.py`)

- limpia `stream` antes de enviar el payload al backend
- reintenta ante `Model unloaded`
- responde con SSE compatible cuando el cliente pidió streaming

### Relé de stream (`runtime/gateway/stream_sanitizer.py`)

- queda reducido a helper de relé compatible con bytes crudos

## Validación

Se verificó:

- `GET /health` del router
- completaciones no-stream y stream contra `:8083`
- completaciones stream contra `:8008`
- respuesta directa correcta para `hola`

## Resultado operativo

- OpenCode ya puede responder a saludos e informes sin caer en el error de `question`.
- El router y el gateway vuelven a cerrar el ciclo de conversación sin cuelgues por JSON/SSE.
- El runtime queda documentado para futuras regresiones.
