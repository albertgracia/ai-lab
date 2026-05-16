---
title: "FASE 12 — Adaptive Learning & Self-Optimization"
summary: "Pattern learning engine, recommendation pipeline, context efficiency scoring, recall threshold optimizer, and supervised profile tuning."
order: 26
---

FASE 12 transforma AI-LAB de un runtime que recuerda y ejecuta bajo control a un
**sistema que aprende patrones operativos y propone mejoras reales**.

Regla sagrada: **NO autoejecuta cambios críticos**. Aprende → propone → policy
valida → Albert aprueba.

## Arquitectura

```
Pattern Learner ──→ Recommendation Engine ──→ Policy Gate ──→ Pending Queue
      ↑                      ↑                      ↑               │
  Qdrant + JSONL      Context Efficiency    optimizer_policy       │
                                                              Approve/Reject
                                                                   │
                                                              Sandbox Runner
                                                                   │
                                                              Audit Trail
```

## 12.0 — Action Types (bug fix)

`runtime/autonomous/action_types.py`

Constantes compartidas para evitar errores de nombres hardcodeados:

```python
BOOST_MODEL_WEIGHT = "boost_model_weight"
PENALIZE_MODEL_WEIGHT = "penalize_model_weight"
INCREASE_SPEED_BIAS = "increase_speed_bias"
DECREASE_CONTEXT_BUDGET = "decrease_context_budget"
TUNE_RECALL_CHARS = "tune_recall_chars"
TUNE_RECALL_SCORE = "tune_recall_score"
TUNE_RECALL_MEMORIES = "tune_recall_memories"
TUNE_PROFILE_MAX_TOKENS = "tune_profile_max_tokens"
```

`optimizer_policy.py` y `runtime_optimizer.py` ahora importan desde aquí,
eliminando el bug donde `boost_speed_weight` → `boost_model_weight`.

## 12.1 — Pattern Learning Engine

`runtime/memory/pattern_learner.py`

### Detectores existentes (mejorados)
| Patrón | Fuente | Dispara cuando... |
|---|---|---|
| `repeated_node_failure` | Qdrant incidents | ≥2 fallos críticos en mismo nodo |
| `high_critical_ratio` | Qdrant incidents | >30% de incidents son critical |
| `peak_failure_hour` | Qdrant incidents | Una hora UTC concentra >20% |
| `latency_trends` | routing_history | Deriva >10% en latencia reciente |

### Nuevos detectores FASE 12
| Patrón | Fuente | Dispara cuando... |
|---|---|---|
| `high_budget_recurring` | cognitive_history.jsonl | budget_used > 80% en ≥3 de últimas 10 entradas |
| `recall_bloat` | cognitive_history.jsonl | recall_chars medio > 2000 |
| `degrading_model` | routing_history.jsonl | success_rate reciente cae >10% vs global |
| `high_latency_model` | routing_history.jsonl | latencia reciente > 20s y sube >15% |
| `recurring_low_recall_quality` | cognitive_history + incidents | quality_score < 0.5 recurrente |
| `noisy_incidents` | Qdrant incidents | >50% de incidents son severidad info |

Entry point: `run_all(days=7)` → lista de patrones.

## 12.2 — Learning Metrics API

Endpoints en Live API (`:8084`):

| Endpoint | Descripción |
|---|---|
| `GET /api/learning/patterns` | Patrones detectados (run_all) |
| `GET /api/learning/recommendations` | Recomendaciones generadas |
| `GET /api/learning/model-performance` | Rendimiento por modelo |
| `GET /api/learning/context-efficiency` | Eficiencia de contexto |
| `GET /api/learning/recall-threshold?collection=&q=&limit=` | Threshold óptimo de recall |

## 12.3 — Recommendation Engine

`runtime/learning/recommendation_engine.py`

Convierte patrones + eficiencia en acciones propuestas:

```python
generate_recommendations(patterns, efficiency_results, model_performance)
```

Cada recomendación incluye:
- `evidence` — fuentes concretas (routing_history: 7 requests > 60s)
- `confidence` — 0-1 basado en datos observados
- `risk` — low / medium / high
- `expected_impact` — estimación cualitativa
- `rollback` — cómo deshacer el cambio

Mapeo patrón → acción:

| Patrón | Acción propuesta |
|---|---|
| `high_budget_recurring` | `tune_recall_chars` — reducir max_chars |
| `recall_bloat` | `tune_recall_chars` — reducir chars |
| `degrading_model` | `penalize_model_weight` — bajar peso |
| `high_latency_model` | `penalize_model_weight` — bajar peso |
| `repeated_node_failure` | `increase_speed_bias` — evitar nodo |
| `high_critical_ratio` | `decrease_context_budget` — reducir carga |
| `fast_bloat` (eficiencia) | `tune_profile_max_tokens` — compactar fast |
| `reasoning_starved` (eficiencia) | `tune_recall_memories` — ampliar reasoning |

## 12.4 — Queue Integration

`runtime_optimizer.py` actualizado con pipeline completo:

1. `_read_sources()` → routing + cognitive + model perf
2. `pattern_learner.run_all()` → patrones
3. `context_efficiency.batch_evaluate()` → scores
4. `recommendation_engine.generate_recommendations()` → propuestas
5. `_queue_recommendations()` → policy gate + pending queue
6. `_evaluate_outcomes()` → revisar ajustes aplicados hace >1h

## 12.5 — Adaptive Profile Tuning

Ajustes permitidos (inicialmente):
- `max_tokens` por perfil (fast/coding/reasoning/general)
- `recall max_chars` — chars de recall inyectados
- `recall min_score` — umbral de similitud
- `recall max_memories` — número máximo de memorias

No permitido todavía: temperatura, modelo principal, systemd, Docker, red, Cloudflare.

## 12.6 — Context Efficiency Scoring

`runtime/learning/context_efficiency.py`

Mide si el contexto inyectado aporta valor:

```
efficiency = utility / cost
```

| Etiqueta | Significado |
|---|---|
| `good` | efficiency ≥ 0.5 |
| `fair` | efficiency ≥ 0.2 |
| `poor` | efficiency < 0.2 |
| `failed` | request fallida |

Casos detectables:

| Detección | Qué significa | Recomendación |
|---|---|---|
| `overcontext` | Mucho contexto + mala calidad | Reducir recall chars o subir min_score |
| `undercontext` | Poco contexto + fallo | Ampliar recall limit |
| `fast_bloat` | Fast con contexto excesivo | Compactar perfil fast |
| `reasoning_starved` | Reasoning con baja calidad | Subir budget de recall |
| `wasted_context` | Budget alto + calidad baja | Reducir contexto total |

## 12.7 — Recall Threshold Optimizer

Funciones en `quality_assessment.py`:

```python
optimize_recall_threshold(results, current_threshold, precision_target=0.7)
```

Analiza la distribución de scores para encontrar el threshold óptimo que
maximiza precisión mientras minimiza ruido.
- Evalúa thresholds candidatos incluyendo puntos de corte naturales (score gaps > 0.05)
- Retorna `suggested_threshold`, `expected_precision`, `expected_noise`
- Se puede consultar vía `GET /api/learning/recall-threshold`

Además, `qdrant_store.recall()` ahora acepta parámetro `threshold` (default 0.0)
que se propaga a `search_collection()`.

## 12.8 — Learning Dashboard

`/ops/learning` — mismo estilo visual que `/ops/memory` y `/ops/commands`:

- **Patrones Detectados** — tarjetas por severidad con evidencia y recomendación
- **Recomendaciones** — tabla con acción, target, riesgo, confianza, impacto esperado y rollback
- **Eficiencia de Contexto** — promedio de efficiency, cost, utility, detecciones
- **Recall Threshold** — threshold actual vs sugerido, precisión esperada, contaminación

## 12.9 — Audit & Explainability

Cada recomendación incluye:

```json
{
  "evidence": [
    "routing_history: 7 fast requests > 60s",
    "cognitive_history: avg prompt_tokens 1275",
    "incidents: 3 high_latency"
  ],
  "expected_impact": "reduce latency 10-20%",
  "rollback": "restore previous profile config"
}
```

Todas las recomendaciones pasan por:
1. `optimizer_policy.validate_action()` — policy gate
2. `pending_adjustments.create_pending()` — cola de aprobación
3. `governance_audit.jsonl` — compliance trail
4. Qdrant incidents — trazabilidad semántica

## Archivos nuevos

| Archivo | Propósito |
|---|---|
| `runtime/autonomous/action_types.py` | Constantes de acciones (evita bugs) |
| `runtime/learning/context_efficiency.py` | Context efficiency scoring |
| `runtime/learning/recommendation_engine.py` | Patrones → recomendaciones |
| `apps/ialab-docs/src/pages/ops/learning.astro` | Learning dashboard |

## Archivos modificados

| Archivo | Cambio |
|---|---|
| `runtime/autonomous/optimizer_policy.py` | Usar action_types en vez de strings |
| `runtime/autonomous/runtime_optimizer.py` | Pipeline completo + evaluate_outcomes |
| `runtime/memory/pattern_learner.py` | +6 nuevos detectores + run_all() |
| `runtime/memory/quality_assessment.py` | +optimize_recall_threshold() |
| `runtime/memory/qdrant_store.py` | +threshold param en recall() |
| `runtime/state/live_api.py` | +5 endpoints learning API |
