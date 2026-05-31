---
title: "FASE 16 - Observe Mode and Readonly Shell"
summary: "Modo de observacion para analisis tecnico/operativo sin HARD_FACTS obligatorio y con comandos informativos seguros."
order: 33
---

## Hito

Se introdujo un modo `observe` para inspeccion tecnica y operativa. Este modo reduce el peso del prompt, elimina el formato `HARD_FACTS` obligatorio y permite comandos readonly que solo aportan informacion.

## Alcance

- `runtime/modes/observe.py`
- `runtime/modes/registry.py`
- `runtime/modes/mode_manager.py`
- `runtime/state/live_api.py`
- `runtime/profiles/observe.py`
- `runtime/llm/router_api.py`
- `runtime/gateway/openai_gateway.py`
- `runtime/agent/intent_router.py`
- `runtime/planner/task_planner.py`
- `runtime/gateway/tool_request_classifier.py`
- `runtime/gateway/tool_call_parser.py`

## Comportamiento nuevo

- `observe` responde en modo natural y breve
- no exige `HARD_FACTS` en el prompt
- ignora `system-reminder` inyectado
- usa un resumen observable mínimo del runtime como contexto
- si la request trae `tools`, el routing tool-aware sigue teniendo prioridad
- acepta shell readonly a traves de la policy existente
- bloquea comandos peligrosos como `reboot` y `rm -rf`

## Evidencias

| Prueba | Resultado |
|---|---|
| `HOLA` | respuesta breve, sin HARD_FACTS |
| analisis operativo | resumen tecnico corto, sin secciones obligatorias |
| `pwd` en observe | permitido |
| `ls /opt/ai-lab` en observe | permitido |
| `reboot` en observe | bloqueado |

## Resultado

La ruta `observe` queda lista para pruebas seguras de inspeccion y analisis.
