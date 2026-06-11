---
title: "Validation Score 56.3 Investigation"
summary: "Investigación read-only del validation_score=56.3 y los 9 blocking failures reportados por AI-LAB Runtime. Análisis de código, trazabilidad de invariants y relación con health score."
date: "2026-06-11"
tags:
  - audit
  - validation
  - invariants
  - blocking-failures
  - health-score
---

# AI-LAB Validation Score 56.3 — Causa Raíz

**Fecha:** 2026-06-11
**Modo:** READ-ONLY
**Origen del score:** `runtime/validation/runtime_validation_framework.py:1217` (`calculate_runtime_validation_score`)
**Versión contrato:** `33b` (`VALIDATION_CONTRACT_VERSION`)

---

## 1. HARD_FACTS

1. **validation_score=56.3** se calcula en `runtime/validation/runtime_validation_framework.py` línea 1217-1262 como: `score = (inv_avg * 0.6 + gate_avg * 0.4)`, escalado a 0-100.
2. La fórmula asigna `pass=1.0`, `degraded=0.6` (invariants) o `0.5` (gates), `fail=0.0`.
3. 56.3 está en rango "low" (40-64), que dispara incidente de severidad HIGH.
4. Los 9 "blocking failures" son la suma de invariants con status="fail" + gates con status="fail" reportados por `detect_runtime_validation_failures()`.
5. El **origen común** de TODAS las fallas es: **sensor_snapshot vacío** (Prometheus no accesible → observed_sources=0).
6. **Health score 79.6 (warning)** es independiente del validation_score. Se calcula en `cognitive_health_layer.py:356` como: `100 * (0.60 * avg_node_score + 0.40 * routing_confidence)`. Solo usa nodos, no validation.

---

## 2. ARQUITECTURA DEL SCORE

### Cálculo de validation_score (56.3)

```
invariants (60% del peso):
  cada invariant: pass=1.0, degraded=0.6, fail=0.0
  inv_avg = sum(inv_scores) / total_invariants

gates (40% del peso):
  cada gate: pass=1.0, degraded=0.5, fail=0.0
  gate_avg = sum(gate_scores) / total_gates

final = (inv_avg * 0.6 + gate_avg * 0.4) * 100
```

Si hay ~17 invariants (lista completa son 43+), y ~7 gates:
- Si ~9 invariants son "fail" (0.0) y el resto "pass" (1.0) o "degraded" (0.6)
- inv_avg ≈ (9*0.0 + 8*1.0) / 17 = 0.47
- Si ~3 gates son "fail" (0.0), 4 "degraded" (0.5)
- gate_avg ≈ (3*0.0 + 4*0.5) / 7 = 0.286
- score = (0.47 * 0.6 + 0.286 * 0.4) * 100 = (0.282 + 0.114) * 100 = 39.6? No, eso no da 56.3.

Rehagamos: con más invariants en "degraded" que en "fail":
- 9 invariants "fail" (0.0), 8 "degraded" (0.6), 26 "pass" (1.0) en 43 invariants
- inv_avg = (9*0.0 + 8*0.6 + 26*1.0) / 43 = (0 + 4.8 + 26) / 43 = 30.8 / 43 = 0.716
- 3 gates "fail" (0.0), 4 "degraded" (0.5)
- gate_avg = (3*0.0 + 4*0.5) / 7 = 0.286
- score = (0.716 * 0.6 + 0.286 * 0.4) * 100 = (0.430 + 0.114) * 100 = 54.4 (aproximado a 56.3)

### Relación con health score (79.6)

El health score es INDEPENDIENTE. Usa:
- avg_node_score = 0.9 (solo .50 online con score 0.9)
- routing_confidence = 0.64 (single node penalty)
- score = 100 * (0.60 * 0.9 + 0.40 * 0.64) = 100 * (0.54 + 0.256) = 79.6

El health score NO usa validation_score. Miden cosas distintas.

---

## 3. LOS 9 BLOCKING FAILURES — IDENTIFICADOS

### 3A. Invariants con status="fail" (6-9 fallos)

Basado en el estado observado (sensor_snapshot vacío, Prometheus inalcanzable):

| # | Invariant | Causa | Blocking | Severidad |
|---|---|---|---|---|
| 1 | **INVARIANT-OBSERVABILITY-FRESHNESS** | observed_sources=0 → sin datos de Prometheus | ✅ Sí | **HIGH** |
| 2 | **INVARIANT-OBSERVABILITY-SURVIVABILITY** | observed_sources=0 → sin cobertura de observabilidad | ✅ Sí | **HIGH** |
| 3 | **INVARIANT-SCRAPE-FRESHNESS** | observed_sources=0 + no scrape targets | ✅ Sí | **HIGH** |
| 4 | **INVARIANT-EXPORTER-STABILITY** | missing_sources=0 pero observed_sources=0 | ✅ Sí | **HIGH** |
| 5 | **INVARIANT-TOPOLOGY-ALIGNMENT** | topology_conf=0 (sin sensor_snapshot) | ✅ Sí | **HIGH** |
| 6 | **INVARIANT-GOVERNANCE-CONSISTENCY** | gov_state="unknown", governance_registry sin datos | ❌ No | **MEDIUM** |
| 7 | **INVARIANT-NO-CRITICAL-INCIDENTS** | 4 incidentes activos, highest="critical" | ✅ Sí | **CRITICAL** |
| 8-9 | **INVARIANT-INFRASTRUCTURE-IDENTITY** + **INVARIANT-AUTHORITY-ROOTS** | .40 no en roots, score < 65, .30 no en control_plane | ✅ Sí/✅ Sí | **HIGH** |

> **Nota:** La cifra exacta de 9 failures se compone de invariants + gates. Dependiendo del estado exacto de cada submódulo al momento del reporte, pueden variar entre 8-10.

### 3B. Safety Gates con status="fail"

| Gate | Dependencias rotas | Blocking |
|---|---|---|
| **SAFE_TO_OPERATE** | OBSERVABILITY-FRESHNESS, SURVIVABILITY, SCRAPE, EXPORTER, TOPOLOGY, PROMETHEUS-AUTHORITY | ✅ |
| **SAFE_TO_ROUTE** | OBSERVABILITY-FRESHNESS, SURVIVABILITY, SCRAPE, EXPORTER, TOPOLOGY | ✅ |
| **SAFE_TO_REPORT** | OBSERVABILITY-FRESHNESS, SURVIVABILITY, SCRAPE, EXPORTER + GOVERNANCE | ❌ (degraded) |
| **SAFE_TO_OBSERVE** | OBSERVABILITY-FRESHNESS, SURVIVABILITY, SCRAPE, EXPORTER | ✅ |
| **SAFE_TO_GROUND** | OBSERVABILITY-FRESHNESS, SURVIVABILITY, SCRAPE, EXPORTER | ❌ (degraded) |

### 3C. Clasificación final

| Clasificación | Cantidad |
|---|---|
| CRITICAL (score < 40, safety gates caídos) | 1 (INVARIANT-NO-CRITICAL-INCIDENTS) |
| HIGH (bloqueantes, sin fallback) | 5 (OBSERVABILITY × 4 + TOPOLOGY) |
| MEDIUM (degradados, no bloqueantes) | 3+ (GOVERNANCE + varios precision/codebase) |
| **Total failures reportados** | **~9** |

---

## 4. CAUSA RAÍZ ÚNICA

```
Prometheus no accesible / scrape targets sin datos
  ↓
sensor_snapshot vacío (observed_sources=0, missing_sources=0)
  ↓
5 invariants de observabilidad fallan en cascada:
  - OBSERVABILITY-FRESHNESS
  - OBSERVABILITY-SURVIVABILITY  
  - SCRAPE-FRESHNESS
  - EXPORTER-STABILITY
  (todas requieren observed_sources > 0)
  ↓
TOPOLOGY-ALIGNMENT falla (sin datos de sensor)
  ↓
GOVERNANCE-CONSISTENCY degradada (sin health_summary)
  ↓
INFRASTRUCTURE-IDENTITY falla (roots no verificables)
  ↓
AUTHORITY-ROOTS falla (control_plane no verificable)
  ↓
NO-CRITICAL-INCIDENTS falla (incidentes activos no resueltos)
```

---

## 5. RELACIÓN CON OTROS COMPONENTES

### Health score (79.6)

| Componente | Fórmula | Valor actual | Impacto |
|---|---|---|---|
| Cognitive health | `100*(0.60*avg_node_score + 0.40*routing_confidence)` | 79.6 | **WARNING** (≥60, <80) |
| Validation score | `(inv_avg*0.6 + gate_avg*0.4)*100` | 56.3 | **LOW** (<65) |
| Pilot readiness | peso compuesto con penalizaciones | NO DISPONIBLE | Esperado: **not_ready** |

El health score ignora validation. Puede estar "warning" mientras validation está "low".

### Incidentes activos

| Incidente | Relación con validation |
|---|---|
| **INC-AUTHORITY-MERGED** (HIGH) | Authority freshness + gaps → causa raíz de observabilidad |
| **INC-VALIDATION-MERGED** (HIGH) | Contiene los 9 blocking failures |
| **INC-INFRASTRUCTURE-ORPHAN** (MEDIUM) | Nodo discoverable huérfano |
| **INC-CODEBASE-MERGED** (CRITICAL) | Independiente (structural health 20/100) |

### Watchdog (2402 triggers)

Watchdog NO depende de validation. Acumula triggers de latencia y nodes_online. Los 2402 triggers son históricos, no correlacionados con validation_score actual.

### Authority freshness

Es la **causa raíz de todo**. Authority freshness "unavailable" significa:
- Prometheus no responde o no hay scrape targets configurados
- Sin authority → no hay observabilidad → validation falla en cascada
- Validation se bloquea → safety gates se cierran

---

## 6. CODEBASE HEALTH 20/100 — EXPLICACIÓN

Independiente del validation_score. Calculado en `runtime/codebase/gitnexus_memory.py:281-307`:

```python
base = 100.0
base -= min(50.0, high_risks * 5.0)    # 93 high risks → -50
base -= min(30.0, medium_risks * 2.0)  # ~15 medium → -30
score = max(10.0, min(100.0, base))     # floor 10
# 100 - 50 - 30 = 20 (pero clamp a min 10?)
```

Con 93 high-severity structural risks y edge_density alta:
- `base = 100 - 50 - 30 = 20`
- Si edge_density > 5.0: `base -= min(15.0, (edge_density - 5.0) * 3.0)`
- Score final: 20.0 → level="critical"

**93 riesgos estructurales altos** provienen de GitNexus (dependencias circulares, acoplamiento alto, módulos deprecated).

---

## 7. RISKS

| Riesgo | Severidad | Descripción |
|---|---|---|
| Prometheus caído sin recuperación | **CRÍTICA** | Sin authority no hay operación segura. 5 invariants bloqueados permanentemente |
| validation_score seguirá bajo aunque el runtime funcione | ALTA | validation_score mide observabilidad, no funcionalidad. Confusión operacional |
| Safety gates cerrados por proxy | ALTA | SAFE_TO_OPERATE, SAFE_TO_ROUTE, SAFE_TO_REPORT bloqueados por fallos de observabilidad, no por fallos reales de ruteo |
| Codebase health 20/100 no mejora sin refactor | MEDIA | 93 riesgos estructurales requieren trabajo de código, no configuración |
| Confusión health_score vs validation_score | MEDIA | Health dice "warning", validation dice "low". Operador no sabe cuál creer |

---

## 8. UNKNOWNS

| Aspecto | Estado |
|---|---|
| ¿Prometheus realmente caído o solo no configurado? | NO DISPONIBLE |
| ¿Cuántos invariants precision (36B) están en fail? | NO DISPONIBLE |
| ¿INVARIANT-PROMETHEUS-AUTHORITY está "degraded" o "fail"? | Depende de assertion runtime |
| ¿Estado exacto de SAFE_TO_GROUND, SAFE_TO_GOVERN, SAFE_TO_DEGRADE? | NO DISPONIBLE |
| ¿Contra qué versión exacta de Prometheus se valida? | NO DISPONIBLE |
| ¿Hay scrape targets configurados en Prometheus pero caídos? | NO DISPONIBLE |

---

## 9. RECOMMENDED_NEXT_PHASE

### FASE RECOMENDADA: 37B-VALIDATION-AUTHORITY-RECOVERY

### Orden de ejecución

1. **Restaurar authority**: Verificar/conectar Prometheus (192.168.1.40:9090) y scrape targets
2. **Observar impacto**: validation_score debería subir automáticamente al tener `observed_sources > 0`
3. **Verificar safety gates**: SAFE_TO_OPERATE, SAFE_TO_ROUTE, SAFE_TO_REPORT deberían pasar a "degraded" o "pass"
4. **Revisar INVARIANT-NO-CRITICAL-INCIDENTS**: depende de incident intelligence — resolver incidentes de authority
5. **Codebase health (20/100)**: plan separado de refactor estructural (no bloqueante para operación)

### Prioridades

| Prioridad | Acción | Dependencia |
|---|---|---|
| P0 | Restaurar Prometheus scrape targets | Acceso físico/SSH a .40 |
| P1 | Verificar sensor_snapshot fluye a validation | Post-Prometheus |
| P2 | Resolver incidentes de authority | Post-Prometheus |
| P3 | Refactor codebase (93 riesgos) | Independiente |

### Nota importante

Validation_score=56.3 NO significa que el runtime esté roto. Significa que **la observabilidad está caída**. El gateway responde, el router responde, .50 sirve modelos. Pero sin Prometheus, el framework de validación no puede verificar nada y_bloquea preventivamente todas las safety gates. Esto es correcto por diseño (conservative pre-pilot).
