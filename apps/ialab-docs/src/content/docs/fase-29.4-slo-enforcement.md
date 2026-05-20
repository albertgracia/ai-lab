---
title: "FASE 29.4 — SLO Enforcement & Adaptive Runtime Protection"
summary: "De SLO pasivo a runtime auto-protegido. SLO enforcement engine con estados GREEN/YELLOW/RED, adaptive degradation (LEVEL 0-3), priority lanes, adaptive concurrency y circuit breakers observables. DRY RUN primero — toda accion es reversible y feature-flagged."
order: 78
---

## Objetivo

Evolucionar de SLO **pasivo** (solo observar metricas en Grafana) a SLO **activo** (reaccionar automaticamente a degradaciones) sin romper el streaming real, gateway hardening, routing tightening ni el three-model runtime establecido en FASE 29.3.

El runtime ahora puede:
- Detectar cuando esta degradado (TTFB alto, GPU sobrecargada, timeouts)
- Reaccionar automaticamente (forzar llama, proteger qwen, reducir concurrencia)
- Recuperarse cuando la presion baja (cooldown de 30s)
- Exponer todo via metricas Prometheus + dashboard dedicado

Todo es **reversible** via feature flags. Default: dry-run.

## Arquitectura

```
SLOState (deques sliding window por modelo)
  ├─ TTFB readings (maxlen=300 ≈ 5min a 1req/s)
  ├─ Timeout readings (maxlen=600 ≈ 10min)
  ├─ GPU / VRAM pressure (ultimo valor)
  └─ Gateway crashes / orphan streams (acumuladores)

RuntimeSLOManager (evaluacion cada 10s)
  ├─ GREEN  (0): sin violaciones
  ├─ YELLOW (1): 1+ SLO en warning
  └─ RED    (2): 1+ SLO en critical

DegradationManager (con anti-flapping 30s + cooldown 30s)
  ├─ LEVEL 0 — NORMAL: routing completo
  ├─ LEVEL 1 — LIGHT: forced llama + qwen protection
  ├─ LEVEL 2 — HEAVY: pause qwen (observable, no auto-activo)
  └─ LEVEL 3 — EMERGENCY: llama-only (observable, no auto-activo)

AdaptiveConcurrency
  └─ qwen parallel: 2 (GPU<70%) → 1 (GPU 70-90%) → 1 (GPU>90%)
  └─ llama parallel: 3 → 2 (GPU>90%)

PrioritySlotManager
  └─ Lane 1: 2 slots dedicados (minimal, observe)
  └─ Lane 2+3: pool compartido de 2 slots

CircuitBreakerRegistry
  └─ Por modelo: CLOSED → OPEN (3 fallos/60s) → HALF_OPEN (30s)
  └─ Observable: no bloquea requests en esta fase
```

## Feature Flags

| Flag | Default | Proposito |
|------|---------|-----------|
| `AI_LAB_ENABLE_SLO_ENFORCEMENT` | `false` | Activa enforcement real. Sin esto, todo es dry-run. |
| `AI_LAB_SLO_DRY_RUN` | `true` | Modo observacion: evalua SLO, emite metricas, NO actua. |

Establecer via env al iniciar el gateway, misma convencion que `AI_LAB_REAL_STREAMING`.

**DRY RUN obligatorio primero.** Solo activar enforcement tras validar dashboards durante al menos 15 minutos de burn-in.

## Modulo: `runtime/slo/`

```
runtime/slo/
├── __init__.py              # Export publico
├── runtime_slo.py           # SLOState + RuntimeSLOManager
├── degradation.py           # DegradationManager (4 niveles)
├── concurrency.py           # AdaptiveConcurrency
├── priority_lanes.py        # PrioritySlotManager
├── circuit_breakers.py      # ModelCircuitBreaker + Registry
└── metrics.py               # 14 metricas Prometheus nuevas
```

### `runtime_slo.py`

**`SLOState`** (thread-safe, daemon thread):
- `ttfb_readings: deque[float]` — sliding window 300 entries (~5 min)
- `timeout_readings: deque[bool]` — sliding window 600 entries (~10 min)
- `gpu_util`, `vram_pressure` — ultimo valor conocido
- `gateway_crashes`, `orphan_streams` — acumuladores
- `record_ttfb(ms)`, `record_timeout(is_timeout)`, `record_gpu_state(util, vram)`
- `get_snapshot()` → `{ttfb_p50, ttfb_p95, timeout_rate, gpu_util, ...}`
- `_compute_p50()`: O(n log n) sobre deque de 300 — sorted + mid index
- `_compute_p95()`: sorted + 95th percentile index
- `_compute_timeout_rate()`: `sum(timeouts) / len(readings)`

**`RuntimeSLOManager`**:
- `evaluate_slo_state()` → 0/1/2 — evalua cada 10s contra `SLO_TARGETS`
- `get_runtime_health()` → `{slo_state, degradation_level, dry_run, snapshot, violations}`
- `trigger_degradation_mode(level)` / `clear_degradation_mode()`
- `update_metrics()` — actualiza metricas Prometheus desde snapshot si no dry-run

**`SLO_TARGETS`** (constantes del modulo):

| SLO | Warning | Critical |
|-----|---------|----------|
| ttfb_p50 | 800ms | 1200ms |
| ttfb_p95 | 5000ms | 10000ms |
| timeout_rate | 0.02 (2%) | 0.05 (5%) |
| gpu_util | 0.85 (85%) | 0.95 (95%) |
| vram_pressure | 0.90 (90%) | 0.97 (97%) |
| gateway_crashes | 0 | 1 |
| orphan_streams | 0 | 1 |

### `degradation.py`

**`DegradationManager`** (thread-safe):

Niveles:

| Level | Nombre | Triggers | Acciones |
|-------|--------|----------|----------|
| 0 | NORMAL | — | Routing completo |
| 1 | LIGHT | TTFB p95>10s **o** GPU util>92% | `greetings → llama obligatorio`; `bloquear escalation a qwen`; `qwen parallel 2→1` |
| 2 | HEAVY | timeout_rate>5% **o** VRAM>97% **o** stream backlog | `bloquear observe/report/cognitive`; `pausa temporal qwen routing` (observable, NO auto-activo) |
| 3 | EMERGENCY | gateway instability **o** orphan streams **o** timeout storms repetidos | `force llama-only`; `rechazar prompts > 500 chars`; `deshabilitar embeddings` (observable, NO auto-activo) |

Anti-flapping: minimo 30s entre transiciones de nivel. Cooldown: 30s de estado saludable continuo antes de bajar de nivel.

Metodos de consulta (usados por gateway):
- `should_force_llama(level)` → True si level>=3
- `should_block_qwen_escalation(level)` → True si level>=1
- `should_pause_qwen_routing(level)` → True si level>=2
- `should_block_observe_report(level)` → True si level>=2
- `should_reject_long_prompts(level)` → True si level==3
- `record_qwen_protection(reason, dry_run)` — log + metrica
- `record_llama_forced(reason, dry_run)` — log + metrica

### `concurrency.py`

**`AdaptiveConcurrency`** (thread-safe):

Constantes:
- `QWEN_BASE_PARALLEL = 2`, `QWEN_MIN_PARALLEL = 1`
- `LLAMA_BASE_PARALLEL = 3`, `LLAMA_MIN_PARALLEL = 2`

Logica:
- `_compute_qwen_parallel()`: degradation>=2→0,>=1→1, GPU>90% o VRAM>97%→1, timeout>5%→1, GPU>70%→2, else→2
- `_compute_llama_parallel()`: degradation>=3→3 (llama full), GPU>90%→2, else→3
- `get_streams_max()`: qwen_parallel + llama_parallel (total concurrent streams)

### `priority_lanes.py`

**`PrioritySlotManager`** (thread-safe):

| Lane | Rutas | Slots dedicados |
|------|-------|----------------|
| 1 — Critical/Fast | minimal, observe, tool_fastpath | 2 slots |
| 2 — Cognitive | cognitive, learning, report | 1 slot (compartido con Lane 3) |
| 3 — Background | embeddings, memory indexing | 1 slot (compartido con Lane 2) |

Sin worker pools, sin preemption. Lane 1 siempre tiene prioridad en el proximo slot disponible via `acquire_slot("critical")`.

Funcion auxiliar `get_lane_for_route(route_family)` → `"critical" | "cognitive"`.

### `circuit_breakers.py`

**`ModelCircuitBreaker`** (por modelo, thread-safe):
- CLOSED (0): operacion normal
- OPEN (2): 3 fallos consecutivos en ventana de 60s
- HALF_OPEN (1): prueba cada 30s. 1 exito → CLOSED. 1 fallo → OPEN.

**`CircuitBreakerRegistry`**: singleton que gestiona breakers para todos los modelos.
- `record_success(model)`, `record_failure(model)`, `should_allow(model)`, `get_all_states()`

**En esta fase: NO bloquean requests.** Solo exponen estado via `ailab_circuit_breaker_state`. El gateway puede decidir si usarlos.

## Integracion en Gateway

### `openai_gateway.py` (5 puntos de integracion)

1. **Startup** (linea 63): import try/except del modulo SLO. Si falla, `_HAVE_SLO = False` y todo el SLO se desactiva silenciosamente.

2. **TTFB recording** (linea 1140): tras medir TTFB, registrar en `_slo_state.record_ttfb(ttfb_ms)` + GPU state.

3. **Degradation model override** (linea 1096): tras seleccionar modelo, comprobar nivel de degradacion:
   - EMERGENCY → forzar llama-3.1-8b siempre
   - HEAVY + qwen seleccionado → redirigir a llama
   - LIGHT + ruta minimal/observe con qwen → bloquear escalation

4. **Periodic evaluation** (linea 1263): tras completar request, llamar `evaluate_slo_state()`, pasar a `DegradationManager.evaluate_and_apply()`, actualizar `AdaptiveConcurrency`, emitir metricas, y llamar `stream_sanitizer.set_max_streams()`.

5. **Circuit breaker recording**: en exito (non-stream + stream paths) y error (RequestException, Exception).

### `stream_sanitizer.py`

- `set_max_streams(limit)` — override externo para `MAX_CONCURRENT_STREAMS`
- `_get_max_streams()` — lee override o devuelve default (3)
- `_acquire_slot()` — usa `_get_max_streams()` en vez de la constante

### Nuevo endpoint `GET /slo/health`

```bash
curl -s http://192.168.1.30:8008/slo/health | jq .
```

Respuesta:
```json
{
  "slo_state": "green",
  "slo_state_code": 0,
  "degradation_level": 0,
  "dry_run": true,
  "enabled": false,
  "snapshot": {
    "ttfb_p50": 804.0,
    "ttfb_p95": 3120.0,
    "timeout_rate": 0.0,
    "gpu_util": 0.3,
    "vram_pressure": 0.5,
    "gateway_crashes": 0,
    "orphan_streams": 0,
    "stream_backlog": 0,
    "active_streams": 0
  },
  "violations": []
}
```

## Nuevas Metricas Prometheus (14)

| Metrica | Tipo | Labels | Proposito |
|---------|------|--------|-----------|
| `ailab_runtime_slo_state` | Gauge | — | 0=GREEN, 1=YELLOW, 2=RED |
| `ailab_runtime_degradation_level` | Gauge | — | 0-3 |
| `ailab_runtime_timeout_rate` | Gauge | — | Timeout rate en ventana actual |
| `ailab_runtime_vram_pressure` | Gauge | — | Presion VRAM (0.0-1.0) |
| `ailab_runtime_gpu_pressure` | Gauge | — | Presion GPU (0.0-1.0) |
| `ailab_runtime_priority_lane_total` | Counter | lane | Requests procesados por lane |
| `ailab_runtime_emergency_mode_total` | Counter | reason | Activaciones de emergency mode |
| `ailab_runtime_qwen_protection_total` | Counter | reason | Eventos de proteccion a qwen |
| `ailab_runtime_llama_fastpath_forced_total` | Counter | reason | Llama forzado por degradacion |
| `ailab_runtime_stream_backlog` | Gauge | — | Requests esperando slot de stream |
| `ailab_circuit_breaker_state` | Gauge | model | 0=closed, 1=half, 2=open |
| `ailab_slo_violations_total` | Counter | slo_name, level | Violaciones de SLO |
| `ailab_runtime_qwen_parallel` | Gauge | — | Limite paralelo actual de qwen |
| `ailab_runtime_concurrent_streams` | Gauge | — | Streams activos actualmente |

## Dashboard: AI-LAB Runtime Protection

14 paneles en el dashboard:

| Panel | Tipo | Metrica | Threshold |
|-------|------|---------|-----------|
| Runtime SLO State | Stat | `ailab_runtime_slo_state` | 0=GREEN, 1=YELLOW, 2=RED |
| Degradation Level | Stat | `ailab_runtime_degradation_level` | 0-3 con thresholds |
| GPU Pressure | Gauge | `ailab_runtime_gpu_pressure` | 85%, 95% |
| VRAM Pressure | Gauge | `ailab_runtime_vram_pressure` | 90%, 97% |
| Timeout Rate | Gauge | `ailab_runtime_timeout_rate` | 2%, 5% |
| Forced Llama Routing | Timeseries | `rate(ailab_llama_fastpath_forced_total[5m])` | — |
| Qwen Protection Events | Timeseries | `rate(ailab_qwen_protection_total[5m])` | — |
| Emergency Mode Activations | Timeseries | `rate(ailab_emergency_mode_total[5m])` | — |
| Priority Lane Distribution | Barchart | `rate(ailab_priority_lane_total[5m])` | — |
| Stream Backlog | Timeseries | `ailab_runtime_stream_backlog` | — |
| Dynamic Qwen Parallel | Stat | `ailab_runtime_qwen_parallel` | 0-2 |
| Concurrent Streams | Timeseries | `ailab_runtime_concurrent_streams` | — |
| SLO Violations | Timeseries | `rate(ailab_slo_violations_total[5m])` | — |
| Circuit Breaker States | Table | `ailab_circuit_breaker_state` | closed/half/open |

Provisioning JSON: `/opt/ai-lab/dashboards/ailab-runtime-protection.json`
Datasource UID: `PBFA97CFB590B2093` (mismo que los otros dashboards AI-LAB)

## Burn-in Plan

### FASE A — DRY RUN (15 min, 3 workers)

Config:
```bash
AI_LAB_SLO_DRY_RUN=true
AI_LAB_ENABLE_SLO_ENFORCEMENT=false
```

Objetivo: verificar que metricas nuevas aparecen en /metrics y dashboard, transiciones GREEN/YELLOW son visibles, 0 side effects en el runtime.

PASS criteria:
- `ailab_runtime_slo_state`, `ailab_runtime_degradation_level` visibles en `:8008/metrics`
- Dashboard AI-LAB Runtime Protection muestra datos
- SLO state transiciones GREEN↔YELLOW visibles bajo carga controlada
- 0 cambios en comportamiento de routing, streaming o gateway

### FASE B — LIGHT ENFORCEMENT (30 min, 3 workers)

Config:
```bash
AI_LAB_SLO_DRY_RUN=false
AI_LAB_ENABLE_SLO_ENFORCEMENT=true
```

Solo LEVEL 1 activo: forced llama routing + qwen protection + qwen parallel 2→1.

PASS criteria:
- Degradacion LEVEL 1 se activa bajo GPU>92%
- Greetings se redirigen a llama bajo degradacion
- Escalation a qwen se bloquea bajo degradacion
- Degradacion se revierte al bajar la carga (cooldown 30s)
- TTFB se mantiene estable (no empeora por el enforcement)
- 0 crashes, 0 orphan streams, 0 qwen3.6 usage

### HEAVY/EMERGENCY — Solo observables

LEVEL 2 y LEVEL 3 implementados, metricados y feature-flagged pero **NO auto-activos**.
Se activaran en fases futuras tras validar comportamiento.

## Prohibiciones en esta iteracion

- ❌ Auto-restart runtime
- ❌ Self-healing loops
- ❌ Autonomous scaling
- ❌ Planner/executor (FASE 28.x)
- ❌ Write sandbox
- ❌ Async/multiprocessing refactor
- ❌ Multi-GPU orchestration

## Compatibilidad FASE 28.x

`runtime/slo/` es completamente desacoplado de `runtime/agentic/`. No toca planner, executor, governance pipeline ni sandbox write. Los circuit breakers, priority lanes y concurrency manager son wrappers sobre infra existente y no interfieren con el pipeline agentic.

## Checkpoint

`CP-29.4-SLO-ENFORCEMENT-STABLE`
