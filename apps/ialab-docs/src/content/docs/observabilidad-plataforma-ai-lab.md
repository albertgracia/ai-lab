---
title: "Observabilidad — Plataforma AI-LAB"
summary: "Infraestructura completa de observabilidad del AI-LAB: Prometheus, Grafana, 8 dashboards organizados por capas del runtime, alertas y metricas."
order: 48
---

## Infraestructura

| Componente | Host | Puerto | Estado |
|-----------|------|--------|--------|
| **Prometheus** | 192.168.1.40 | 9090 | Active |
| **Grafana** | 192.168.1.40 | 3000 | Active |
| **Alertmanager** | (pendiente) | — | — |

### Scrape targets AI-LAB

| Job | Target | Métricas |
|-----|--------|----------|
| `ai-lab-router` | 192.168.1.30:8083/metrics | Perfiles, routing, tools, memoria |
| `ai-lab-gateway` | 192.168.1.30:8008/metrics | Gateway, rate limit, sesiones |
| `ai-lab-live-api` | 192.168.1.30:8084/metrics | Estado vivo, control plane |
| `ai-lab-node` | 192.168.1.30:9100/metrics | CPU, RAM, disco |
| `ai-lab-cadvisor` | 192.168.1.30:8081/metrics | Contenedores Docker |
| `ai-lab-gpu-rx9070` | 192.168.1.50:9182/metrics | VRAM, temperatura, uso GPU |
| `ai-lab-gpu-rx7900xt` | 192.168.1.60:9182/metrics | VRAM, temperatura, uso GPU |

---

## Dashboards Grafana (folder `AI-LAB`)

| # | Dashboard | UID | Capa |
|---|-----------|-----|------|
| 00 | **Executive Overview** | `ai-lab-overview` | Resumen general |
| 01 | **Routing & Models** | `ai-lab-runtime` | Rutas, modelos, latencia |
| 02 | **Cognitive Profiles** | `ai-lab-profiles` | Perfiles cognitivos (FASE 21) |
| 03 | **Tool Governance** | `ai-lab-tools` | Tools + gobernanza (FASE 22) |
| 04 | **Memory Runtime** | `ai-lab-memory` | Memoria semantica (FASE 23) |
| 05 | **Execution & Safety** | `ai-lab-safety` | Seguridad y bloques |
| 06 | **GPU / Inference** | `ai-lab-gpus` | RX9070 / RX7900XT |
| 07 | **Infrastructure** | `ai-lab-infra` | Docker, host, red |

### Executive Overview

Resumen de salud del runtime en un vistazo.

| Panel | Métrica |
|-------|---------|
| Router UP | `up{job="ai-lab-router"}` |
| Gateway UP | `up{job="ai-lab-gateway"}` |
| Requests/min | `rate(ailab_router_chat_requests_total[5m])` |
| Error rate | `rate(ailab_route_family_errors_total[5m]) / rate(ailab_router_chat_requests_total[5m])` |
| Avg latency | `avg by (family)(rate(ailab_route_family_latency_ms_sum[5m]) / rate(ailab_route_family_latency_ms_count[5m]))` |
| Profiles active | `count(count by (profile)(rate(ailab_profile_total[5m])))` |

### Cognitive Profiles

Distribucion de uso de perfiles cognitivos.

| Panel | Métrica |
|-------|---------|
| Requests by profile | `sum(rate(ailab_profile_total[5m])) by (profile)` |
| Profile vs route | `sum(rate(ailab_profile_total[5m])) by (profile, route_family)` |
| Model by profile | `sum(rate(ailab_profile_total[5m])) by (profile, model)` |

### Tool Governance

Uso y bloqueo de herramientas.

| Panel | Métrica |
|-------|---------|
| Tool calls by name | `sum(rate(ailab_tool_call_total[5m])) by (tool_name)` |
| Allowed vs blocked | `sum(rate(ailab_tool_call_total[5m])) by (result)` |
| By policy mode | `sum(rate(ailab_tool_call_total[5m])) by (policy, mode)` |
| Blocked by reason | `rate(ailab_governance_blocked_actions_by_reason_total[5m])` |

### Memory Runtime

Recall semantico y uso de memoria.

| Panel | Métrica |
|-------|---------|
| Recall by policy | `sum(rate(ailab_memory_recall_total[5m])) by (policy, hit)` |
| Hit ratio | `sum(rate(ailab_memory_recall_total{hit="true"}[5m])) / sum(rate(ailab_memory_recall_total[5m]))` |
| Chars injected p95 | `histogram_quantile(0.95, rate(ailab_memory_chars_injected_bucket[5m]))` |
| Items by source | `sum(rate(ailab_memory_items_total[5m])) by (source)` |

---

## Alertas Prometheus

| Alerta | Expresion | Severidad |
|--------|-----------|-----------|
| `MinimalRouteRegression` | `increase(ailab_route_family_prompt_tokens_total{family="minimal"}[10m]) > 500` | warning |
| `ToolFastpathLatencySpike` | `avg latency tool_fastpath > 8000ms` | critical |
| `CognitiveRouteExplosion` | `increase(ailab_route_family_prompt_tokens_total{family="cognitive"}[10m]) > 12000` | warning |
| `RouteFamilyErrorRate` | `increase(ailab_route_family_errors_total[5m]) > 0` | critical |
| `GovernanceBlocksSpike` | `increase(ailab_route_family_blocked_total[10m]) > 10` | warning |
| `ProfileUnknown` | `increase(ailab_profile_total{profile="unknown"}[5m]) > 0` | warning |
| `ToolBudgetExceeded` | `sum(rate(ailab_tool_call_total{result="blocked_by_policy"}[5m])) > 0` | warning |
| `MemoryFallback` | `sum(rate(ailab_memory_recall_total{policy="fallback"}[5m])) > 0` | warning |

---

## Provisioning

Los dashboards se auto-cargan desde:

```
/home/albert/docker/monitorizacion/grafana/provisioning/dashboards/AI-LAB/
```

Grafana los detecta automaticamente al arrancar o al hacer reload:

```bash
docker exec grafana kill -HUP 1
```

Las alertas estan en:

```
/home/albert/docker/monitorizacion/prometheus/config/rules/ai-lab-route-family-alerts.yml
```

---

## URLs

- **Grafana**: `http://192.168.1.40:3000`
- **Prometheus**: `http://192.168.1.40:9090`
- **Router métricas**: `http://192.168.1.30:8083/metrics`
- **Gateway métricas**: `http://192.168.1.30:8008/metrics`
