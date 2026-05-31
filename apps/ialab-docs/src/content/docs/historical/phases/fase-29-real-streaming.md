---
title: "FASE 29.2 — Real Streaming & TTFB Architecture"
summary: "Eliminación del pseudo-streaming y activación de streaming real end-to-end con relay de chunks nativos desde llama.cpp. Feature flag AI_LAB_REAL_STREAMING, backpressure, timeouts en 4 capas y primeras métricas de TTFB real."
order: 69
---

## Hito

Se completó FASE 29.2: eliminación del pseudo-SSE introducido en FASE 27.1.1 y reactivación del streaming real end-to-end.

## Problema

Desde FASE 27.1.1, el gateway hardcodeaba `stream=False` contra LM Studio. Esperaba la response completa, la bufferizaba en memoria con `response.json()`, y luego sintetizaba 2 chunks SSE artificiales + `[DONE]`. El resultado era **pseudo-streaming**: el cliente veía un spinner hasta recibir todo el texto de golpe.

- TTFB = completion completa (~10-13s)
- `stream_chunks_total` = siempre 2 por request
- `completion_stream_duration` ≈ 0ms (medición tautológica)
- Sin medición real de primer token

## Solución

Se reactivó `relay_stream()` — un módulo de 17 líneas que existía en versiones legacy del gateway pero fue reemplazado durante FASE 27.1.1:

```python
def relay_stream(upstream, handler, model="unknown"):
    for chunk in upstream.iter_content(chunk_size=8192):
        if not chunk:
            continue
        handler.wfile.write(chunk)
        handler.wfile.flush()
```

El gateway ahora:
1. Envía `stream=true` a LM Studio cuando el cliente lo solicita
2. Usa `requests.post(stream=True)` para no bufferizar
3. Relaya cada chunk directamente al cliente sin esperar completion

## Feature flag

```bash
AI_LAB_REAL_STREAMING=true   # streaming real
AI_LAB_REAL_STREAMING=false  # fallback fake SSE (legacy)
```

Rollback instantáneo sin reiniciar.

## Backpressure

```python
MAX_CONCURRENT_STREAMS = 3
MAX_STREAM_DURATION_SEC = 300
FIRST_CHUNK_TIMEOUT_SEC = 20
```

Con `finally{}` que limpia slots, cierra upstream y libera recursos.

## Resultados

| Métrica | Antes (fake SSE) | Ahora (real) |
|---------|-----------------|--------------|
| Chunks por request | 2 (sintéticos) | 79 (reales) |
| TTFB | ~10-13s (respuesta completa) | ~1.5s (primer chunk) |
| curl -N | Spinner → todo de golpe | Texto progresivo |
| Streams activos | 0 (siempre) | Variable real |
| Gateway | Estable | Estable |

## Arquitectura de timeouts (4 capas)

```
connect_timeout       = 5s     TCP handshake con LM Studio
first_chunk_timeout   = 20s    TTFB deadline (primer token)
stream_idle_timeout   = 30s    Máx inactividad entre chunks
completion_timeout    = 300s   Tiempo total máximo
```

## Archivos modificados

- `runtime/gateway/stream_sanitizer.py` — 17 → 112 líneas (backpressure, timeouts, cleanup, métricas)
- `runtime/gateway/openai_gateway.py` — `stream=False` → `stream=stream_enabled` condicional, relay real con fallback legacy
- `runtime/telemetry/prometheus_metrics.py` — métricas `ailab_stream_first_chunk_ms`, `ailab_stream_chunks_total` ya activas
