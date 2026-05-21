---
title: "Observabilidad"
summary: "Documentación de observabilidad de AI-LAB: métricas Prometheus, dashboards Grafana, alertas, audit trail, SLO enforcement y error taxonomy."
order: 4
---

## Qué contiene

- **FASE 29 — Runtime Observability** — gateway hardening, real streaming, three-model runtime, SLO enforcement, runtime grounding, error taxonomy, SLO health endpoint, parallel tool call hardening
- **Dashboards Grafana** — 15 dashboards, 100+ métricas `ailab_*`
- **Alertas** — 19 reglas con health checks
- **Audit trail** — shards diarios en JSONL
- **Replay API** — trazabilidad completa de cada request

## Stack

| Componente | Host | Puerto |
|------------|------|--------|
| Prometheus | 192.168.1.40 | 9090 |
| Grafana | 192.168.1.40 | 3000 |
| Gateway metrics | 192.168.1.30 | 8008/metrics |
| Router metrics | 192.168.1.30 | 8083/metrics |
| Live API metrics | 192.168.1.30 | 8084/metrics |

## Checkpoint actual

**CP-29.4.4-D-PARALLEL-TOOLCALL-HARDENING-STABLE** — SLO enforcement, error taxonomy, health endpoint always-on, parallel tool call hardening.
