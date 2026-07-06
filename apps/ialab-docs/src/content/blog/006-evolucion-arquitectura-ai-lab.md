---
title: "AI-LAB: La Evolución Arquitectónica de un Runtime de IA Local"
description: "De un wrapper experimental a una plataforma cognitiva con streaming real, perfiles gobernados, agentic runtime simulado y observabilidad completa. 29 fases, 15 dashboards Grafana, 100+ métricas Prometheus."
summary: "Recorrido por la evolución arquitectónica de AI-LAB: del gateway monolítico al runtime gobernado con streaming real, agentic pipeline y hardening operacional."
date: "2026-05-20"
tags:
  - arquitectura
  - ai-lab
  - streaming
  - agentic
  - observability
  - governance
---


AI-LAB empezó como un simple wrapper HTTP entre OpenCode/OpenWebUI y LM Studio. Hoy es una plataforma cognitiva local con 9 servicios, 22 fases completadas, streaming real, agentic runtime simulado y observabilidad de grado producción. Este es el recorrido.

## Fase 0: El Gateway Monolítico (Enero-Mayo 2026)

El punto de partida era un único script Python — `openai_gateway.py` — que traducía peticiones OpenAI-compatible a LM Studio. Sin routing, sin perfiles, sin memoria, sin observabilidad.

```
Cliente → Gateway → LM Studio
```

Funcionaba. Pero cada nueva capacidad se añadía como hardcode. Los prompts estaban incrustados en el código. Los modelos estaban hardcodeados. No había separación de responsabilidades.

## La Ruptura: Perfiles Cognitivos (FASE 21)

El punto de inflexión fue la introducción de **perfiles cognitivos como policy bundles declarativos**. En lugar de hardcodear `max_tokens`, `temperature` y `model` por ruta, estos parámetros salieron del código y pasaron a archivos JSON:

```json
{
  "profile": "chat",
  "model": { "default": "qwen2.5-coder-14b-instruct" },
  "inference": { "max_tokens": 512, "temperature": 0.4 },
  "tools": { "allowed": false },
  "memory": { "policy": "light" }
}
```

Esto desacopló el comportamiento del runtime del código. Un perfil podía evolucionar sin tocar una línea de Python.

## La Torre de Control: Observabilidad (FASE 24-27)

Con el runtime estabilizado, llegó la torre de control:

- **Prometheus** en observability host:9090 — 80+ métricas `ailab_*`
- **Grafana** en observability host:3000 — 15 dashboards auto-provisionados
- **Alertas** — 19 reglas con health checks
- **Audit trail** — shards diarios en JSONL con `request_id`
- **Replay API** — trazabilidad completa de cada request

Cada decisión del runtime — selección de perfil, tool call, memory recall — quedaba registrada, medida y alertada.

## La Disciplina: Memoria Gobernada (FASE 23)

AI-LAB podía recordar. Pero recordar sin control es peligroso. Implementamos:

- **3 políticas de memoria**: minimal (sin recall), light (1 memoria, solo incidents), full (5 memorias, 3 colecciones)
- **Contamination guard**: si el recall trae items con score < 0.15, se descarta
- **8 skip reasons** normalizados: `SKIP_MINIMAL_GUARD`, `SKIP_QUERY_SHORT`, `SKIP_CONTAMINATION`, etc.

La memoria no era magia — era ingeniería con límites explícitos.

## El Puente: OpenCode & OpenWebUI (FASE 25-26)

Con el runtime maduro, los clientes necesitaban perfiles de producción. Implementamos:

- Single ingress router para ambos clientes
- Supresión de `HARD_FACTS` para peticiones no técnicas
- `question` tool stripping
- `_is_reasoning_request()` con 10 keywords

El resultado: OpenCode y OpenWebUI funcionando en producción con perfiles optimizados.

## La Ambición: Agentic Runtime Gobernado (FASE 28)

El salto más ambicioso: permitir que el LLM propusiera cambios, pero NUNCA ejecutarlos sin aprobación humana.

Implementamos 10 capas:

```
Action Intent Layer  →  LLM genera intents, no tool_calls
Planner              →  Intents → acciones reales + DAG
Dry-Run Engine       →  Simula sin ejecutar
Risk Engine          →  Determinista, nunca el LLM decide
Explainability       →  Resumen en lenguaje natural
Approval Gate        →  Tickets HMAC, TTL, single-use
Simulation Executor  →  NO-OP (siempre en FASE 28.0)
Verifier             →  Checksums, service health, side effects
Rollback             →  Transaction boundaries + snapshots
Replay               →  Plan diffing (3 versiones)
```

**Principio fundacional:** el LLM PROPONE, el runtime EVALÚA, el humano APRUEBA. Nunca al revés.

## El Realismo: Streaming de Verdad (FASE 29.2)

Durante meses, el "streaming" de AI-LAB era un espejismo. El gateway esperaba la respuesta completa de LM Studio (~10-13s), la bufferizaba, y luego emitía 2 chunks SSE sintéticos. El cliente veía texto instantáneo... después de 13 segundos de spinner.

La FASE 29.2 eliminó el pseudo-SSE. El gateway ahora:

1. Envía `stream=true` a llama.cpp (Vulkan/ROCm)
2. Relaya cada chunk directamente sin bufferizar
3. Mide el TTFB real (~1.5s en vez de 10-13s)

```python
def relay_stream(upstream, handler, model="unknown"):
    for chunk in upstream.iter_content(chunk_size=8192):
        handler.wfile.write(chunk)
        handler.wfile.flush()  # ← esto es la magia
```

Con backpressure (max 3 streams concurrentes), timeouts en 4 capas (connect, first_chunk, idle, completion) y feature flag para rollback instantáneo.

## La Estabilidad: Gateway Hardening (FASE 29.0)

Un incidente con 3 workers concurrentes reveló vulnerabilidades críticas:

- Sin PID file → posible doble instancia del gateway
- Sin port ownership guard → rogue uvicorn podía ocupar :8008
- Sin SIGTERM handler → shutdowns sucios

Implementamos `process_guard.py`: singleton lock, rogue uvicorn killer automático, cleanup atexit. Systemd hardening con `StartLimitBurst=6`. El gateway ya no crashea bajo concurrencia.

## La Base: llama.cpp Vulkan/ROCm (FASE 29.0)

La migración de LM Studio a llama.cpp v2.14.0 transformó la latencia:

| Backend | p50 | Spread (max-min) |
|---------|-----|-----------------|
| LM Studio (viejo) | ~11.9s | 15-30s |
| llama.cpp Vulkan | 10.06s | 0.7s |
| llama.cpp ROCm | 9.99s | 0.6s |

La consistencia es el verdadero avance: de 30 segundos de varianza a menos de 1 segundo.

## El Stack Hoy

```
┌─────────────────────────────────────────┐
│          Clientes                        │
│  OpenCode  ·  OpenWebUI  ·  curl -N     │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│       Gateway (:8008)                    │
│  ┌──────────────────────────────────┐   │
│  │ Routing  ·  Perfiles  ·  Memoria │   │
│  │ Agentic  ·  Streaming Real       │   │
│  │ Hardening (PID, SIGTERM, Guard)  │   │
│  └──────────────────────────────────┘   │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│    llama.cpp (inference GPU node:1234)        │
│    RX9070 16GB  ·  Vulkan/ROCm          │
│    qwen2.5-14b  ·  llama-3.1-8b        │
│    qwen3.6-27b  ·  nomic-embed          │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│    Observabilidad (observability host)         │
│  Prometheus :9090  ·  Grafana :3000     │
│  100+ métricas  ·  15 dashboards        │
│  19 alertas  ·  Audit trail diario     │
└─────────────────────────────────────────┘
```

## Lo Construido

| Capa | Entregables |
|------|------------|
| **Runtime** | 9 servicios systemd, gateway con streaming real, router API, live API |
| **Cognitivo** | 8 perfiles (3 estables), routing por intención, 10 KNOWN_INTENTS |
| **Memoria** | 3 políticas gobernadas, Qdrant, contamination guard, decay scoring |
| **Agentic** | Pipeline 10 capas, simulation-only mode, approval HMAC, rollback transaccional |
| **Observabilidad** | Prometheus + Grafana, 100+ métricas, 15 dashboards, 19 alertas |
| **Infraestructura** | llama.cpp Vulkan/ROCm, RX9070, hardening gateway, PID singleton |
| **Docs** | 128 páginas Astro, blog, roadmap, runbooks |

## Lo Que NO Hicimos

- No Kubernetes, no cloud, no SaaS
- No multi-agent swarm (riesgo de recursión)
- No auto-aprobación (human-in-the-loop siempre)
- No ejecución real agentic (todo simulation-only en FASE 28.0)

## Lo Que Viene

- FASE 29.3 → Readonly execution runtime
- FASE 29.5 → Streaming governance (sanitize on stream)
- FASE 30 → AI-LAB v1.0 estable

---

AI-LAB no es un producto. Es un laboratorio. La diferencia es que aquí la estabilidad, la observabilidad y la gobernanza no son afterthoughts — son el diseño desde el principio.
