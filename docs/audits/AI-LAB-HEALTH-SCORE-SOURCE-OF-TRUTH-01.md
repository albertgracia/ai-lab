# AI-LAB-HEALTH-SCORE-SOURCE-OF-TRUTH-01

## Resultado: PASS

---

## Resumen ejecutivo

Se identificaron **3 sistemas de health score** coexistiendo en AI-LAB, no 2 como se
hipotetizaba originalmente. El drift de ~100 puntos no es un bug, sino el resultado
esperado de medir **aspectos distintos** de la salud del sistema.

| Sistema | Métrica | Rango | Valor actual | Propósito |
|---------|---------|-------|-------------|-----------|
| A — `health_score.py` | (ninguna en Prometheus) | 0-100 | ~50-100 | **LEGACY** — diagnóstico por subprocess |
| B — `cognitive_health_layer.py` | `ailab_cognitive_health_score` | 0-100 | **0.0** | Estado del layer cognitivo (datos de routing) |
| C — recording rule | `ai_lab:runtime_health_score` | 0-1 → *100 | **100** | Salud de infraestructura SLO |

---

## FASE 0 — Inventario

### Sistema A: `health_score.py`

| Atributo | Valor |
|----------|-------|
| Ruta | `/opt/ai-lab/runtime/analytics/health_score.py` |
| Líneas | 76 |
| Última modificación | 16 May 2026 |
| Productor | `control_plane.py` (línea 27) |
| Consumidores | Solo `control_plane.py` (línea 52) |

### Sistema B: `cognitive_health_layer.py`

| Atributo | Valor |
|----------|-------|
| Ruta | `/opt/ai-lab/runtime/health/cognitive_health_layer.py` |
| Líneas | ~545 |
| Última modificación | (en repo) |
| Productor | `build_cognitive_health_prometheus_metrics()` → `ailab_cognitive_health_score` |
| Consumidores | `runtime_api_routes.py`, `openai_gateway.py`, `hotspot_history.py`, `critical_path_analysis.py`, `graph_runtime_correlation.py`, Prometheus, Grafana |

### Sistema C: Recording Rule `ai_lab:runtime_health_score`

| Atributo | Valor |
|----------|-------|
| Fuente | `ai-lab-cognitive-alerts.yml` (Prometheus recording rule) |
| Fórmula | `(slo_gateway + slo_lmstudio + slo_registry + routable_models>1 + guard_state<2) / 5` |
| Rango | 0-1 |
| Consumidores | Grafana (RHS Cross-check, Drift Indicator, Drift Graph), alerta AI-LABRuntimeHealthScoreDrift |

### Tabla completa de referencias

| Archivo | Sistema | Rol |
|---------|---------|-----|
| `runtime/analytics/health_score.py` | A | Productor LEGACY |
| `runtime/control/control_plane.py` | A | Único consumidor |
| `runtime/health/cognitive_health_layer.py` | B | Productor CANÓNICO |
| `runtime/gateway/openai_gateway.py` | B | Metric exporter (`_cached_cognitive_health`) |
| `runtime/gateway/runtime_api_routes.py` | B | Serve `/runtime/health` endpoint |
| `runtime/hotspot_history/hotspot_history.py` | B | Drift tracking |
| `runtime/critical_path/critical_path_analysis.py` | B | Critical path weighting |
| `runtime/correlation/graph_runtime_correlation.py` | B | Health correlation |
| `runtime/slo/runtime_slo.py` | C | SLO metric provider |
| `monitorizacion/prometheus/rules/ai-lab-cognitive-alerts.yml` | C | Recording + alerting rules |
| `stacks/observability/grafana/provisioning/dashboards/active/` | B+C | Dashboard panels |

---

## FASE 1 — Trazabilidad

### Sistema A: `health_score.py` → `calculate()`

**Fórmula:**
```
score = 100
  - max(0, gpu_total - gpu_online) * 30    # -30 por GPU offline
  - 15 if Gateway unreachable                # subprocess curl
  - 10 if Router unreachable                 # subprocess curl
  - 10 if Prometheus unreachable             # subprocess curl
  -  5 if <5 Docker containers running       # subprocess docker ps
  - 20 if latency > 30s o -10 si > 10s       # subprocess curl /metrics
score = clamp(0, 100)
```

**Dependencias:**
- `cluster_state.json` (lectura de archivo)
- `subprocess.run(["curl", ...])` × 3 llamadas
- `subprocess.run(["docker", "ps", ...])` × 1 llamada

**Bug detectado:** `http://localhost:8008/metricsmetrics` — URL con "metrics" duplicado.

**Rango esperado:** 0-100.

### Sistema B: `cognitive_health_layer.py` → `build_cognitive_health_snapshot()`

**Fórmula:**
```
overall = 100 * (0.60 * avg_node_score + 0.40 * routing_confidence)

Donde:
  node_score (0-1) = 0.50 baseline
    + 0.20 si online
    - 0.40 si offline
    + (success_rate - 0.5) * 0.60
    + delta_latency (0.20 excelente ... -0.20 muy alta)

  routing_confidence (0-1) = 0.50 + (avg_score - 0.5) * 0.60
    + 0.15 si >= 2 nodos online
    - 0.10 si 1 solo nodo
```

**Dependencias:**
- `control_plane.get_control_nodes()` — lista de nodos del cluster
- `routing_history.read_route_history()` — historial de rutas (ventana 60min)
- `routing_history.stats_by_node()` — estadísticas por nodo
- `sensor_fusion.SensorFusionEngine()` — estado de GPUs
- `telemetry.gateway_metrics.get_latency_stats()` — latencias P50/P95

**Rango esperado:** 0-100.

### Sistema C: Recording Rule `ai_lab:runtime_health_score`

**Fórmula:**
```
(ailab_slo_gateway_health + ailab_slo_lmstudio_health
 + ailab_slo_registry_consistency
 + (ailab_registry_routable_models_total > bool(1))
 + (ailab_federation_guard_state < bool(2))) / 5
```

**Dependencias:**
- `runtime_slo.SloManager` — produce `ailab_slo_gateway_health`, `ailab_slo_lmstudio_health`, `ailab_slo_registry_consistency`
- Gateway `/metrics` — expone `ailab_registry_routable_models_total`, `ailab_federation_guard_state`

**Rango esperado:** 0-1 (multiplicado por 100 en dashboards → 0-100).

---

## FASE 2 — Mapa de consumidores

```
health_score.py (A) ──→ control_plane.py ──→ "health_score" en output de control_plane
                    (sin métrica Prometheus)

cognitive_health_layer.py (B) ──→ runtime_api_routes.py ──→ /runtime/health endpoint
                              ──→ openai_gateway.py ──→ METRICS: ailab_cognitive_health_score
                              ──→ hotspot_history.py ──→ drift detection
                              ──→ critical_path_analysis.py ──→ critical path score
                              ──→ graph_runtime_correlation.py ──→ correlation analysis
                              ──→ Grafana ──→ Cognitive Health Score panel

runtime_slo.py (C, provider) ──→ /metrics ──→ ailab_slo_gateway_health, etc.
                              ──→ recording rule ──→ ai_lab:runtime_health_score
                              ──→ Grafana ──→ RHS Cross-check, Drift Graph
                              ──→ alerta ──→ AI-LABRuntimeHealthScoreDrift
```

---

## FASE 3 — Comparación

### ¿Duplican responsabilidades?

**NO.** Los 3 sistemas miden aspectos distintos:

| Aspecto | A (health_score) | B (cognitive_health) | C (SLO recording rule) |
|---------|------------------|----------------------|----------------------|
| ¿Qué mide? | Salud infra server | Salud capa cognitiva | Salud SLOs gateway |
| Método | subprocess + file read | API interna + routing_history | Métricas en memoria |
| Threshold | Hardcode (GPU=30, GW=15...) | Ponderado (60% nodos, 40% confianza) | Media simple de 5 binarias |
| Inputs | Archivos JSON + procesos externos | Objetos Python en memoria | SLO counters del gateway |
| Salida | Solo dict en memoria | Métrica Prometheus + endpoint HTTP | Métrica Prometheus |

### ¿Uno reemplaza al otro?

No directamente. Miden conceptos diferentes.

- B no puede reemplazar A porque A mide disponibilidad de servicios externos.
- C no puede reemplazar B porque C mide solo SLOs de infraestructura.
- A es un diagnóstico básico que B+C cubren con mayor granularidad.

### ¿Ambos siguen activos?

Sí:

- **A**: Activo pero relegado a `control_plane.py` (un solo consumidor). No produce métrica Prometheus.
- **B**: Activo y CANÓNICO. 6 consumidores + Prometheus + Grafana.
- **C**: Activo como recording rule. 2 paneles Grafana + 1 alerta.

### ¿Cuál tiene más consumidores?

- **B (cognitive_health_layer)**: 6 consumidores directos de código + Prometheus + Grafana
- **A (health_score)**: 1 consumidor (control_plane.py)
- **C (recording rule)**: 2 paneles + 1 alerta

### ¿Cuál tiene métricas reales?

| Sistema | Métrica en Prometheus | Valor actual |
|---------|----------------------|-------------|
| A | Ninguna | No visible |
| B | `ailab_cognitive_health_score` | **0.0** |
| C | `ai_lab:runtime_health_score` | **1.0** |

### ¿Cuál tiene mejor cobertura funcional?

**B (cognitive_health_layer)**:
- ✅ 5 funciones exportables
- ✅ Fail-safe en todas
- ✅ Snapshot completo (nodos, confianza, watchdog, GPUs)
- ✅ Contrato de versión
- ✅ Métricas Prometheus
- ✅ Endpoint HTTP dedicado
- ✅ Cacheable (120s TTL en Gateway)

**A (health_score)**:
- ❌ Una sola función
- ❌ Dependencias externas frágiles (subprocess)
- ❌ Bug conocido (/metricsmetrics)
- ❌ Sin métricas Prometheus
- ❌ Sin endpoint HTTP dedicado

**C (recording rule)**:
- ✅ Simple y determinista
- ✅ Dependencias robustas (contadores de Gateway)
- ❌ Solo 5 métricas binarias
- ❌ No evalúa estado cognitivo

---

## FASE 4 — Source of Truth

### Decisión: OPCIÓN B (cognitive_health_layer.py debe ser canónico)

**Justificación:**

1. **Mayor cobertura funcional** — 5 métricas vs 1 de A vs 1 de C
2. **Más consumidores** — 6 módulos la importan directamente
3. **Contrato de versión** — `COGNITIVE_HEALTH_CONTRACT_VERSION = "37A-COGNITIVE-HEALTH-LAYER-01"`
4. **Fail-safe** — toda función pública retorna payload válido incluso en error
5. **Observabilidad nativa** — produce métrica Prometheus + endpoint HTTP
6. **Cacheable** — ya integrada con cache 120s en Gateway
7. **Arquitectura modular** — nodos, confianza, watchdog, GPUs como funciones separadas

**Problema identificado:**

En estado frío (sin tráfico), `cognitive_health_layer.py` retorna score=0 porque:
- `control_plane.get_control_nodes()` devuelve sin nodos
- `routing_history.stats_by_node()` devuelve vacío
- `routing_confidence.confidence = 0` cuando `nodes_online = 0`

Esto **no es un bug** — es el comportamiento esperado. La capa cognitiva no puede
evaluar salud si no tiene datos de routing. Sin embargo, para efectos de dashboard,
un score de 0 en estado frío crea una alerta de drift con el runtime_health_score=100.

### Recomendación sobre A (health_score.py)

**Debe ser retirado** por:

1. Un solo consumidor (`control_plane.py`)
2. Uso de subprocess (frágil, no portable, lento)
3. Bug confirmado: `/metricsmetrics`
4. No produce métricas Prometheus
5. Funcionalidad cubierta por B + C

### Relación entre B y C

**B y C son complementarios, no duplicados:**

| Sistema | Mide | Estado frío |
|---------|------|-------------|
| B — cognitive_health_score | ¿El cerebro tiene datos? | 0 (correcto) |
| C — runtime_health_score | ¿El cuerpo responde? | 100 (correcto) |

Ambos deben coexistir. La alerta de drift es correcta al señalar la diferencia.

---

## FASE 5 — Plan de migración (propuesta, sin ejecutar)

### Si se decide migrar A a B:

| Paso | Descripción | Riesgo |
|------|-------------|--------|
| 1. Score canónico | Mantener `cognitive_health_layer.py` como fuente de verdad | Bajo |
| 2. Migrar `control_plane.py` | Reemplazar `health_score.calculate()` por `cognitive_health_layer.build_cognitive_health_snapshot()` | Medio — cambiar firma de output |
| 3. Retirar `health_score.py` | Eliminar archivo tras migración | Bajo |
| 4. Consumidores afectados | Solo `control_plane.py` | Bajo |
| 5. Dashboards | Ninguno (A no produce métricas) | Ninguno |
| 6. Alertas | Ninguna (A no tiene alertas) | Ninguno |
| 7. Esfuerzo estimado | 1-2 horas (cambio localizado en control_plane.py) | |

### Si se decide mejorar B (recomendado):

| Paso | Descripción |
|------|-------------|
| 1. Añadir baseline | Si no hay datos de routing → score = 50 ("unknown but operational") |
| 2. Mejorar `build_cognitive_health_prometheus_metrics()` | Incluir SLO metrics como signals adicionales |
| 3. Migrar `control_plane.py` | Usar B en lugar de A |

---

## Conclusión

**Resultado: PASS**

### Respuestas ejecutivas

**1. ¿Cuál es el score correcto?**
No hay un score único correcto. `ailab_cognitive_health_score` (B) es el score canónico para la **capa cognitiva**. `ai_lab:runtime_health_score` (C) es el score correcto para la **infraestructura SLO**. Miden cosas distintas.

**2. ¿Por qué existe el drift de ~100 puntos?**
Porque la capa cognitiva (B) requiere datos de routing_history para calcular su score. En estado frío/sin tráfico: `nodes_online=0 → routing_confidence=0 → score=0`. Mientras tanto, la infraestructura SLO (C) reporta salud perfecta porque todos los servicios responden. El drift es **comportamiento esperado y correcto**.

**3. ¿Qué componente debe sobrevivir?**
`cognitive_health_layer.py` (Sistema B) como score canónico de la capa cognitiva.

**4. ¿Qué componente debería retirarse?**
`health_score.py` (Sistema A) — LEGACY. Un solo consumidor, frágil, buggy, sin métricas Prometheus. Su funcionalidad está cubierta por B + C.

**5. ¿Cuál sería el impacto esperado sobre los dashboards?**
Migrar A a B no afecta dashboards (A no produce métricas). El drift entre B y C es esperado y se mantiene como alerta informativa.
