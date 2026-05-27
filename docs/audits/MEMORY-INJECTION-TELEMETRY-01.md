# MEMORY-INJECTION-TELEMETRY-01

## Objetivo
Instrumentar AI-LAB para medir cuanta memoria/contexto se inyecta en cada respuesta y correlacionarlo con route_family, modelo, latencia y exito/error.

## Relacion con Qdrant audit/policy
- Audit: `QDRANT-MEMORY-GOVERNANCE-AUDIT-01` (PASS)
- Policy: `QDRANT-MEMORY-GOVERNANCE-POLICY-01` (PASS, commit `f85dd371`)
- Hallazgo principal: cognitive_history no registraba `memory_injected`, `chars_injected`, `collections_used`.

## Campos anadidos

### cognitive_history (eventos nuevos)
- `memory_injected`: bool
- `chars_injected`: int
- `estimated_tokens_injected`: int (ceil(chars/4))
- `collections_used`: list[string]
- `matches_total`: int
- `avg_score`, `max_score`, `min_score`: float|null
- `recall_source`: string|null
- `context_budget_chars`, `context_budget_used_chars`: int|null
- `context_truncated`: bool
- `prompt_tokens_delta`: int|null
- `route_family`: string

### routing_history (eventos nuevos)
- `route_family`: string
- `prompt_tokens`: int
- `completion_tokens`: int
- `memory_injected`: bool
- `chars_injected`: int
- `ttfb_ms`: float

## Que se mide
1. **Contexto pre-inyeccion**: tamano de mensajes antes de `inject_agent_context`.
2. **Contexto post-inyeccion**: tamano total de messages + system_prompt.
3. **Inferencia**: prompt_tokens, completion_tokens, latency_ms, ttfb_ms.
4. **Memoria**: si se inyecto, cuantos chars, que colecciones, scores, matches.

## Que NO se guarda
- Prompts completos de usuario
- Respuestas completas
- Secrets, tokens, credenciales, PII
- Payloads largos (>50000 chars truncados implicitamente)
- Datos personales

## Metricas Prometheus anadidas
- `ailab_memory_injection_events_total`: Counter
- `ailab_memory_injection_chars_total`: Counter
- `ailab_memory_injection_estimated_tokens_total`: Counter
- `ailab_memory_injection_matches_total`: Counter
- `ailab_memory_injection_context_truncated_total`: Counter
- `ailab_memory_injection_last_chars`: Gauge
- `ailab_memory_injection_last_estimated_tokens`: Gauge
- `ailab_memory_injection_latency_correlation_events_total`: Counter con labels `route_family`, `injected`

## Endpoint
`GET /runtime/memory-injection/summary`

Devuelve:
```json
{
  "status": "ok",
  "summary": {
    "events_total": 0,
    "chars_injected_total": 0,
    "estimated_tokens_injected_total": 0,
    "matches_total": 0,
    "last_event": null
  }
}
```

## Riesgos
- **Falso negativo**: telemetry captura solo el contexto post-inyeccion sin saber exactamente que parte vino de memoria. Para precision se necesitaria instrumentar antes/despues de `build_memory_context`.
- **Falsa correlacion**: prompt_tokens_delta puede incluir cambios de system_prompt no relacionados con memoria (ej. OBSERVED_RUNTIME injection).
- **Sin historico**: no hay migracion de datos historicos en routing_history/cognitive_history.

## Como interpretar metricas
- `memory_injection_events_total` sube con cada request. Si `chars_injected_total` es 0, no hay inyeccion de memoria.
- `memory_injection_latency_correlation_events_total{injected="true"}` son requests con memoria.
- Comparar latencia entre injected=true y injected=false para aislar impacto de memoria.
- `memory_injection_matches_total` indica cuantos items recupero Qdrant.

## Relacion con latencia
Con esta instrumentacion se puede empezar a correlacionar:
- `routing_history.prompt_tokens` vs `routing_history.latency_ms`
- `cognitive_history.chars_injected` vs `ttfb_ms` real de inferencia
- `cognitive_history.route_family` + `memory_injected` vs latencia promedio

## Rollback
1. Revertir cambios en `openai_gateway.py`: eliminar hooks try/except.
2. Revertir `routing_history.py`: eliminar nuevos parametros de `record_route_result`.
3. Revertir `prometheus_metrics.py`: eliminar metricas `ailab_memory_injection_*`.
4. Revertir `runtime_api_routes.py`: eliminar `handle_memory_injection_routes`.
5. Revertir `qdrant_routing_hook.py`: eliminar campos nuevos de `on_cognitive_event`.
6. Revertir `qdrant_collections.py`: eliminar optional_fields nuevos.
7. Eliminar `runtime/memory/memory_injection_telemetry.py`.
8. Reiniciar gateway.

## Archivos tocados
- `runtime/memory/memory_injection_telemetry.py` (NUEVO)
- `runtime/memory/qdrant_collections.py` (modificado)
- `runtime/memory/qdrant_routing_hook.py` (modificado)
- `runtime/routing/routing_history.py` (modificado)
- `runtime/telemetry/prometheus_metrics.py` (modificado)
- `runtime/gateway/openai_gateway.py` (modificado, 2 hooks)
- `runtime/gateway/runtime_api_routes.py` (modificado, endpoint)
- `tests/test_memory_injection_telemetry_01.py` (NUEVO)
- `docs/audits/MEMORY-INJECTION-TELEMETRY-01.md` (NUEVO)
