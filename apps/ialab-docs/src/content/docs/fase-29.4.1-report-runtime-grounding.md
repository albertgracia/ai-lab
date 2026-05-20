---
title: "FASE 29.4.1 — Report Runtime Grounding Fix"
summary: "Los reportes pesados (informe técnico, estructura general, detallado) ahora reciben OBSERVED_RUNTIME real en lugar de una referencia vacía. Nuevo módulo runtime/context/report_runtime_context.py, prompt externo en runtime/prompts/report_prompt.md, y 4 métricas Prometheus nuevas."
order: 79
---

## Objetivo

Corregir el bug de grounding en reportes: `build_minimal_report_messages()` mencionaba `OBSERVED_RUNTIME` en el system prompt pero nunca lo construía ni inyectaba. Los reportes heavy (ruta `report` con qwen2.5-14b) respondían "no tengo información" porque el LLM no recibía datos reales del runtime.

## Cambios

### Nuevo: `runtime/context/report_runtime_context.py`

Módulo dedicado para construir el snapshot OBSERVED_RUNTIME a partir de módulos Python locales:

- `build_report_runtime_context()` — recolecta datos de:
  - `runtime.state.runtime_state` (modo, sesiones, streams, ejecuciones)
  - `runtime.distributed.runtime_topology` (gateway host/port, backend host/port)
  - `runtime.analytics.health_score` (health score, nivel, razones)
  - `config/inference_nodes.json` (nodos GPU disponibles)
  - `runtime/profiles/manifest_profiles.json` (perfiles disponibles)
- `format_report_runtime_context()` — serializa a JSON string, capped a 12,000 chars, con `observed_fields` y `missing_fields`
- `extract_target_ip(text)` — extrae IP/dominio/URL del prompt del usuario (ej. "dame el estado de 192.168.1.40" → `192.168.1.40`)
- `REPORT_MAX_CHARS = 12000` — límite de tamaño del snapshot

### Nuevo: `runtime/prompts/report_prompt.md`

System prompt externo para reportes, versionable y auditable:

```
Responde en espanol, directo y util.
Genera un informe breve en 5-8 lineas.
Usa unicamente los datos disponibles en OBSERVED_RUNTIME o en el contexto proporcionado.
...
```

Cargado via `Path` en `tool_request_classifier.py` con caché (`_load_report_prompt()`).
Registrado en `runtime/prompts/manifest.json` como ruta `report → report_prompt.md`.

### Modificado: `runtime/gateway/tool_request_classifier.py`

- `build_minimal_report_messages()` ahora acepta `observed_runtime: str | None = None`. Si se proporciona, lo inyecta como `\n\nOBSERVED_RUNTIME: {snapshot}` después del system prompt.
- Carga el prompt desde `runtime/prompts/report_prompt.md` vía `_load_report_prompt()` con fallback inline.

### Modificado: `runtime/gateway/openai_gateway.py`

- En `inject_agent_context()`, antes del bloqueo de rutas report, construye `_report_runtime` y `_report_grounded_target` si la ruta es report.
- Inyecta `_report_grounded: true` en el payload.
- Inyecta `_report_grounded_target` si se detectó IP/dominio.
- Para **light report** (minimal/report): pasa `observed_runtime` a `build_minimal_report_messages()`.
- Para **heavy report** (report): pasa `observed_runtime`, y elimina `system_prompt` redundante para evitar doble system message.
- Métricas inline: `REPORT_GROUNDING_TOTAL`, `REPORT_TARGET_IP_TOTAL`, `REPORT_MISSING_FIELDS_TOTAL`, `REPORT_UNGROUNDED_TOTAL`.

### Modificado: `runtime/telemetry/prometheus_metrics.py`

4 nuevas métricas:

| Métrica | Tipo | Labels | Descripción |
|---------|------|--------|-------------|
| `ailab_report_grounding_total` | Counter | — | Reportes con OBSERVED_RUNTIME inyectado |
| `ailab_report_missing_fields_total` | Counter | `count` | Reportes con campos faltantes |
| `ailab_report_target_ip_total` | Counter | — | Reportes con IP/dominio detectado |
| `ailab_report_ungrounded_total` | Counter | — | Reportes con cero campos observados |

## Flujo de datos

```
Peticion de informe
  → inject_agent_context()
    → classify_chat_route() → family=="report", variant="heavy"
    → format_report_runtime_context()
      → lee runtime_state, topology, health_score, inference_nodes
      → produce JSON con observed_fields + missing_fields
    → extract_target_ip(user_text) → IP/dominio o None
    → payload["_report_grounded"] = True
    → build_minimal_report_messages(user_text, observed_runtime=snapshot)
      → carga prompt de runtime/prompts/report_prompt.md
      → inyecta "OBSERVED_RUNTIME: {snapshot}" al final
    → payload["messages"] = [system, user]
    → (system_prompt se pone None para evitar doble inyeccion)
  → POST a LM Studio
  → Respuesta del LLM con datos reales del runtime
```

## Grounding discipline

- Datos vienen de módulos Python locales (NO HTTP remoto)
- NO memory recall, NO tools, NO HARD_FACTS
- Snapshot capped a 12,000 chars
- `observed_fields` / `missing_fields` ayudan al LLM a distinguir ausencia vs null
- `_report_grounded=true` inyectado en payload para futura gobernanza

## Pruebas

```python
# extract_target_ip
extract_target_ip("dame el estado de 192.168.1.40")
# → "192.168.1.40"

extract_target_ip("revisa metricas.labrazahome.com")
# → "metricas.labrazahome.com"

extract_target_ip("http://192.168.1.40:9090/targets")
# → "192.168.1.40:9090"

# build_report_runtime_context
ctx = build_report_runtime_context()
ctx["observed_fields"]
# → ["runtime", "status", "mode", "active_sessions", ..., "profiles_available"]

ctx["health_score"]
# → 40

# format: JSON < 12,000 chars
snapshot = format_report_runtime_context()
# ~780 chars en estado actual
```
