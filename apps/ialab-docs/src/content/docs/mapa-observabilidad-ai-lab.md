---
title: "Mapa de Observabilidad — AI-LAB"
summary: "Mapa completo del flujo de observabilidad del AI-LAB: generacion de metricas, scrape Prometheus, dashboards Grafana, alertas y auditoria."
order: 49
---

## Flujo completo

```
┌─────────────────────────────────────────────────────────────┐
│                     AI-LAB Runtime (:8083, :8008)           │
│                                                             │
│  router_api.py  ──►  prometheus_metrics.py                  │
│  openai_gateway.py ──►  profile_loader, tool_policy,        │
│  context_shaper.py        memory_injector                   │
│                                                             │
│  Generan métricas:                                          │
│    ailab_profile_total                                       │
│    ailab_tool_call_total                                     │
│    ailab_memory_recall_total                                 │
│    ailab_route_family_*                                      │
│    ailab_governance_blocked_*                                │
│                                                             │
└──────────────┬──────────────────────────────────────────────┘
               │ /metrics (Prometheus format)
               ▼
┌─────────────────────────────────────────────────────────────┐
│              Prometheus (192.168.1.40:9090)                 │
│                                                             │
│  scrape_configs:                                            │
│    ai-lab-router     192.168.1.30:8083/metrics   (15s)     │
│    ai-lab-gateway    192.168.1.30:8008/metrics   (15s)     │
│    ai-lab-live-api   192.168.1.30:8084/metrics   (15s)     │
│    ai-lab-node       192.168.1.30:9100/metrics   (15s)     │
│    ai-lab-cadvisor   192.168.1.30:8081/metrics   (30s)     │
│    ai-lab-gpu-rx9070 192.168.1.50:9182/metrics   (30s)     │
│                                                             │
│  rule_files:                                                │
│    ai-lab-route-family-alerts.yml (8 alertas)               │
│                                                             │
└──────────────┬──────────────────────────────────────────────┘
               │ query
               ▼
┌─────────────────────────────────────────────────────────────┐
│               Grafana (192.168.1.40:3000)                   │
│                                                             │
│  Datasource: Prometheus  (UID: PBFA97CFB590B2093)           │
│  Folder: AI-LAB  (10 dashboards)                            │
│                                                             │
│  Provisioning:                                              │
│    /home/albert/docker/monitorizacion/grafana/              │
│    provisioning/dashboards/AI-LAB/*.json                    │
│                                                             │
│  00 Executive Overview          ai-lab-overview             │
│  01 Routing & Models            ai-lab-runtime              │
│  02 Cognitive Profiles          ai-lab-profiles             │
│  03 Tool Governance             ai-lab-tools                │
│  04 Memory Runtime              ai-lab-memory               │
│  05 Execution & Safety          ai-lab-safety               │
│  06 GPU / Inference             ai-lab-gpus                 │
│  07 Infrastructure              ai-lab-infra                │
│  08 Incidents & Audit           ai-lab-incidents            │
│                                                             │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│                    3 Canales de Observabilidad               │
│                                                             │
│  1. stdout  → journalctl -u ailab-gateway | grep "profile=" │
│  2. audit   → /opt/ai-lab/runtime/state/                   │
│               governance_audit.jsonl                        │
│  3. Prometheus → :8083/metrics + :8008/metrics              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Métricas Prometheus (26 familias)

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

### FASE 19 — Routing (6)
```
ailab_route_family_total{family}
ailab_route_family_latency_ms{family}      (histogram)
ailab_route_family_prompt_tokens_total{family}
ailab_route_family_completion_tokens_total{family}
ailab_route_family_errors_total{family}
ailab_route_family_blocked_total{family}
```

### Gobernanza (2)
```
ailab_governance_blocked_actions_total
ailab_governance_blocked_actions_by_reason_total{reason}
```

### Router base (3)
```
ailab_router_chat_requests_total
ailab_router_hard_facts_hits_total
ailab_embedding_truncations_total
ailab_embedding_input_chars
ailab_recall_query_chars
```

### Tool-specific legacy (2)
```
ailab_tool_fastpath_total
ailab_tool_fastpath_fallback_total
```

---

## Scrape targets

| Job | Host:Port | Intervalo | Métricas |
|-----|-----------|-----------|----------|
| `ai-lab-router` | 192.168.1.30:8083 | 15s | Perfiles, routing, tools, memoria |
| `ai-lab-gateway` | 192.168.1.30:8008 | 15s | Gateway, rate limit, sesiones |
| `ai-lab-live-api` | 192.168.1.30:8084 | 15s | Estado vivo |
| `ai-lab-node` | 192.168.1.30:9100 | 15s | CPU, RAM, disco |
| `ai-lab-cadvisor` | 192.168.1.30:8081 | 30s | Contenedores Docker |
| `ai-lab-gpu-rx9070` | 192.168.1.50:9182 | 30s | VRAM, GPU usage |
| `ai-lab-gpu-metrics` | 192.168.1.50:9183 | 30s | Temperatura, power, tokens/s |

---

## Dashboards — Consultas clave por panel

### 00 — Executive Overview
| Panel | Query |
|-------|-------|
| Router UP | `up{job="ai-lab-router"}` |
| Req/min | `sum(rate(ailab_router_chat_requests_total[5m]))` |
| Avg Latency | `avg by (family)(rate(ailab_route_family_latency_ms_sum[5m]) / rate(ailab_route_family_latency_ms_count[5m]))` |
| Profiles Active | `count(count by (profile)(rate(ailab_profile_total[5m])))` |

### 01 — Routing & Models
| Panel | Query |
|-------|-------|
| Requests by Route | `sum(rate(ailab_route_family_total[5m])) by (family)` |
| Latency by Route | `avg by (family)(rate(ailab_route_family_latency_ms_sum[5m]) / rate(ailab_route_family_latency_ms_count[5m]))` |
| Prompt Tokens | `rate(ailab_route_family_prompt_tokens_total[5m])` |
| Errors by Route | `rate(ailab_route_family_errors_total[5m])` |

### 02 — Cognitive Profiles
| Panel | Query |
|-------|-------|
| Requests by Profile | `sum(rate(ailab_profile_total[5m])) by (profile)` |
| Profile vs Route | `sum(rate(ailab_profile_total[5m])) by (profile, route_family)` |
| Model by Profile | `sum(rate(ailab_profile_total[5m])) by (profile, model)` |

### 03 — Tool Governance
| Panel | Query |
|-------|-------|
| Tool Calls by Name | `sum(rate(ailab_tool_call_total[5m])) by (tool_name)` |
| Allowed vs Blocked | `sum(rate(ailab_tool_call_total[5m])) by (result)` |
| By Policy Mode | `sum(rate(ailab_tool_call_total[5m])) by (policy, mode)` |
| Blocked by Reason | `rate(ailab_governance_blocked_actions_by_reason_total[5m])` |

### 04 — Memory Runtime
| Panel | Query |
|-------|-------|
| Recall by Policy | `sum(rate(ailab_memory_recall_total[5m])) by (policy, hit)` |
| Hit Ratio | `sum(rate(ailab_memory_recall_total{hit="true"}[5m])) / sum(rate(ailab_memory_recall_total[5m]))` |
| Chars Injected p95 | `histogram_quantile(0.95, sum(rate(ailab_memory_chars_injected_bucket[5m])) by (le, policy))` |
| Items by Source | `sum(rate(ailab_memory_items_total[5m])) by (source)` |

### 05 — Execution & Safety
| Panel | Query |
|-------|-------|
| Governance Blocked | `rate(ailab_governance_blocked_actions_total[5m])` |
| Blocked by Route | `rate(ailab_route_family_blocked_total[5m])` |
| Tool Malformed | `rate(ailab_tool_calls_malformed_total[5m])` |
| Fastpath Fallback | `rate(ailab_tool_fastpath_fallback_total[5m])` |

### 08 — Incidents & Audit
| Panel | Query |
|-------|-------|
| Route Family Blocked | `rate(ailab_route_family_blocked_total[5m])` |
| Governance by Reason | `rate(ailab_governance_blocked_actions_by_reason_total[5m])` |
| Tool Recall Fallback | `rate(ailab_tool_fastpath_fallback_total[5m])` |

---

## Alertas Prometheus

| Alerta | Expresion | Severidad | Detecta |
|--------|-----------|-----------|---------|
| `MinimalRouteRegression` | `increase(prompt_tokens{family="minimal"}[10m]) > 500` | warning | Contexto pesado en ruta ligera |
| `ToolFastpathLatencySpike` | `avg latency tool_fastpath > 8000ms` | critical | Fastpath roto o backend lento |
| `CognitiveRouteExplosion` | `increase(prompt_tokens{family="cognitive"}[10m]) > 12000` | warning | Recall runaway |
| `RouteFamilyErrorRate` | `increase(errors[5m]) > 0` | critical | Errores recientes |
| `GovernanceBlocksSpike` | `increase(blocked[10m]) > 10` | warning | Abuso de prompts o tools |
| `ProfileUnknown` | `increase(profile_total{profile="unknown"}[5m]) > 0` | warning | Perfil no clasificado |
| `ToolBudgetExceeded` | `sum(rate(tool_call_total{result="blocked_by_policy"}[5m])) > 0` | warning | Tools bloqueadas por politica |
| `MemoryFallback` | `sum(rate(memory_recall_total{policy="fallback"}[5m])) > 0` | warning | Memory injector fallando a legacy |

---

## URLs de acceso

| Servicio | URL |
|----------|-----|
| **Grafana** | `http://192.168.1.40:3000` |
| **Prometheus** | `http://192.168.1.40:9090` |
| **Router métricas** | `http://192.168.1.30:8083/metrics` |
| **Gateway métricas** | `http://192.168.1.30:8008/metrics` |
| **Live API métricas** | `http://192.168.1.30:8084/metrics` |

---

## Provisioning

Los dashboards se cargan automaticamente desde:

```
/home/albert/docker/monitorizacion/grafana/provisioning/dashboards/AI-LAB/
```

Recarga en caliente sin reiniciar:

```bash
docker exec grafana kill -HUP 1
```

Las reglas de alerta estan en:

```
/home/albert/docker/monitorizacion/prometheus/config/rules/ai-lab-route-family-alerts.yml
```

Recarga de reglas:

```bash
docker exec prometheus kill -HUP 1
```

---

## Auditoria (3er canal)

Ademas de Prometheus y stdout, el runtime emite eventos de auditoria en:

```
/opt/ai-lab/runtime/state/governance_audit.jsonl
```

Eventos clave:
- `profile_applied` — perfil cognitivo aplicado
- `tool_call_allowed` / `tool_call_blocked_by_policy` — tools aceptadas o bloqueadas
- `tool_call_blocked` — tool bloqueada por governance
- `memory_injector_failed` — fallo del memory injector
- `route_family_selected` — ruta clasificada
