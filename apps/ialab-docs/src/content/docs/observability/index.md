---
title: "Observabilidad"
summary: "Documentación de observabilidad de AI-LAB: métricas Prometheus, dashboards Grafana, alertas, audit trail, SLO enforcement y error taxonomy."
order: 4
---

## Qué contiene

- **FASE 30I — Sensor Fusion** — Prometheus como source of truth, 13 dominios, GPU metrics en vivo, observed/derived separation, freshness labels
- **GPU Metrics Integration** — integración viva de RX9070/RX7900XT dentro del contrato operacional
- **Sensor Domains** — mapa de dominios, prioridades y confidence per-domain
- **Grafana Dashboard Map** — relación entre dashboards y contratos del runtime
- **FASE 29 — Runtime Observability** — gateway hardening, real streaming, three-model runtime, SLO enforcement, runtime grounding, error taxonomy, SLO health endpoint, parallel tool call hardening
- **Prometheus Runtime Integration** — PrometheusQueryClient, cache TTL, target discovery, GPU dynamic metrics
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
| GPU metrics endpoint | 192.168.1.50 | 9183 |

## Checkpoint actual

**CP-30I-D-SENSOR-SEMANTICS-NORMALIZED-STABLE** — contrato 30I-D, `/runtime/sensors` normalizado, `gpu_operational_summaries`, `source_quality` y semántica operacional estable.
