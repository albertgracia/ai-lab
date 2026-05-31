---
title: "FASE 95 — Plan Mode (HISTORICO)"
summary: "Documento historico de FASE 9.5 (marzo 2026). El Plan Mode fue eliminado en FASE 20B y reemplazado por tool governance y perfiles cognitivos declarativos."
order: 21
---

> **ESTE DOCUMENTO ES HISTORICO — FASE 9.5 (marzo 2026).**
> La arquitectura actual (CP-22B+) reemplazo Plan Mode con:
> - Tool governance (`runtime/policies/tools/`, 3 modos: disabled/readonly/agentic)
> - Perfiles cognitivos (`runtime/profiles/*.json`)
> - Prompts declarativos (`runtime/prompts/*.md`)
> - Memory injector (`runtime/policies/memory/`)

## Contexto historico

En FASE 9.5 se introdujo el "Modo PLAN" como un modo operacional del AI-LAB. Definia que el copiloto podia leer, analizar, diagnosticar y proponer, pero NO ejecutar cambios sin confirmacion explicita.

Este concepto usaba:
- Delimitadores `[HARD_FACTS_BEGIN]` / `[HARD_FACTS_END]`
- System prompt "Eres el copiloto autonomo del AI-LAB de Albert. Operas en MODO PLAN..."
- `build_system_context()` con `_current_mode_label()` para inyectar el modo

## Que lo reemplazo

En CP-22B+, el comportamiento esta gobernado por:

| Antes (Plan Mode) | Ahora (FASE 21-22) |
|-------------------|---------------------|
| "MODO PLAN" en system prompt | `chat_profile.json` con prompt ligero |
| HARD_FACTS universal | Solo para reasoning/analysis |
| Shell bloqueado por modo | `blocked_tools.json` + bash_sanitizer |
| Confirmacion manual | 428 confirmation gate para write tools |
| `build_system_context()` con modo | `apply_profile()` con perfil cognitivo |

## Archivos legacy preservados

Los archivos de modos aun existen en `runtime/modes/` pero no son la fuente de verdad activa:

- `runtime/modes/plan.py` — preservado, no usado en routing
- `runtime/modes/registry.py` — preservado, no usado en routing
- `runtime/modes/mode_manager.py` — preservado, no usado en routing

## Que se mantiene del concepto original

- Respuesta en espanol
- Separacion de hechos e inferencias
- No ejecutar acciones destructivas sin control
- Rollback inmediato

Pero la implementacion ahora es via perfiles, politicas y prompts declarativos.
