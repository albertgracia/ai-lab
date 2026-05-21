---
title: "FASE 29 — Runtime Observability"
summary: "Gateway hardening, real streaming, three-model runtime, SLO enforcement, error taxonomy, SLO health endpoint always-on, parallel tool call hardening."
order: 10
---

## Resumen

La FASE 29 transformó la observabilidad del runtime: gateway hardening contra crash loops y puertos robados, streaming real eliminando pseudo-SSE, three-model runtime consolidado, SLO enforcement con auto-protección, error taxonomy para atribución de fallos y parallel tool call hardening.

## Subfases implementadas

| Subfase | Checkpoint | Descripción |
|---------|------------|-------------|
| 29.0 | Gateway hardening | PID singleton, rogue uvicorn killer, SIGTERM handler, systemd hardening |
| 29.2 | CP-29.2-B-STREAMING-BURNIN-STABLE | Real streaming: relay directo de chunks SSE desde llama.cpp |
| 29.3 | CP-29.3-THREE-MODEL-RUNTIME-STABLE | Three-model runtime: llama-3.1-8b, qwen2.5-14b, nomic-embed |
| 29.3.1 | Routing tightening | Routing 100% determinista, 48 greeting markers, lightweight heuristic |
| 29.3.2 | SLO baseline | 45-min burn-in, 306/306 OK. TTFB p50=804ms, p95=~3s |
| 29.4 | CP-29.4-SLO-ENFORCEMENT-STABLE | SLO enforcement engine con 4 niveles de degradación |
| 29.4.1 | Report runtime grounding | OBSERVED_RUNTIME inyectado en reportes |
| 29.4.2 | Report presentation fix | Corrección de presentación de reportes |
| 29.4.3 | Runtime identity grounding | Identidad del runtime en reportes |
| 29.4.4 | CP-29.4.4-ERROR-TAXONOMY-STABLE | Error taxonomy y failure attribution |
| 29.4.4-C | CP-29.4.4-C-SLO-HEALTH-ENDPOINT-STABLE | SLO health endpoint always-on 200 |
| 29.4.4-D | CP-29.4.4-D-PARALLEL-TOOLCALL-HARDENING-STABLE | Parallel tool call hardening |

## Gateway Hardening (FASE 29.0)

`process_guard.py`:
- PID lock singleton (previene 2 instancias)
- Rogue uvicorn killer en prebind
- SIGTERM handler: graceful shutdown con flush de métricas
- Port hardening: router_api.py no puede ocupar :8008
- Systemd: StartLimitBurst=6 previene fork storms
- 15 métricas lifecycle

## Real Streaming (FASE 29.2)

- `relay_stream()` con `requests.post(stream=True)`
- Relay directo de chunks SSE desde llama.cpp sin bufferizar
- Backpressure: max 3 streams concurrentes
- Timeout 4 capas: connect=5s / chunk=20s / idle=30s / completion=300s
- TTFB ~1.5s (vs ~12s con fake SSE)
- ~79 chunks reales vs 2 sintéticos
- Rollback vía `AI_LAB_REAL_STREAMING=false`

## Three-Model Runtime (FASE 29.3)

Model set activo:
- `llama-3.1-8b-instruct` — minimal, observe, greetings
- `qwen2.5-coder-14b-instruct` — coding, report, architecture, reasoning
- `nomic-embed-text-v1.5` — embeddings

qwen3.6-27b desactivado (no borrado del disco).

## SLO Enforcement (FASE 29.4)

### RuntimeSLOManager

Estados: GREEN (0), YELLOW (1), RED (2).
Evaluación cada 10s con deques sliding window.

### DegradationManager (4 niveles)

| Level | Nombre | Acciones |
|-------|--------|----------|
| 0 | NORMAL | Routing completo |
| 1 | LIGHT | forced llama + qwen protection + qwen parallel 2→1 |
| 2 | HEAVY | bloqueo observe/report/cognitive (observable, no auto-activo) |
| 3 | EMERGENCY | llama-only (observable, no auto-activo) |

Anti-flapping: 30s entre transiciones, cooldown 30s.

### AdaptiveConcurrency

- qwen parallel: 2 (GPU<70%) → 1 (GPU>90%)
- llama parallel: 3 (GPU<90%) → 2 (GPU>90%)

### PrioritySlotManager

Lane 1 (critical): 2 slots dedicados para minimal/observe.
Lane 2+3: pool compartido de 2 slots.

### Feature flags

- `AI_LAB_ENABLE_SLO_ENFORCEMENT=false` (default)
- `AI_LAB_SLO_DRY_RUN=true` (default)

### Endpoint /slo/health

Siempre 200. Devuelve slo_state, degradation_level, snapshot, violations.

## Error Taxonomy (FASE 29.4.4)

Clasificación de fallos para atribución precisa:

| Categoría | Subcategorías |
|-----------|---------------|
| Gateway | timeout, connection refused, model unloaded |
| Inference | GPU OOM, context length exceeded, generation error |
| Upstream | LM Studio error, llama.cpp crash, stream stall |
| Governance | tool block, policy violation, bash sanitizer |

## Parallel Tool Call Hardening (FASE 29.4.4-D)

- Límite de tools paralelas por request
- Timeout por tool call individual
- Rate limiting por tool type
- Deadlock detection

## Métricas Prometheus

14 métricas SLO + 4 grounding + 4 evidence guard + 80+ existentes = 100+ métricas `ailab_*`.

## Dashboards Grafana

15 dashboards en carpeta AI-LAB (datasource UID: PBFA97CFB590B2093).

TIER 1: latencia, perfiles, tools, errores, GPU, tokens.
TIER 2: memory, streaming, quality, cold starts, checksums.
SLO: Runtime Protection (14 paneles).

## Checkpoints

- CP-29.2-B-STREAMING-BURNIN-STABLE
- CP-29.3-THREE-MODEL-RUNTIME-STABLE
- CP-29.4-SLO-ENFORCEMENT-STABLE
- CP-29.4.4-ERROR-TAXONOMY-STABLE
- CP-29.4.4-C-SLO-HEALTH-ENDPOINT-STABLE
- CP-29.4.4-D-PARALLEL-TOOLCALL-HARDENING-STABLE
