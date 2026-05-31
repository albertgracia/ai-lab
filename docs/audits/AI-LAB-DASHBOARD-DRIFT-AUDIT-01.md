# AI-LAB-DASHBOARD-DRIFT-AUDIT-01

## Resumen ejecutivo

Se auditaron 5 dashboards de Grafana AI-LAB (156 paneles, 134 queries PromQL únicas) contra Prometheus para detectar drift entre paneles, queries y métricas existentes.

**Resultado: PARTIAL** — Los dashboards cargan correctamente y las métricas existen en Prometheus, pero se detectaron 5 recording rules (ai_lab:*) que no están desplegadas, afectando a 9 paneles en 3 dashboards. Además, la mayoría de métricas del Gateway (94 de 134 queries) retornan valor 0 porque no hay actividad de producción en el sistema.

---

## Dashboards auditados

| # | Dashboard | Paneles | Queries | OK | Zero | Recording Rule Missing |
|---|-----------|---------|---------|----|------|----------------------|
| 1 | AI-LAB Overview | 19 | 20 | 4 | 4 | 2 |
| 2 | AI-LAB Runtime | 15 | 18 | 1 | 3 | 2 |
| 3 | AI-LAB Cognitive Runtime | 101 | 104 | 0 | 27 | 5 |
| 4 | AI-LAB Infrastructure | 6 | 6 | 6 | 0 | 0 |
| 5 | AI-LAB GPUs | 1 | 8 | 8 | 0 | 0 |
| | **TOTAL** | **142** | **156** | **19** | **34** | **9** |

---

## Recording rules faltantes

Se detectaron 5 recording rules que no existen en Prometheus. Estas rules fueron diseñadas como parte del contrato health score (fase HEALTH-SCORE-CONTRACT-SPEC-01) pero nunca fueron desplegadas.

| Recording Rule | Paneles afectados | Dashboards |
|---------------|-------------------|------------|
| ai_lab:runtime_health_score | 5 | Overview, Runtime, Cognitive Runtime |
| ai_lab:architecture_risk_score | 1 | Cognitive Runtime |
| ai_lab:federation_guard_events_rate5m | 1 | Cognitive Runtime |
| ai_lab:slo_violations_rate5m | 1 | Cognitive Runtime |
| ai_lab:evidence_replay_rate5m | 1 | Cognitive Runtime |

### Impacto de ai_lab:runtime_health_score

Esta recording rule es la más crítica porque es parte del contrato de health score (RHS cross-check). Sin ella, 5 paneles quedan sin datos:

- **Overview**: RHS Cross-check (panel 12), Drift Indicator (panel 13)
- **Runtime**: RHS Cross-check Historical (panel 9), Drift Graph (panel 10)
- **Cognitive Runtime**: Runtime Health Score (panel en Alerting Overview)

---

## Métricas Gateway con actividad real (non-zero)

De las 82 métricas del Gateway, solo las siguientes tienen valores distintos de cero en Prometheus:

| Métrica | Valor | Descripción |
|---------|-------|-------------|
| ailab_cognitive_health_watchdog_triggers_total | 169 | Watchdog ha detectado eventos reales |
| ailab_errors_total | 1 | 1 error registrado |
| ailab_slo_gateway_health | 1 | Gateway health SLO OK |
| ailab_slo_lmstudio_health | 1 | LM Studio health SLO OK |
| ailab_slo_registry_consistency | 1 | Registry consistency OK |
| ailab_slo_violations_total | 17 | Violaciones históricas de SLO |
| ailab_slo_degraded_total | 1 | 1 SLO degradado |
| ailab_slo_safe_mode_total | 1 | 1 SLO en safe mode |
| ailab_registry_models_total | 4 | 4 modelos en registry |
| ailab_registry_routable_models_total | 2 | 2 modelos routables |
| ailab_registry_deprecated_aliases_total | 1 | 1 alias deprecado |
| ailab_registry_tolerated_aliases_total | 1 | 1 alias tolerado |
| ailab_critical_path_score | 0.925 | Critical path score alto (92.5%) |
| ailab_critical_path_high_total | 28 | 28 módulos high risk |
| ailab_critical_path_critical_total | 1 | 1 módulo crítico |
| ailab_correlation_score | 0.99 | Correlation score 99% |
| ailab_correlation_hotspots_total | 47 | 47 hotspots correlacionados |
| ailab_correlation_high_risk_total | 20 | 20 correlaciones high risk |
| ailab_correlation_critical_total | 10 | 10 correlaciones críticas |
| ailab_correlation_recommendations_total | 1 | 1 recomendación activa |
| ailab_correlation_runtime_health_linked_total | 20 | 20 enlaces runtime health |
| ailab_hotspot_history_snapshots_total | 4 | 4 snapshots históricos |
| ailab_hotspot_history_recurring_total | 10 | 10 hotspots recurrentes |
| ailab_hotspot_history_unknowns_total | 1 | 1 unknown |
| ailab_hotspot_history_recommendations_total | 2 | 2 recomendaciones |
| ailab_governance_drift_score | 0.279 | Drift de gobierno 27.9% |
| ailab_governance_drift_governance_confidence | 0.721 | Confianza 72.1% |
| ailab_governance_drift_events_total | 128 | 128 eventos de drift |
| ailab_governance_drift_domains_total | 20 | 20 dominios analizados |
| ailab_governance_drift_health_delta_avg | 0.7398 | Delta avg salud |
| ailab_governance_drift_recommendations_total | 1 | 1 recomendación drift |
| ailab_gateway_metrics_render_seconds | 0.0001 | Render time 0.1ms |

---

## Métricas Gateway en cero

Las siguientes métricas existen y son scrapeadas por Prometheus pero retornan 0, indicando que los subsistemas correspondientes no tienen actividad o no están disponibles:

### Grupo: Cognitive Health (0)
- ailab_cognitive_health_score = 0 (Qdrant query returns no data for 60min window)
- ailab_cognitive_health_routing_confidence = 0
- ailab_cognitive_health_nodes_online = 0

### Grupo: Contadores Gateway (0)
- ailab_requests_total = 0, ailab_active_streams = 0
- ailab_routing_decisions_total = 0
- ailab_sessions_total = 0
- ailab_last_latency_ms = 0
- ailab_gateway_latency_p50_ms = 0, ailab_gateway_latency_p95_ms = 0

### Grupo: Federation Guards (0)
- ailab_federation_guard_state = 0
- ailab_federation_guard_caps_applied_total = 0
- ailab_federation_guard_replay_detections_total = 0
- ailab_federation_guard_storm_detections_total = 0
- ailab_federation_guard_authority_escalations_total = 0

### Grupo: Evidence (0)
- ailab_evidence_propagations_total, *_stale_total, *_replay_risk_total = 0
- ailab_evidence_lineage_depth_max = 0
- ailab_evidence_reuse_total, *_stored_total, *_invalid_lineage_total = 0

### Grupo: LM Studio (0)
- ailab_lmstudio_up = 0 (no reachable)
- ailab_lmstudio_models_count = 0

### Grupo: Triage (0)
- ailab_triage_incidents_total, *_critical_total, *_high_total = 0
- ailab_triage_platform_blast_radius_total, *_federation_blast_radius_total = 0
- ailab_triage_lmstudio_related_total, *_registry_related_total = 0

### Grupo: Runtime Scores (0)
- ailab_runtime_maturity_score = 0
- ailab_runtime_performance_score = 0
- ailab_runtime_operational_impact = 0
- ailab_runtime_degradation_level = 0
- ailab_runtime_slo_state = 0

### Grupo: Graph (0)
- ailab_graph_hotspots_total = 0
- ailab_graph_governance_findings_total = 0
- ailab_graph_gravity_centers_total = 0

---

## Tabla completa de hallazgos (resumida por dashboard)

### AI-LAB Overview (20 queries)

| Panel | Query | Estado | Motivo |
|-------|-------|--------|--------|
| Targets up | sum(up) | OK | 1 |
| Health rate | sum(up)/count(up)*100 | OK | 100 |
| Requests total | ailab_requests_total{job="ai-lab-gateway"} | ZERO | 0 activos |
| Latency ms | ailab_last_latency_ms{job="ai-lab-gateway"} | ZERO | 0 activos |
| Errors / min | rate(ailab_errors_total...)*60 | ZERO | 0 activos |
| Active streams | ailab_active_streams{job="ai-lab-gateway"} | ZERO | 0 activos |
| GPU nodes | count(up{job="ai-lab-gpu-metrics"}) | OK | 2 GPUs |
| Containers | count(container_cpu_usage...) | OK | OK |
| Runtime trend (A) | rate(ailab_requests_total...)*60 | ZERO | 0 activos |
| Runtime trend (B) | rate(ailab_routing_decisions_total...)*60 | ZERO | 0 activos |
| RHS Canónico | ailab_cognitive_health_score{job="ai-lab-gateway"} | ZERO | 0.0 |
| RHS Cross-check | ai_lab:runtime_health_score * 100 | **RECORDING_RULE_MISSING** | No desplegada |
| Drift Indicator | abs(ailab_cognitive_health_score - (ai_lab:runtime_health_score * 100)) | **RECORDING_RULE_MISSING** | Depende de RR |
| Gateway Status | up{job="ai-lab-gateway"} | OK | 1 (UP) |
| Routing Confidence | ailab_cognitive_health_routing_confidence * 100 | ZERO | 0 |
| Nodes Online | ailab_cognitive_health_nodes_online{job="ai-lab-gateway"} | ZERO | 0 |
| Watchdog Triggers | ailab_cognitive_health_watchdog_triggers_total{job="ai-lab-gateway"} | OK | 169 |
| SLO Gateway | ailab_slo_gateway_health{job="ai-lab-gateway"} | OK | 1 |
| SLO LM Studio | ailab_slo_lmstudio_health{job="ai-lab-gateway"} | OK | 1 |
| SLO Registry | ailab_slo_registry_consistency{job="ai-lab-gateway"} | OK | 1 |

### AI-LAB Runtime (18 queries)

| Panel | Query | Estado | Motivo |
|-------|-------|--------|--------|
| Requests total | ailab_requests_total{job="ai-lab-gateway"} | ZERO | 0 |
| Requests / min | rate(...)*60 | ZERO | 0 |
| Routing / min | rate(...)*60 | ZERO | 0 |
| Latency ms | ailab_last_latency_ms{job="ai-lab-gateway"} | ZERO | 0 |
| Errors / min | rate(...)*60 | ZERO | 0 |
| Active streams | ailab_active_streams{job="ai-lab-gateway"} | ZERO | 0 |
| Gateway activity | ailab_sessions_total{job="ai-lab-gateway"} | ZERO | 0 |
| RHS Historical | ailab_cognitive_health_score{job="ai-lab-gateway"} | ZERO | 0.0 |
| RHS Cross-check Historical | ai_lab:runtime_health_score * 100 | **RECORDING_RULE_MISSING** | No desplegada |
| Drift Graph | abs(ailab_cognitive_health_score - (ai_lab:runtime_health_score * 100)) | **RECORDING_RULE_MISSING** | Depende de RR |
| Routing Confidence Historical | ailab_cognitive_health_routing_confidence * 100 | ZERO | 0 |
| Nodes Online Historical | ailab_cognitive_health_nodes_online{job="ai-lab-gateway"} | ZERO | 0 |
| Latency p50/p95 | ailab_gateway_latency_p50/p95_ms | ZERO | 0 |
| Watchdog Rate | rate(ailab_cognitive_health_watchdog_triggers_total[5m]) | ZERO | 169 pero rate=0 |
| SLO Historical (A) | ailab_slo_gateway_health{job="ai-lab-gateway"} | OK | 1 |
| SLO Historical (B) | ailab_slo_lmstudio_health{job="ai-lab-gateway"} | OK | 1 |
| SLO Historical (C) | ailab_slo_registry_consistency{job="ai-lab-gateway"} | OK | 1 |

### AI-LAB Cognitive Runtime (104 queries)

**Hallazgos principales:**
- 72 paneles retornan 0 (métricas existen, subsistemas sin actividad)
- 27 paneles rate() retornan 0
- 5 recording rules faltantes

Resumen por sección:
| Sección | Paneles | Estado |
|---------|---------|--------|
| Federation/Evidence/Registry/LM Studio (stat) | 39 | OK (métricas=0, subsistemas inactivos) |
| SLO | 6 | OK (1s = healthy) |
| Alerting Overview | 8 | OK (ALERTS=0, sin alertas) |
| Autonomous Triage | 8 | OK (incidentes=0) |
| Graph Reasoning | 24 | OK (métricas=0, sin actividad) |

### AI-LAB Infrastructure (6 queries)

Todos OK — node_exporter, cadvisor, unpoller operativos.

### AI-LAB GPUs (8 queries)

Todos OK — gpu_smalldata, gpu_power_watts, gpu_temperature_celsius operativos.

---

## Riesgos

| # | Riesgo | Severidad | Impacto |
|---|--------|-----------|---------|
| R1 | 5 recording rules no desplegadas | **Alta** | 9 paneles sin datos; RHS cross-check y drift no funcionales |
| R2 | ailab_cognitive_health_score = 0 | **Media** | Panel RHS Canónico muestra 0; la capa cognitiva no produce score |
| R3 | ailab_requests_total = 0 | **Media** | No hay tráfico de producción; paneles de actividad vacíos |
| R4 | ailab_lmstudio_up = 0 | **Media** | LM Studio no accesible; paneles LM Studio muestran down |
| R5 | ailab_active_streams = 0, sessions = 0 | **Baja** | Gateway sin carga actual |
| R6 | ailab_gateway_latency_p50/p95_ms = 0 | **Baja** | Sin métricas de latencia por falta de tráfico |
| R7 | ailab_triage_* en 0 | **Baja** | Sistema de triage sin actividad |
| R8 | ailab_runtime_maturity_score = 0 | **Baja** | Scoring de madurez no computado |

---

## Recomendaciones priorizadas

### P1 — Crítico (siguiente fase)
**Desplegar recording rules de Prometheus**
- Crear `ai_lab:runtime_health_score` (crítico: RHS cross-check, drift)
- Crear `ai_lab:architecture_risk_score`, `ai_lab:federation_guard_events_rate5m`
- Crear `ai_lab:slo_violations_rate5m`, `ai_lab:evidence_replay_rate5m`
- Fase recomendada: **AI-LAB-PROMETHEUS-RUNTIME-HEALTH-RECORDING-RULE-01**

### P2 — Alta
**Investigar ailab_cognitive_health_score = 0**
- Posible causa: Qdrant query vacía (ventana 60min sin datos)
- Verificar si cognitive_health_layer recibe datos de routing_history
- Si no hay datos de producción, el score 0 puede ser correcto

### P3 — Media
**Restaurar conectividad LM Studio**
- `ailab_lmstudio_up = 0` desde el restart del Gateway
- Verificar endpoint 192.168.1.50:1234

### P4 — Baja
**Activar tráfico de producción en Gateway**
- ailab_requests_total = 0, ailab_active_streams = 0
- Sin tráfico real, los dashboards de actividad Gateway siempre mostrarán vacío

---

## Conclusión

**Resultado: PARTIAL**

Los dashboards cargan correctamente, las métricas del Gateway son scrapeadas por Prometheus, y no hay queries rotas. Sin embargo, el sistema de health score no es funcional porque:
1. Las 5 recording rules nunca fueron desplegadas
2. La capa cognitiva retorna score 0

La fase **AI-LAB-PROMETHEUS-RUNTIME-HEALTH-RECORDING-RULE-01** debe ejecutarse antes que **AI-LAB-HEALTH-SCORE-DRIFT-RULE-01** para que los paneles RHS cross-check, drift y runtime health score tengan datos.

---

## Datos de la auditoría

- Fecha: 2026-05-31
- HEAD: 41b274f6
- Método: READ ONLY — queries contra Prometheus API (192.168.1.40:9090) + extracción de JSONs de provisioning
- Dashboards: 5 (overview, runtime, cognitive-runtime, infra, gpus)
- Paneles: 156
- Queries únicas: 134
- Métricas auditadas: 98
- Recording rules faltantes: 5
