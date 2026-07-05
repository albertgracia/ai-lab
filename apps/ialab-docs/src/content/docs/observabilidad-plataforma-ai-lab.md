---
title: "Observabilidad — Plataforma AI-LAB"
summary: "Infraestructura completa de observabilidad del AI-LAB: Prometheus, Grafana, 15 dashboards, 19 alertas y metricas."
order: 48
---

> **IMPORTANTE:** `192.168.1.30:3001` es **Grafana v12.0.2**, NO AnythingLLM.  
> AnythingLLM está en `192.168.1.50:3001`.

## Stack Completo

| Componente | Host | Puerto | Rol | Estado |
|-----------|------|--------|-----|--------|
| **Prometheus** | 192.168.1.40 | 9090 | Source of Truth — scraping + alertas + TSDB | Active |
| **Grafana** | 192.168.1.40 | 3000 | Visualización — dashboards + provisioning | Active |
| **Loki** | 192.168.1.40 | — | Agregación de logs | Active |
| **node_exporter** | 192.168.1.30 | 9100 | Métricas de host (CPU, RAM, disco) | Active |
| **cAdvisor** | 192.168.1.30 | 8081 | Métricas de contenedores Docker | Active |
| **GPU exporter** | 192.168.1.50 | 9182 | GPU RX9070 (VRAM, temperatura, uso) | Active |
| **GPU compute metrics** | 192.168.1.50 | 9183 | Métricas de cómputo GPU | Active |
| **GPU exporter** | 192.168.1.60 | 9182 | GPU RX7900XT — **DOWN** (nodo apagado) | Inactive |
| **GPU compute metrics** | 192.168.1.60 | 9183 | Métricas de cómputo GPU — **DOWN** | Inactive |
| **Cloudflare Tunnel** | cloudflare-tunnel | 2000 | Métricas del túnel Cloudflare | Active |

---

## Scrape Targets Prometheus

| Job | Target | Estado | Labels |
|-----|--------|--------|--------|
| `ai-lab-gateway` | 192.168.1.30:8008/metrics | UP | `role=gateway` |
| `ai-lab-router` | 192.168.1.30:8083/metrics | UP | `role=router` |
| `ai-lab-live-api` | 192.168.1.30:8084/metrics | UP | `role=live-api` |
| `ai-lab-cadvisor` | 192.168.1.30:8081/metrics | UP | Container metrics |
| `ai-lab-node` | 192.168.1.30:9100/metrics | UP | Host metrics (node_exporter) |
| `ai-lab-gpu-rx9070` | 192.168.1.50:9182/metrics | UP | GPU RX9070 |
| `ai-lab-gpu-metrics` | 192.168.1.50:9183/metrics | UP | GPU compute |
| `ai-lab-gpu-rx7900xt` | 192.168.1.60:9182/metrics | DOWN | GPU RX7900XT — nodo apagado |
| `cloudflare-tunnel` | cloudflare-tunnel:2000/metrics | UP | Tunnel Cloudflare |

---

## Dashboards Grafana (folder `AI-LAB`)

Datasource UID: `PBFA97CFB590B2093`

| # | Dashboard | UID | Capa | Tier |
|---|-----------|-----|------|------|
| 00 | **Executive Overview** | `ai-lab-overview` | Resumen general | TIER 1 |
| 01 | **Routing & Models** | `ai-lab-runtime` | Rutas, modelos, latencia | TIER 1 |
| 02 | **Cognitive Profiles** | `ai-lab-profiles` | Perfiles cognitivos (FASE 21) | TIER 1 |
| 03 | **Tool Governance** | `ai-lab-tools` | Tools + gobernanza (FASE 22) | TIER 1 |
| 04 | **Memory Runtime** | `ai-lab-memory` | Memoria semántica (FASE 23) | TIER 2 |
| 05 | **Execution & Safety** | `ai-lab-safety` | Seguridad y bloques | TIER 1 |
| 06 | **GPU / Inference** | `ai-lab-gpus` | RX9070 / RX7900XT | TIER 1 |
| 07 | **Infrastructure** | `ai-lab-infra` | Docker, host, red | TIER 2 |
| 08 | **Incidents & Audit** | `ai-lab-incidents` | Incidentes, errores, auditoría | TIER 2 |
| 09 | **Runtime Protection (SLO)** | `ai-lab-slo` | SLO enforcement (FASE 29.4) | TIER 1 |
| 10 | **Sensor Fusion** | `ai-lab-sensors` | Fusión de sensores runtime (FASE 30I) | TIER 2 |
| 11 | **Evidence Guard** | `ai-lab-evidence` | Guardias de evidencia (FASE 30H) | TIER 2 |
| 12 | **Precision Mode** | `ai-lab-precision` | Precisión operacional (FASE 36B) | TIER 2 |
| 13 | **Cognitive Health** | `ai-lab-cognitive` | Salud cognitiva (FASE 37A) | TIER 2 |
| 14 | **Governance Drift** | `ai-lab-governance-drift` | Detección de deriva (FASE 37E) | TIER 2 |

### Executive Overview (00)

Resumen de salud del runtime en un vistazo.

| Panel | Métrica |
|-------|---------|
| Router UP | `up{job="ai-lab-router"}` |
| Gateway UP | `up{job="ai-lab-gateway"}` |
| Requests/min | `rate(ailab_router_chat_requests_total[5m])` |
| Error rate | `rate(ailab_route_family_errors_total[5m]) / rate(ailab_router_chat_requests_total[5m])` |
| Avg latency | `avg by (family)(rate(ailab_route_family_latency_ms_sum[5m]) / rate(ailab_route_family_latency_ms_count[5m]))` |
| Profiles active | `count(count by (profile)(rate(ailab_profile_total[5m])))` |

### Routing & Models (01)

Rendimiento de rutas y modelos de inferencia.

| Panel | Métrica |
|-------|---------|
| Requests by route family | `sum(rate(ailab_route_family_total[5m])) by (family)` |
| Latency p50/p95 | `histogram_quantile(0.50/0.95, rate(ailab_route_family_latency_ms_bucket[5m]))` |
| First token latency (TTFB) | `rate(ailab_first_token_latency_ms_sum[5m]) / rate(ailab_first_token_latency_ms_count[5m])` |
| Completion stream duration | `rate(ailab_completion_stream_duration_ms_sum[5m]) / rate(ailab_completion_stream_duration_ms_count[5m])` |
| Model distribution | `sum(rate(ailab_profile_total[5m])) by (model)` |

### Cognitive Profiles (02)

Distribución de uso de perfiles cognitivos.

| Panel | Métrica |
|-------|---------|
| Requests by profile | `sum(rate(ailab_profile_total[5m])) by (profile)` |
| Profile vs route | `sum(rate(ailab_profile_total[5m])) by (profile, route_family)` |
| Model by profile | `sum(rate(ailab_profile_total[5m])) by (profile, model)` |
| Greeting fastpath | `rate(ailab_greeting_fastpath_total[5m])` |
| Qwen escalation | `rate(ailab_qwen_escalation_total[5m])` |

### Tool Governance (03)

Uso y bloqueo de herramientas.

| Panel | Métrica |
|-------|---------|
| Tool calls by name | `sum(rate(ailab_tool_call_total[5m])) by (tool_name)` |
| Allowed vs blocked | `sum(rate(ailab_tool_call_total[5m])) by (result)` |
| By policy mode | `sum(rate(ailab_tool_call_total[5m])) by (policy, mode)` |
| Blocked by reason | `rate(ailab_governance_blocked_actions_by_reason_total[5m])` |
| Fastpath leakage | `rate(ailab_tool_fastpath_total[5m])` |

### Memory Runtime (04)

Recall semántico y uso de memoria.

| Panel | Métrica |
|-------|---------|
| Recall by policy | `sum(rate(ailab_memory_recall_total[5m])) by (policy, hit)` |
| Hit ratio | `sum(rate(ailab_memory_recall_total{hit="true"}[5m])) / sum(rate(ailab_memory_recall_total[5m]))` |
| Chars injected p95 | `histogram_quantile(0.95, rate(ailab_memory_chars_injected_bucket[5m]))` |
| Items by source | `sum(rate(ailab_memory_items_total[5m])) by (source)` |
| Contamination risk | `rate(ailab_memory_contamination_risk[5m])` |

### Execution & Safety (05)

Seguridad, bloqueos y gobernanza.

| Panel | Métrica |
|-------|---------|
| Blocked by governance | `rate(ailab_governance_blocked_actions_total[5m])` |
| Circuit breaker state | `ailab_circuit_breaker_state` |
| SLO degradation level | `ailab_runtime_degradation_level` |
| Emergency mode | `rate(ailab_runtime_emergency_mode_total[5m])` |
| Qwen protection | `rate(ailab_runtime_qwen_protection_total[5m])` |
| Llama fastpath forced | `rate(ailab_runtime_llama_fastpath_forced_total[5m])` |

### GPU / Inference (06)

Métricas de las GPUs de inferencia.

| Panel | Métrica |
|-------|---------|
| VRAM usage | `ailab_gpu_vram_used_bytes / ailab_gpu_vram_total_bytes` |
| GPU utilization | `ailab_gpu_estimated_utilization_pct` |
| Active requests | `ailab_gpu_active_requests` |
| Temperature | `ailab_gpu_temperature_celsius` |
| Power draw | `ailab_gpu_power_draw_watts` |

### Infrastructure (07)

Métricas de infraestructura subyacente.

| Panel | Métrica |
|-------|---------|
| Host CPU | `100 - (avg by (instance)(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)` |
| Host RAM | `(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes` |
| Host disk | `(node_filesystem_size_bytes{mountpoint="/"} - node_filesystem_free_bytes{mountpoint="/"}) / node_filesystem_size_bytes{mountpoint="/"}` |
| Docker containers | `count(container_last_seen)` |

### Incidents & Audit (08)

Incidentes activos, errores y auditoría del runtime.

| Panel | Métrica |
|-------|---------|
| Active incidents | `count(ailab_incident_active == 1)` |
| Error rate by type | `rate(ailab_errors_total[5m]) by (error_type)` |
| Audit log volume | `rate(ailab_audit_events_total[5m])` |
| Failure attribution | `rate(ailab_failure_attribution_total[5m]) by (category)` |
| Offline nodes | `count(up == 0) by (job)` |

### Runtime Protection — SLO (09)

Protección adaptativa del runtime vía SLO enforcement (FASE 29.4).

| Panel | Métrica |
|-------|---------|
| SLO state | `ailab_runtime_slo_state` |
| Degradation level | `ailab_runtime_degradation_level` |
| Timeout rate | `rate(ailab_runtime_timeout_rate[5m])` |
| VRAM pressure | `ailab_runtime_vram_pressure` |
| GPU pressure | `ailab_runtime_gpu_pressure` |
| Priority lane usage | `rate(ailab_runtime_priority_lane_total[5m]) by (lane)` |
| Stream backlog | `ailab_runtime_stream_backlog` |
| SLO violations | `rate(ailab_slo_violations_total[5m])` |
| Qwen parallel | `ailab_runtime_qwen_parallel` |
| Concurrent streams | `ailab_runtime_concurrent_streams` |

### Sensor Fusion (10)

Fusión de sensores del runtime (FASE 30I). Agrega señales de health, GPU, errores, auditable, governance y routing.

| Panel | Métrica |
|-------|---------|
| Sensor health score | `ailab_sensor_health_score` |
| Signal freshness | `ailab_sensor_freshness_seconds` |
| Active signals | `count(ailab_sensor_active == 1)` |
| Sensor conflicts | `rate(ailab_sensor_conflicts_total[5m])` |
| Degraded sensors | `count(ailab_sensor_status == 2)` |

### Evidence Guard (11)

Guardias de evidencia y lineage (FASE 30H).

| Panel | Métrica |
|-------|---------|
| Invalid lineage | `ailab_evidence_invalid_lineage_total` |
| Replay risk | `ailab_evidence_replay_risk_total` |
| Stale evidence | `ailab_evidence_stale_total` |
| Lineage depth | `ailab_evidence_lineage_depth_max` |
| Evidence confidence | `ailab_evidence_confidence_score` |

### Precision Mode (12)

Precisión operacional y gestión de confianza (FASE 36B).

| Panel | Métrica |
|-------|---------|
| Precision score | `ailab_operational_precision_score` |
| Confidence integrity | `ailab_confidence_integrity_score` |
| Authority conflicts | `rate(ailab_authority_conflicts_total[5m])` |
| Partial state | `rate(ailab_partial_state_total[5m])` |
| Discovery leakage | `rate(ailab_discovery_leakage_total[5m])` |
| Stale evidence | `rate(ailab_stale_evidence_total[5m])` |
| Confidence degraded | `rate(ailab_precision_degraded_responses_total[5m])` |
| Confidence downgrade | `rate(ailab_confidence_downgrade_total[5m])` |

### Cognitive Health (13)

Salud de la capa cognitiva (FASE 37A).

| Panel | Métrica |
|-------|---------|
| Cognitive health score | `ailab_cognitive_health_score` |
| Cognitive health state | `ailab_cognitive_health_state` |
| Degraded routes | `count(ailab_route_family_health < 1)` |
| Graph-runtime correlation | `ailab_graph_runtime_correlation` |
| Critical path score | `ailab_critical_path_score` |
| Hotspot history | `ailab_graph_hotspot_score` |

### Governance Drift (14)

Detección de deriva en gobernanza (FASE 37E).

| Panel | Métrica |
|-------|---------|
| Governance violations | `ailab_architecture_governance_violations_total` |
| Drift score | `ailab_governance_drift_score` |
| High risk modules | `ailab_architecture_high_risk_total` |
| Critical modules | `ailab_architecture_critical_modules_total` |
| Deprecated alias count | `ailab_registry_deprecated_aliases_total` |

---

## Alertas Prometheus

Las reglas de alerta están en:
```
/home/albert/docker/monitorizacion/prometheus/config/rules/ai-lab-route-family-alerts.yml
/home/albert/docker/monitorizacion/prometheus/config/rules/ai-lab-cognitive-alerts.yml
```

### Alertas críticas (RED — STOP burn-in)

| Alerta | Expresión | Severidad |
|--------|-----------|-----------|
| **🔴 `AilabToolFastpathLeakage`** | `ailab_tool_fastpath_total > 0` | **critical** |
| **🔴 `AilabGovernanceUnexpectedBlocks`** | `increase(ailab_governance_unexpected_blocks_total[5m]) > 0` | **critical** |
| **🔴 `AilabHardFactsAccidental`** | `ailab_memory_hard_facts_recall_total{route!~".*analysis.*"} > 0` | **critical** |
| **🔴 `AilabMemoryRecallMinimal`** | `ailab_memory_recall_total{policy="minimal",hit="true"} > 0` | **critical** |

### Alertas de operación

| Alerta | Expresión | Severidad |
|--------|-----------|-----------|
| `MinimalRouteRegression` | `increase(ailab_route_family_prompt_tokens_total{family="minimal"}[10m]) > 500` | warning |
| `ToolFastpathLatencySpike` | `avg latency tool_fastpath > 8000ms` | critical |
| `CognitiveRouteExplosion` | `increase(ailab_route_family_prompt_tokens_total{family="cognitive"}[10m]) > 12000` | warning |
| `RouteFamilyErrorRate` | `increase(ailab_route_family_errors_total[5m]) > 0` | critical |
| `GovernanceBlocksSpike` | `increase(ailab_route_family_blocked_total[10m]) > 10` | warning |
| `ProfileUnknown` | `increase(ailab_profile_total{profile="unknown"}[5m]) > 0` | warning |
| `ToolBudgetExceeded` | `sum(rate(ailab_tool_call_total{result="blocked_by_policy"}[5m])) > 0` | warning |
| `MemoryFallback` | `sum(rate(ailab_memory_recall_total{policy="fallback"}[5m])) > 0` | warning |
| `AI-LABSLOViolation` | `increase(ailab_slo_violations_total[10m]) > 0` | warning |
| `AI-LABGatewayUnavailable` | `ailab_slo_gateway_health < 1` | critical |
| `AI-LABLMStudioUnavailable` | `ailab_slo_lmstudio_health < 1` | critical |
| `AI-LABNoRoutableModels` | `ailab_registry_routable_models_total < 1` | critical |
| `AI-LABFederationSafeMode` | `ailab_federation_guard_state >= 3` | critical |
| `AILABGatewayDown` | `ailab_slo_gateway_health < 1` | critical |
| `AILABGatewayHighErrorRate` | `rate(ailab_errors_total[5m]) > 0.2` | warning |

---

## Provisioning

Los dashboards se auto-cargan desde:

```
/home/albert/docker/monitorizacion/grafana/provisioning/dashboards/AI-LAB/
```

Grafana los detecta automáticamente al arrancar o al hacer reload:

```bash
docker exec grafana kill -HUP 1
```

Las alertas están en:

```
/home/albert/docker/monitorizacion/prometheus/config/rules/ai-lab-route-family-alerts.yml
/home/albert/docker/monitorizacion/prometheus/config/rules/ai-lab-cognitive-alerts.yml
```

La configuración de Prometheus está en:

```
/home/albert/docker/monitorizacion/prometheus/prometheus.yml
```

---

## URLs

- **Grafana**: `http://192.168.1.40:3000`
- **Prometheus**: `http://192.168.1.40:9090`
- **Router métricas**: `http://192.168.1.30:8083/metrics`
- **Gateway métricas**: `http://192.168.1.30:8008/metrics`
- **Live API métricas**: `http://192.168.1.30:8084/metrics`
- **cAdvisor**: `http://192.168.1.30:8081/metrics`
- **Node exporter**: `http://192.168.1.30:9100/metrics`
- **GPU RX9070**: `http://192.168.1.50:9182/metrics`
- **GPU compute**: `http://192.168.1.50:9183/metrics`
