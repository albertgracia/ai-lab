---
title: "FASE 29.4.4 — Error Taxonomy & Failure Attribution"
summary: "Elimina la caja negra de ailab_errors_total. Convierte todos los errores runtime en eventos clasificados, atribuibles y observables con taxonomy de 31 categorías, severity, recoverability, origin stage, attribution engine y structured logs."
order: 82
---

## Problema

`ailab_errors_total` era un contador texto-plano sin labels, sin categoría, sin atribución. Los errores coexistían en **tres sistemas** (in-memory dict + JSON persist + prometheus_client) **sin coordinación**. Había **47 `except` con `pass`** que silenciaban fallos sin dejar traza.

## Solución

Nuevo módulo `runtime/errors/` con:

- **Taxonomy** (31 categorías)
- **Severity** (INFO/WARNING/ERROR/CRITICAL)
- **Recoverability** (4 niveles)
- **Attribution engine** (exception → categoría)
- **Structured JSONL logging** a `/opt/ai-lab/logs/runtime_errors.jsonl`
- **Prometheus counters** (10 nuevos)
- **Origin stage tracking** (11 stages)

## Cambios

### Nuevo: `runtime/errors/` (8 archivos)

| Archivo | Propósito |
|---------|-----------|
| `taxonomy.py` | `RuntimeErrorCategory` enum con 31 categorías |
| `severity.py` | `ErrorSeverity`, `severity_for_category()` |
| `recovery.py` | `Recoverability`, `recoverability_for_category()` |
| `correlation.py` | `CorrelationTags`, `new_error_id()`, `stack_hash()`, `dedup_key()` |
| `runtime_errors.py` | `RuntimeErrorEvent` dataclass con 25 campos |
| `attribution.py` | `classify_exception()`, `classify_http_status()`, `classify_stream_failure()`, `classify_timeout()`, `build_error_event()` |
| `metrics.py` | 10 Prometheus counters + JSONL RotatingFileHandler (100MB, 7 backups) |
| `__init__.py` | Export público |

### Modificado: `runtime/gateway/openai_gateway.py`

**5 `record_error()` reemplazados por `emit_error(build_error_event(...))`**:

| Contexto | Category | Origin Stage |
|----------|----------|-------------|
| `do_GET` /v1/models falla | `UPSTREAM_CONNECTION` | `upstream` |
| `relay_stream()` Exception | `STREAM_INTERRUPTED` | `streaming` |
| Fake SSE response falla | `UPSTREAM_INVALID_RESPONSE` | `upstream` |
| `RequestException` | `UPSTREAM_TIMEOUT` / `LMSTUDIO_TIMEOUT` | `connect`/`read` |
| Catch-all Exception | clasificado vía `classify_exception()` | `gateway` |

**6 nuevos puntos observacionales** (emiten evento pero no cambian comportamiento):

| Punto | Origin Stage | Antes | Ahora |
|-------|-------------|-------|-------|
| `apply_profile()` falla | `routing` | `pass` | `emit(ROUTING_FAILURE)` |
| `format_report_context()` falla | `reporting` | `pass` | `emit(GATEWAY_INTERNAL)` |
| Pipeline agentic falla | `agentic` | solo `print()` | `emit(WORKFLOW_INVALID_STATE)` |
| Disabled model attempt | `routing` | solo métrica | `emit(MODEL_DISABLED)` |
| Stream parse fail | `streaming` | no capturado | `emit(STREAM_INTERRUPTED)` |

### Modificado: `runtime/gateway/stream_sanitizer.py`

| Excepción | Antes | Ahora |
|-----------|-------|-------|
| `BrokenPipeError`, `ConnectionResetError`, `OSError` | `_interrupted_streams++` silencioso | `emit(CLIENT_DISCONNECT)` |
| `Exception` fallback | solo `[STREAM_ERROR]` | `emit(STREAM_INTERRUPTED)` |
| Stream slot exhaustion | solo retorno | `emit(STREAM_BACKPRESSURE)` |
| First chunk timeout >20s | no detectado | DRY RUN: `emit(LMSTUDIO_TIMEOUT)` observacional |
| `upstream.close()` falla | `pass` | mantiene `pass` (no crítico) |

## Taxonomy completa (31 categorías)

```
UPSTREAM_TIMEOUT | UPSTREAM_CONNECTION | UPSTREAM_INVALID_RESPONSE
LMSTUDIO_TIMEOUT | LMSTUDIO_STREAM_STALL | LMSTUDIO_MODEL_UNAVAILABLE
STREAM_INTERRUPTED | STREAM_BACKPRESSURE | CLIENT_DISCONNECT
REQUEST_VALIDATION | REQUEST_TOO_LARGE | PROMPT_POLICY | PROMPT_SANITIZATION
GOVERNANCE_BLOCK | TOOL_VALIDATION | TOOL_MALFORMED
WORKFLOW_INVALID_STATE | EXECUTOR_READONLY_BLOCK
SANDBOX_POLICY_BLOCK | SANDBOX_TRAVERSAL_ATTEMPT | ROLLBACK_FAILURE
MEMORY_RECALL_FAILURE | MEMORY_EMPTY | ROUTING_FAILURE | MODEL_DISABLED
CONCURRENCY_THROTTLE | GPU_PRESSURE | VRAM_PRESSURE
GATEWAY_INTERNAL | UNKNOWN
```

## Exception → Category mapping

| Exception | Category |
|-----------|----------|
| `requests.ConnectTimeout` | `UPSTREAM_TIMEOUT` |
| `requests.ReadTimeout` | `LMSTUDIO_TIMEOUT` |
| `requests.ConnectionError` | `UPSTREAM_CONNECTION` |
| `requests.RequestException` (timeout) | `UPSTREAM_TIMEOUT` |
| `BrokenPipeError` | `CLIENT_DISCONNECT` |
| `ConnectionResetError` | `CLIENT_DISCONNECT` |
| `ConnectionAbortedError` | `CLIENT_DISCONNECT` |
| `json.JSONDecodeError` | `UPSTREAM_INVALID_RESPONSE` |
| `OSError` | `STREAM_INTERRUPTED` |
| `PermissionError` | `GOVERNANCE_BLOCK` |
| `TimeoutError` | `LMSTUDIO_TIMEOUT` |
| `ValueError` / `TypeError` | `REQUEST_VALIDATION` |
| `RuntimeError` / `SystemError` | `GATEWAY_INTERNAL` |
| `Exception` (fallback) | `UNKNOWN` |

## Métricas Prometheus

| Métrica | Labels | Tipo |
|---------|--------|------|
| `ailab_runtime_errors_total` | `category, severity, component` | Counter |
| `ailab_runtime_error_recoverability_total` | `recoverability` | Counter |
| `ailab_runtime_timeout_total` | `stage` | Counter |
| `ailab_runtime_stream_interruptions_total` | `reason` | Counter |
| `ailab_runtime_upstream_failures_total` | `reason` | Counter |
| `ailab_runtime_gateway_internal_total` | `exception` | Counter |
| `ailab_runtime_client_disconnect_total` | — | Counter |
| `ailab_runtime_error_slo_impact_total` | `slo` | Counter |
| `ailab_runtime_error_retryable_total` | — | Counter |
| `ailab_runtime_error_nonrecoverable_total` | — | Counter |

## Structured logging

Path: `/opt/ai-lab/logs/runtime_errors.jsonl`

Formato por línea:
```json
{
  "timestamp": 1711234567.89,
  "category": "LMSTUDIO_TIMEOUT",
  "severity": "warning",
  "recoverability": "retryable",
  "origin_stage": "upstream",
  "component": "gateway",
  "exception_class": "ReadTimeout",
  "model": "qwen2.5-coder-14b-instruct",
  "retryable": true,
  "root_cause": "upstream too slow",
  "latency_ms": 30211
}
```

Rotación: 100MB máx, 7 archivos de backup.

## Feature flags

```env
AI_LAB_ERROR_ATTRIBUTION_ENABLED=true
AI_LAB_ERROR_STRUCTURED_LOGS=true
AI_LAB_ERROR_PROMETHEUS_ENABLED=true
AI_LAB_ERROR_TIMEOUT_ENFORCEMENT=false
```

## Legacy compatibility

Mantenido en transición (FASE A→D):
- **FASE A** (ahora): Emisión dual (`ailab_errors_total` legacy + `ailab_runtime_errors_total` nueva)
- **FASE B**: Migrar dashboards Grafana
- **FASE C**: Validar equivalencia en burn-in
- **FASE D**: Deprecar legacy

## Validación

183 tests:
- 19 categorías de test (exception mapping, severity, recoverability, timing, correlation, dedup, origin stages, secrets filtering)
- 0 regresiones en tests existentes
