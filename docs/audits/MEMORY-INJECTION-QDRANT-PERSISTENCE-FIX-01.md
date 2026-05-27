# MEMORY-INJECTION-QDRANT-PERSISTENCE-FIX-01

**Fecha:** 2026-05-27 21:02 CEST
**Objetivo:** Propagar campos de memory injection telemetry a Qdrant routing_history.

## Cambio

`runtime/memory/qdrant_routing_hook.py` — `on_routing_event()`:

Anadidos 9 campos al payload Qdrant desde `event_data`:
- `route_family`, `prompt_tokens`, `completion_tokens`
- `memory_injected`, `chars_injected`, `estimated_tokens_injected`
- `collections_used`, `matches_total`, `ttfb_ms`

`runtime/memory/qdrant_collections.py` — schema `routing_history`:

Anadidos 9 campos a `optional_fields`.

## Validacion

- compileall: PASS
- tests memory injection: 19/19 PASS
- smoke endpoints: OK
- Request controlada: 200, 0.55s, 86 prompt_tokens
- Qdrant routing_history con filtro reciente: 1 punto con todos los campos nuevos
- Prompts completos guardados: NO

## Verificacion Qdrant

```
route_family=cognitive
prompt_tokens=86
completion_tokens=2
memory_injected=False
chars_injected=0
ttfb_ms=550
estimated_tokens_injected=0
collections_used=[]
matches_total=0
```

## Rollback

1. Revertir cambios en `qdrant_routing_hook.py`: eliminar los 9 nuevos campos de `on_routing_event()`.
2. Revertir cambios en `qdrant_collections.py`: eliminar `optional_fields` nuevos de routing_history.
3. Reiniciar gateway.
