---
title: "Mapa de Observabilidad — AI-LAB"
summary: "Mapa completo del flujo de observabilidad del AI-LAB: generacion de metricas, scrape Prometheus, dashboards Grafana, alertas y auditoria."
order: 49
---

## Flujo completo

```
┌──────────────────────────────────────────────────────────────────┐
│          AI-LAB Runtime — 3 procesos independientes              │
│                                                                  │
│  ┌──────────────────────┐   ┌──────────────────┐   ┌──────────┐ │
│  │  openai_gateway.py   │   │  router_api.py   │   │live_api  │ │
│  │  :8008  ★ TRAFICO    │   │  :8083  SIN TRÁF │   │:8084     │ │
│  │  (único entrypoint)  │   │  (API interna)   │   │(state)   │ │
│  │                      │   │                  │   │          │ │
│  │  profile_loader      │   │  metricas        │   │ metricas │ │
│  │  tool_policy         │   │  registradas     │   │ planas   │ │
│  │  memory_injector     │   │  pero en 0       │   │          │ │
│  │  classifier          │   │                  │   │          │ │
│  │  slo_manager         │   │                  │   │          │ │
│  │  precision_engine    │   │                  │   │          │ │
│  └──────────┬───────────┘   └────────┬─────────┘   └────┬─────┘ │
│             │                        │                  │        │
│       genera métricas          métricas planas     métricas planas│
│       con tráfico real         sin tráfico         sin tráfico   │
└─────────────┬────────────────────────────────────────────────────┘
              │ /metrics (Prometheus format)
              ▼
┌──────────────────────────────────────────────────────────────────┐
│           Prometheus (192.168.1.40:9090)                         │
│                                                                  │
│  scrape_configs (scrape interval entre parentesis):              │
│    ai-lab-gateway     192.168.1.30:8008/metrics   (15s)  ★       │
│    ai-lab-router      192.168.1.30:8083/metrics   (15s)         │
│    ai-lab-live-api    192.168.1.30:8084/metrics   (15s)         │
│    ai-lab-node        192.168.1.30:9100/metrics   (15s)         │
│    ai-lab-cadvisor    192.168.1.30:8081/metrics   (30s)         │
│    ai-lab-gpu-rx9070  192.168.1.50:9182/metrics   (30s)         │
│    ai-lab-gpu-metrics 192.168.1.50:9183/metrics   (30s)         │
│    ai-lab-gpu-rx7900xt 192.168.1.60:9182/metrics  (30s)  ⚠ DOWN │
│    cloudflare-tunnel  192.168.1.30:2000/metrics   (15s)         │
│    wifi-exporter       .40 — infra adicional                     │
│    unifi-exporter      .40 — infra adicional                     │
│    smartctl-exporter   .40 — infra adicional                     │
│    windows-exporter    .50/.200 — nodos Windows                  │
│                                                                  │
│  rule_files:                                                     │
│    /home/albert/docker/monitorizacion/prometheus/                │
│    config/rules/ai-lab-route-family-alerts.yml (19 alertas)      │
│                                                                  │
└──────────────────────┬───────────────────────────────────────────┘
                       │ query
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│            Grafana (192.168.1.40:3000)                           │
│                                                                  │
│  Datasource: Prometheus  (UID: PBFA97CFB590B2093)              │
│  Folder: AI-LAB  (15 dashboards, 3 TIERS)                       │
│                                                                  │
│  Provisioning:                                                   │
│    /home/albert/docker/monitorizacion/grafana/                   │
│    provisioning/dashboards/AI-LAB/*.json                         │
│                                                                  │
│  TIER 1 (operación diaria):                                      │
│  00  Executive Overview          ai-lab-overview                 │
│  01  Routing & Models            ai-lab-runtime                  │
│  02  Cognitive Profiles          ai-lab-profiles                 │
│  03  Tool Governance             ai-lab-tools                    │
│  06  GPU / Inference             ai-lab-gpus                     │
│  09  Runtime Protection (SLO)    ai-lab-slo-protection           │
│                                                                  │
│  TIER 2 (troubleshooting):                                       │
│  04  Memory Runtime              ai-lab-memory                   │
│  05  Execution & Safety          ai-lab-safety                   │
│  07  Infrastructure              ai-lab-infra                    │
│  08  Incidents & Audit           ai-lab-incidents                │
│  10  Streaming Quality           ai-lab-streaming                │
│  11  Cold Start Analysis         ai-lab-coldstart                │
│                                                                  │
│  TIER 3 (profiling / avanzado):                                  │
│  12  Precision & Confidence      ai-lab-precision                │
│  13  Cognitive Health            ai-lab-cognitive-health         │
│  14  Governance Drift            ai-lab-governance-drift         │
│                                                                  │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                 3 Canales de Observabilidad                       │
│                                                                  │
│  1. stdout → journalctl -u ailab-gateway -f --no-pager           │
│              grep "profile=" "family=" "SLO=" "evidence="        │
│                                                                  │
│  2. audit  → /opt/ai-lab/runtime/state/                          │
│              governance_audit.jsonl                               │
│              runtime_sensor_fusion.jsonl                          │
│                                                                  │
│  3. Prometheus → :8008/metrics (gateway — tráfico real)           │
│                   :8083/metrics (router — métricas planas)        │
│                   :8084/metrics (live-api — métricas planas)      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## ⚠ Regla crítica: 3 procesos, no confundir métricas

AI-LAB tiene **3 procesos Python independientes**, cada uno con su propio registry Prometheus.
Solo el **gateway (`:8008`)** recibe tráfico de chat real. El router (`:8083`) y live-api (`:8084`)
tienen los mismos counters registrados pero **nunca los incrementan**.

**Diagnóstico rápido:**
```bash
# Verificar qué endpoint tiene datos reales
curl -s http://192.168.1.30:8008/metrics | grep "ailab_route_family_total"
curl -s http://192.168.1.30:8083/metrics | grep "ailab_route_family_total"
curl -s http://192.168.1.30:8084/metrics | grep "ailab_route_family_total"
```

**Regla:** Las métricas que solo emite el gateway NO deben ser "primeadas" (inc(0))
en router ni live-api. Esto evita que series con valor 0 contaminen las queries PromQL
de Grafana.

---

## Scrape targets

| Job | Host:Port | Intervalo | Estado | Métricas que contiene |
|-----|-----------|-----------|--------|----------------------|
| `ai-lab-gateway` | 192.168.1.30:8008 | 15s | **★ TRÁFICO REAL** | Perfiles, routing, tools, memoria, SLO, streaming, calidad, precision, report_grounding, sensor_fusion, evidence_guard, cognitive_health, graph, critical_path, hotspot, governance_drift |
| `ai-lab-router` | 192.168.1.30:8083 | 15s | ⚠ Sin tráfico | Mismas métricas registradas pero siempre en 0 |
| `ai-lab-live-api` | 192.168.1.30:8084 | 15s | ⚠ Sin tráfico | Estado vivo, métricas planas |
| `ai-lab-node` | 192.168.1.30:9100 | 15s | ✅ Activo | CPU, RAM, disco, red (node_exporter) |
| `ai-lab-cadvisor` | 192.168.1.30:8081 | 30s | ✅ Activo | Contenedores Docker (CPU, memoria, IO) |
| `ai-lab-gpu-rx9070` | 192.168.1.50:9182 | 30s | ✅ Activo | VRAM, GPU usage, temperatura (nvidia-smi exporter) |
| `ai-lab-gpu-metrics` | 192.168.1.50:9183 | 30s | ✅ Activo | Compute metrics, tokens/s, power |
| `ai-lab-gpu-rx7900xt` | 192.168.1.60:9182 | 30s | **⛔ DOWN** | Nodo RX7900XT apagado |
| `ai-lab-gpu-metrics` | 192.168.1.60:9183 | 30s | **⛔ DOWN** | Nodo RX7900XT apagado |
| `cloudflare-tunnel` | 192.168.1.30:2000 | 15s | ✅ Activo | Tunnel metrics, conexiones Cloudflare |
| `wifi-exporter` | .40 (adicional) | 30s | ✅ Activo | Red WiFi |
| `unifi-exporter` | .40 (adicional) | 30s | ✅ Activo | Estado UniFi |
| `smartctl-exporter` | .40 (adicional) | 60s | ✅ Activo | SMART discos |
| `windows-exporter` | .50 / .200 | 15s | ✅ Activo | Métricas hosts Windows |

La configuración de scrape targets está en:
```
/home/albert/docker/monitorizacion/prometheus/prometheus.yml
```

---

## Métricas Prometheus

A continuación se listan todas las familias de métricas `ailab_*` organizadas por fase/área funcional.
Salvo que se indique lo contrario, todas se generan en **openai_gateway.py (:8008)** con tráfico real.

### Tool-specific routing (FASE 29.3.1)
```
ailab_greeting_fastpath_total
ailab_qwen_escalation_total
ailab_llama_fastpath_total
```
Contadores de decisión de ruta: saludos derivados a llama-3.1-8b, escalados a qwen2.5-14b por razón técnica.

### FASE 19 — Routing (6)
```
ailab_route_family_total{family}
ailab_route_family_latency_ms{family}      (histogram)
ailab_route_family_prompt_tokens_total{family}
ailab_route_family_completion_tokens_total{family}
ailab_route_family_errors_total{family}
ailab_route_family_blocked_total{family}
```

### FASE 21 — Perfiles cognitivos (1)
```
ailab_profile_total{profile, route_family, model}
```

### FASE 22 — Tool governance (3)
```
ailab_tool_call_total{tool_name, result, policy, mode}
ailab_tool_fastpath_total
ailab_tool_fastpath_fallback_total
```

### FASE 22B — Tool malformed (1)
```
ailab_tool_calls_malformed_total
```

### FASE 23 — Memory (3)
```
ailab_memory_recall_total{policy, hit}
ailab_memory_chars_injected{policy}        (histogram)
ailab_memory_items_total{policy, source}
```

### FASE 23B — Calidad (2)
```
ailab_quality_score                            (histogram)
ailab_hallucination_risk                       (histogram)
```

### FASE 24 — Streaming (3)
```
ailab_stream_chunks_total{model}
ailab_stream_stalls_total{model}
ailab_stream_finish_inconsistent_total{model}
```

### FASE 24 — Latencia (3)
```
ailab_first_token_latency_ms                   (histogram — TTFB)
ailab_request_total_latency_ms                 (histogram)
ailab_completion_stream_duration_ms            (histogram)
```

### FASE 24 — Checksums (1)
```
ailab_prompt_checksum_changes_total
```

### Cold starts (1)
```
ailab_cold_start_total{model, reason}
```

### GPU / Inference (2)
```
ailab_gpu_active_requests{node}
ailab_gpu_estimated_utilization_pct{node}
```

### Gobernanza (2)
```
ailab_governance_blocked_actions_total
ailab_governance_blocked_actions_by_reason_total{reason}
```

### Router base (4)
```
ailab_router_chat_requests_total
ailab_router_hard_facts_hits_total
ailab_embedding_truncations_total
ailab_embedding_input_chars
ailab_recall_query_chars
```

---

### FASE 29.4 — SLO Enforcement (14)

Familia completa de protección adaptativa del runtime. El `RuntimeSLOManager` evalúa ventanas deslizantes de TTFB, timeouts, GPU y VRAM. El `DegradationManager` aplica niveles progresivos con anti-flapping.

```
ailab_runtime_slo_state{state}                           GREEN / YELLOW / RED
ailab_runtime_degradation_level{level}                   NORMAL / LIGHT / HEAVY / EMERGENCY
ailab_runtime_timeout_rate                                % timeouts en ventana
ailab_runtime_vram_pressure                               % VRAM utilizada
ailab_runtime_gpu_pressure                                % GPU utilizada
ailab_runtime_priority_lane_total{lane}                   Lane 1 (critical) / Lane 2 / Lane 3
ailab_runtime_emergency_mode_total                        Contador de activaciones EMERGENCY
ailab_runtime_qwen_protection_total                       Protección qwen activada
ailab_runtime_llama_fastpath_forced_total                 Forced llama routing por degradación
ailab_runtime_stream_backlog                              Streams en cola
ailab_circuit_breaker_state{model}                        OPEN / CLOSED / HALF_OPEN
ailab_slo_violations_total{violation_type}                Violación de SLO
ailab_runtime_qwen_parallel                               Paralelismo qwen actual (1 o 2)
ailab_runtime_concurrent_streams                          Streams concurrentes activos
```

---

### FASE 29.4.1 — Report grounding (4)

Métricas de calidad de los reportes generados. Detecta reportes sin contexto de runtime, campos faltantes,
target IP no encontrada, y respuestas no grounded.

```
ailab_report_grounding_total{result}                     Reporte grounded / ungrounded
ailab_report_missing_fields_total                        Campos de runtime ausentes
ailab_report_target_ip_total{found}                      IP target resuelta / no resuelta
ailab_report_ungrounded_total                            Contador de reportes sin grounding
```

---

### FASE 30H — Evidence guard (4)

Guard de evidencia universal. Previene que el LLM afirme información sin respaldo observable.

```
ailab_evidence_guard_blocks_total{reason}
ailab_evidence_guard_confidence_downgrade_total
ailab_evidence_guard_degraded_responses_total
ailab_evidence_guard_unknown_state_total
```

---

### FASE 30I — Sensor fusion (4)

Fusión de sensores del runtime: combina señales de health, topología, GPU, SLO, estado de modelo
y watchdog en un snapshot unificado de estado observado.

```
ailab_sensor_fusion_snapshots_total
ailab_sensor_fusion_sensors_active
ailab_sensor_fusion_sensors_degraded
ailab_observed_runtime_context_size_bytes                 (histogram)
```

---

### FASE 36B — Precision (8)

Precisión operacional extrema: manejo de evidencia parcial, conflictos de autoridad,
confianza degradada y señales contradictorias.

```
ailab_operational_precision_score                        Score 0.0–1.0 de precisión
ailab_confidence_integrity_score                         Score 0.0–1.0 de integridad
ailab_authority_conflicts_total                          Conflictos entre fuentes de autoridad
ailab_partial_state_total                                Estados parcialmente observados
ailab_discovery_leakage_total                            Discoverable filtrado como active
ailab_stale_evidence_total                               Evidencia fuera de ventana
ailab_precision_degraded_responses_total                 Respuestas con precisión degradada
ailab_confidence_downgrade_total                         Downgrades de confianza
```

---

### FASE 37A — Cognitive health (1)

```
ailab_cognitive_health_score{layer}
```

Score compuesto de salud cognitiva por capa (routing, profiles, memory, tools, governance).
0.0–1.0, derivado de métricas observadas.

---

### FASE 37B — Graph correlation (3)

```
ailab_graph_routes_mapped_total
ailab_graph_nodes_active_total
ailab_graph_correlation_score
```

Correlación entre el grafo cognitivo GitNexus y el runtime observado.
Score alto = topología real coincide con el análisis estructural.

---

### FASE 37C — Critical path (3)

```
ailab_critical_path_latency_ms                    (histogram)
ailab_critical_path_bottleneck_blocks_total
ailab_critical_path_health_score
```

Análisis de ruta crítica: latencia extrema, cuellos de botella, salud del camino más lento.

---

### FASE 37D — Hotspot history (3)

```
ailab_hotspot_requests_total{hotspot}
ailab_hotspot_error_rate{hotspot}
ailab_hotspot_latency_p99_ms{hotspot}
```

Historial de hotspots: funciones o endpoints que concentran tráfico, errores o latencia.

---

### FASE 37E — Governance drift (3)

```
ailab_governance_drift_detections_total
ailab_governance_drift_severity{severity}
ailab_governance_drift_remediation_total
```

Detección de drift entre la governance declarada y la observada en runtime.
Severidad: LOW / MEDIUM / HIGH / CRITICAL.

---

### Tool-specific legacy (2)
```
ailab_tool_fastpath_total
ailab_tool_fastpath_fallback_total
```

---

## Totales

| Categoría | Familias |
|-----------|----------|
| Routing (F19) | 6 |
| Routing tool-specific (F29.3.1) | 3 |
| Perfiles (F21) | 1 |
| Tool governance (F22 + F22B) | 4 |
| Memoria (F23) | 3 |
| Calidad (F23B) | 2 |
| Streaming (F24) | 3 |
| Latencia (F24) | 3 |
| Checksums (F24) | 1 |
| Cold starts | 1 |
| GPU | 2 |
| Gobernanza | 2 |
| Router base | 4 |
| SLO Enforcement (F29.4) | 14 |
| Report grounding (F29.4.1) | 4 |
| Evidence guard (F30H) | 4 |
| Sensor fusion (F30I) | 4 |
| Precision (F36B) | 8 |
| Cognitive health (F37A) | 1 |
| Graph correlation (F37B) | 3 |
| Critical path (F37C) | 3 |
| Hotspot history (F37D) | 3 |
| Governance drift (F37E) | 3 |
| Legacy | 2 |
| **Total** | **~80+ familias** |

---

## Dashboards — Consultas clave por panel

### TIER 1 — Operación diaria

#### 00 — Executive Overview
| Panel | Query |
|-------|-------|
| Gateway UP | `up{job="ai-lab-gateway"}` |
| Req/min | `sum(rate(ailab_route_family_total[5m]))` |
| Avg Latency | `avg by (family)(rate(ailab_route_family_latency_ms_sum[5m]) / rate(ailab_route_family_latency_ms_count[5m]))` |
| Profiles Active | `count(count by (profile)(rate(ailab_profile_total[5m])))` |
| SLO State | `ailab_runtime_slo_state` |

#### 01 — Routing & Models
| Panel | Query |
|-------|-------|
| Requests by Route | `sum(rate(ailab_route_family_total[5m])) by (family)` |
| Latency by Route | `avg by (family)(rate(ailab_route_family_latency_ms_sum[5m]) / rate(ailab_route_family_latency_ms_count[5m]))` |
| Prompt Tokens | `rate(ailab_route_family_prompt_tokens_total[5m])` |
| Errors by Route | `rate(ailab_route_family_errors_total[5m])` |
| Greeting FastPath | `rate(ailab_greeting_fastpath_total[5m])` |

#### 02 — Cognitive Profiles
| Panel | Query |
|-------|-------|
| Requests by Profile | `sum(rate(ailab_profile_total[5m])) by (profile)` |
| Profile vs Route | `sum(rate(ailab_profile_total[5m])) by (profile, route_family)` |
| Model by Profile | `sum(rate(ailab_profile_total[5m])) by (profile, model)` |

#### 03 — Tool Governance
| Panel | Query |
|-------|-------|
| Tool Calls by Name | `sum(rate(ailab_tool_call_total[5m])) by (tool_name)` |
| Allowed vs Blocked | `sum(rate(ailab_tool_call_total[5m])) by (result)` |
| By Policy Mode | `sum(rate(ailab_tool_call_total[5m])) by (policy, mode)` |
| Blocked by Reason | `rate(ailab_governance_blocked_actions_by_reason_total[5m])` |

#### 06 — GPU / Inference
| Panel | Query |
|-------|-------|
| GPU Active Requests | `ailab_gpu_active_requests` |
| GPU Utilization | `ailab_gpu_estimated_utilization_pct` |
| GPU by Node | `ailab_gpu_estimated_utilization_pct{node="rx9070"}` |

#### 09 — Runtime Protection (SLO)
| Panel | Query |
|-------|-------|
| SLO State | `ailab_runtime_slo_state` |
| Degradation Level | `ailab_runtime_degradation_level` |
| Timeout Rate | `ailab_runtime_timeout_rate` |
| VRAM Pressure | `ailab_runtime_vram_pressure` |
| GPU Pressure | `ailab_runtime_gpu_pressure` |
| Priority Lane Usage | `rate(ailab_runtime_priority_lane_total[5m])` |
| Circuit Breakers | `ailab_circuit_breaker_state` |
| SLO Violations | `rate(ailab_slo_violations_total[5m])` |
| Concurrent Streams | `ailab_runtime_concurrent_streams` |
| Qwen Parallel | `ailab_runtime_qwen_parallel` |

### TIER 2 — Troubleshooting

#### 04 — Memory Runtime
| Panel | Query |
|-------|-------|
| Recall by Policy | `sum(rate(ailab_memory_recall_total[5m])) by (policy, hit)` |
| Hit Ratio | `sum(rate(ailab_memory_recall_total{hit="true"}[5m])) / sum(rate(ailab_memory_recall_total[5m]))` |
| Chars Injected p95 | `histogram_quantile(0.95, sum(rate(ailab_memory_chars_injected_bucket[5m])) by (le, policy))` |
| Items by Source | `sum(rate(ailab_memory_items_total[5m])) by (source)` |

#### 05 — Execution & Safety
| Panel | Query |
|-------|-------|
| Governance Blocked | `rate(ailab_governance_blocked_actions_total[5m])` |
| Blocked by Route | `rate(ailab_route_family_blocked_total[5m])` |
| Tool Malformed | `rate(ailab_tool_calls_malformed_total[5m])` |
| Fastpath Fallback | `rate(ailab_tool_fastpath_fallback_total[5m])` |
| Evidence Guard Blocks | `rate(ailab_evidence_guard_blocks_total[5m])` |

#### 07 — Infrastructure
| Panel | Query |
|-------|-------|
| Node CPU | `100 - avg by (instance)(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100` |
| Node Memory | `(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100` |
| Container CPU | `sum(rate(container_cpu_usage_seconds_total[5m])) by (name)` |

#### 08 — Incidents & Audit
| Panel | Query |
|-------|-------|
| Route Family Blocked | `rate(ailab_route_family_blocked_total[5m])` |
| Governance by Reason | `rate(ailab_governance_blocked_actions_by_reason_total[5m])` |
| Tool Recall Fallback | `rate(ailab_tool_fastpath_fallback_total[5m])` |
| Hotspot Error Rate | `rate(ailab_hotspot_error_rate[5m])` |

#### 10 — Streaming Quality
| Panel | Query |
|-------|-------|
| Chunks per Stream | `rate(ailab_stream_chunks_total[5m])` |
| Stream Stalls | `rate(ailab_stream_stalls_total[5m])` |
| Finish Inconsistency | `rate(ailab_stream_finish_inconsistent_total[5m])` |
| TTFB p50/p95 | `histogram_quantile(0.5, rate(ailab_first_token_latency_ms_bucket[5m]))` |

#### 11 — Cold Start Analysis
| Panel | Query |
|-------|-------|
| Cold Starts by Model | `rate(ailab_cold_start_total[5m])` |
| Cold Start Reason | `rate(ailab_cold_start_total[5m]) by (reason)` |

### TIER 3 — Profiling / Avanzado

#### 12 — Precision & Confidence
| Panel | Query |
|-------|-------|
| Precision Score | `ailab_operational_precision_score` |
| Confidence Integrity | `ailab_confidence_integrity_score` |
| Authority Conflicts | `rate(ailab_authority_conflicts_total[5m])` |
| Discovery Leakage | `rate(ailab_discovery_leakage_total[5m])` |
| Stale Evidence | `rate(ailab_stale_evidence_total[5m])` |

#### 13 — Cognitive Health
| Panel | Query |
|-------|-------|
| Health Score by Layer | `ailab_cognitive_health_score` |
| Graph Correlation | `ailab_graph_correlation_score` |
| Critical Path Health | `ailab_critical_path_health_score` |
| Critical Path Latency | `histogram_quantile(0.95, rate(ailab_critical_path_latency_ms_bucket[5m]))` |

#### 14 — Governance Drift
| Panel | Query |
|-------|-------|
| Drift Detections | `rate(ailab_governance_drift_detections_total[5m])` |
| Drift Severity | `ailab_governance_drift_severity` |
| Remediations | `rate(ailab_governance_drift_remediation_total[5m])` |

---

## Alertas Prometheus

**19 reglas activas** en `/home/albert/docker/monitorizacion/prometheus/config/rules/ai-lab-route-family-alerts.yml`.

### 🔴 ROJO — STOP burn-in (detención inmediata si se activan)

| Alerta | Expresión | Severidad | Detecta |
|--------|-----------|-----------|---------|
| `ToolFastpathLeakage` | `increase(ailab_tool_fastpath_total{tool_fastpath="true"}[5m]) > 0` | **critical** | Tool fastpath activo en ruta que no debería |
| `GovernanceUnexpectedBlocks` | `increase(ailab_governance_blocked_actions_total[5m]) > 0` | **critical** | Bloqueos de gobernanza inesperados |
| `EmptyResponsesSustained` | `rate(ailab_route_family_errors_total{error="empty_response"}[5m]) > 0.1` | **critical** | Respuestas vacías sostenidas |
| `HardFactsAccidental` | `increase(ailab_router_hard_facts_hits_total[5m]) > 0` | **critical** | HARD_FACTS inyectado accidentalmente |
| `MemoryRecallMinimal` | `increase(ailab_memory_recall_total{policy="minimal"}[5m]) > 0` | **critical** | Memory recall en ruta minimal (contaminación) |
| `PromptInflationRunaway` | `rate(ailab_route_family_prompt_tokens_total[5m]) > 50000` | **critical** | Inflation runaway de tokens de prompt |
| `FinishInconsistencyHigh` | `rate(ailab_stream_finish_inconsistent_total[5m]) > 1` | **critical** | Inconsistencia alta de finalización stream |
| `StreamStallsRepeated` | `rate(ailab_stream_stalls_total[5m]) > 3` | **critical** | Stream stalls repetidos |

### 🟡 AMARILLO — Warning operacional

| Alerta | Expresión | Severidad | Detecta |
|--------|-----------|-----------|---------|
| `MinimalRouteRegression` | `increase(ailab_route_family_prompt_tokens_total{family="minimal"}[10m]) > 500` | warning | Contexto pesado en ruta ligera |
| `ToolFastpathLatencySpike` | `avg by (tool_name)(rate(ailab_tool_call_total[5m])) > 8` | warning | Fastpath lento o backend degradado |
| `CognitiveRouteExplosion` | `increase(ailab_route_family_prompt_tokens_total{family="cognitive"}[10m]) > 12000` | warning | Recall runaway en ruta cognitiva |
| `RouteFamilyErrorRate` | `increase(ailab_route_family_errors_total[5m]) > 0` | warning | Errores recientes en cualquier ruta |
| `GovernanceBlocksSpike` | `increase(ailab_route_family_blocked_total[10m]) > 10` | warning | Bloqueos masivos de governance |
| `SLOViolationRateHigh` | `rate(ailab_slo_violations_total[5m]) > 0` | warning | Violaciones de SLO recientes |
| `GPUVRAMPressureHigh` | `ailab_runtime_vram_pressure > 85` | warning | Presión de VRAM > 85% |
| `CircuitBreakerTripped` | `ailab_circuit_breaker_state{state="OPEN"} > 0` | warning | Circuit breaker abierto en algún modelo |
| `ProfileUnknown` | `increase(ailab_profile_total{profile="unknown"}[5m]) > 0` | warning | Perfil no clasificado |
| `ToolBudgetExceeded` | `sum(rate(ailab_tool_call_total{result="blocked_by_policy"}[5m])) > 0` | warning | Tools bloqueadas por política |
| `MemoryFallback` | `sum(rate(ailab_memory_recall_total{policy="fallback"}[5m])) > 0` | warning | Memory injector fallando a legacy |

---

## URLs de acceso

| Servicio | URL |
|----------|-----|
| **Grafana** | `http://192.168.1.40:3000` |
| **Prometheus** | `http://192.168.1.40:9090` |
| **Gateway métricas** | `http://192.168.1.30:8008/metrics` **★ tráfico real** |
| **Router métricas** | `http://192.168.1.30:8083/metrics` ⚠ sin tráfico |
| **Live API métricas** | `http://192.168.1.30:8084/metrics` ⚠ sin tráfico |

> **⚠ NOTA:** `192.168.1.30:3001` es **Grafana v12.0.2**, NO AnythingLLM.
> AnythingLLM está en `192.168.1.50:3001` (LAN).

---

## Provisioning

Los dashboards se cargan automáticamente desde:

```
/home/albert/docker/monitorizacion/grafana/provisioning/dashboards/AI-LAB/
```

Los archivos `*.json` se importan en caliente. Recarga sin reiniciar:

```bash
docker exec grafana kill -HUP 1
```

Las reglas de alerta están en:

```
/home/albert/docker/monitorizacion/prometheus/config/rules/ai-lab-route-family-alerts.yml
```

Recarga de reglas:

```bash
docker exec prometheus kill -HUP 1
```

---

## Troubleshooting de métricas

### Dashboard sin datos — checklist

Cuando un panel Grafana muestra "Sin datos", seguir este orden:

1. **Verificar que la métrica existe en el endpoint correcto:**
   ```bash
   curl -s http://192.168.1.30:8008/metrics | grep "NOMBRE_METRICA"
   ```

2. **Si existe pero con valor 0**, verificar que el code path se ejecuta:
   - Feature flags activos (`AI_LAB_ENABLE_MEMORY_INJECTOR`, `AI_LAB_ENABLE_PROFILES`, etc.)
   - Import errors silenciosos
   - Que el perfil/ruta correcta esté recibiendo tráfico

3. **Si no existe en :8008 pero sí en :8083 o :8084**, el tráfico va al proceso equivocado.
   El gateway (:8008) es el único que recibe tráfico de chat real.

4. **Si la métrica existe con datos en :8008 pero Grafana no la ve**, verificar la query PromQL directamente:
   ```bash
   curl -s "http://192.168.1.40:9090/api/v1/query?query=METRICA" | jq .
   ```

5. **Las métricas `rate()` requieren ≥5 min de tráfico continuo** para devolver datos.

6. **Métricas que dependen de feature flags**:
   - `AI_LAB_ENABLE_MEMORY_INJECTOR=false` → `ailab_memory_*` = 0
   - `AI_LAB_ENABLE_PROFILES=false` → `ailab_profile_total` = 0
   - `AI_LAB_SLO_DRY_RUN=true` → SLO enforcement observado pero no activo

### Métricas flatlineadas — causas comunes

| Síntoma | Causa probable |
|---------|---------------|
| Todas las `ailab_*` en 0 | Gateway caído o scrape target mal configurado |
| Solo `ailab_route_family_*` en 0 | Zero traffic window o classifier no ejecutándose |
| `ailab_memory_*` en 0 | `AI_LAB_ENABLE_MEMORY_INJECTOR=false` |
| `ailab_slo_*` planas | `AI_LAB_SLO_DRY_RUN=true` o SLO disabled |
| `ailab_precision_*` planas | `precision_engine` no inicializado o import falló |
| `ailab_graph_*` planas | GitNexus index no disponible o no se consultó |
| `ailab_*` solo en :8083 | Router recibiendo tráfico que debería ir al gateway |

---

## Auditoría (3er canal)

Además de Prometheus y stdout, el runtime emite eventos de auditoría en JSONL:

```
/opt/ai-lab/runtime/state/governance_audit.jsonl
/opt/ai-lab/runtime/state/runtime_sensor_fusion.jsonl
```

### governance_audit.jsonl

Eventos clave de gobernanza:

| Evento | Descripción |
|--------|-------------|
| `profile_applied` | Perfil cognitivo aplicado a una request |
| `tool_call_allowed` | Tool aceptada por política |
| `tool_call_blocked_by_policy` | Tool bloqueada por política activa |
| `tool_call_blocked_by_denylist` | Tool bloqueada por denylist |
| `memory_injector_failed` | Fallo del memory injector |
| `route_family_selected` | Ruta clasificada (family + variant) |
| `slo_state_change` | Cambio de estado SLO |
| `degradation_level_change` | Cambio de nivel de degradación |
| `circuit_breaker_state_change` | Cambio de estado de circuit breaker |
| `evidence_guard_block` | Bloqueo por evidence guard |
| `governance_drift_detected` | Drift entre governance declarada y observada |

### runtime_sensor_fusion.jsonl

Snapshots periódicos del estado observado del runtime:

| Campo | Descripción |
|-------|-------------|
| `timestamp` | ISO 8601 |
| `gateway_health` | Salud del gateway |
| `inference_nodes` | Estado de nodos de inferencia |
| `active_models` | Modelos activos |
| `slo_state` | Estado SLO actual |
| `degradation_level` | Nivel de degradación |
| `topology` | Topología observada |
| `evidence_confidence` | Confianza de evidencia |

**Ver en vivo:**
```bash
tail -f /opt/ai-lab/runtime/state/governance_audit.jsonl | jq .
```

**Filtrar por evento:**
```bash
grep '"profile_applied"' /opt/ai-lab/runtime/state/governance_audit.jsonl | tail -20 | jq .
```
