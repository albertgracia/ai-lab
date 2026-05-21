---
title: "Estado Actual del Runtime"
summary: "Descripción del estado actual del runtime AI-LAB: control-plane, backend, modelos activos, servicios principales, endpoints y checkpoints."
order: 10
---

## Arquitectura general

```
CONTROL PLANE
ubuntu-ialab
192.168.1.30

INFERENCE BACKEND ACTIVO
RX9070 · 192.168.1.50
llama.cpp v2.14.0 (Vulkan/ROCm)

INFERENCE BACKEND FUTURO (no activo)
RX7900XT · 192.168.1.60
Nodo apagado — previsto para FASE 31A
```

## Modelos activos

| Modelo | Estado | Host | Uso |
|--------|--------|------|-----|
| llama-3.1-8b-instruct | Activo | 192.168.1.50:1234 | Minimal, observe, greetings, light prompts |
| qwen2.5-coder-14b-instruct | Activo | 192.168.1.50:1234 | Coding, report, architecture, reasoning |
| nomic-embed-text-v1.5 | Activo | 192.168.1.50:1234 | Embeddings, semantic recall |
| qwen3.6-27b | Desactivado | 192.168.1.50:1234 | No borrado del disco, disponible para tests manuales |
| qwen2.5-coder-32b | DOWN | 192.168.1.60:1234 | Nodo RX7900XT apagado |

> **Nota:** active != loaded != discoverable != disabled. qwen3.6-27b está DISABLED. El modelo previsto para RX7900XT es `gpt-oss-20b-derestricted Q4_K_M`.

## Servicios principales

| Servicio | Puerto | Proceso | Tráfico |
|----------|--------|---------|---------|
| ailab-gateway | 8008 | openai_gateway.py | Único entrypoint de chat |
| ailab-router | 8083 | router_api.py (FastAPI) | API interna (/status, /profiles, /replay) |
| ailab-live-api | 8084 | live_api.py | API de estado, embeddings |
| ailab-docs | 4322 | Astro preview | Documentación |
| ailab-metrics | 3010 | Next.js SSR | Dashboard público |
| ailab-heartbeat | — | Heartbeat persistente | Latido de cluster |
| ailab-live-state | — | State snapshot | Snapshot periódico |
| ailab-runner | — | GitHub Actions Runner | CI/CD |

## Endpoints always-on (9/9)

| Endpoint | Propósito |
|----------|-----------|
| GET /health | Salud del gateway |
| GET /slo/health | Estado SLO completo |
| GET /runtime/sensors | Snapshot completo de sensor fusion (FASE 30I) |
| GET /runtime/maturity | Descriptores de madurez del runtime |
| GET /runtime/topology | Topología y dominio de fallo |
| GET /runtime/governance | Visibilidad de decisiones governance |
| GET /runtime/routes/semantics | Semántica operacional por route-family |
| GET /runtime/reports/discipline | Disciplina de reportes operacionales |
| GET /runtime/reports/evidence | Catálogo de evidencia y thresholds |

## Observabilidad

| Componente | Host | Puerto |
|------------|------|--------|
| Prometheus | 192.168.1.40 | 9090 |
| Grafana | 192.168.1.40 | 3000 |
| Prometheus config | /home/albert/docker/monitorizacion/prometheus/ | prometheus.yml |
| Grafana provisioning | /home/albert/docker/monitorizacion/grafana/provisioning/ | Dashboards JSON auto-load |

100+ métricas `ailab_*`, 15 dashboards, 19 alertas activas.
Sensor fusion: 13 dominios observados, 4 métricas nuevas (`ailab_sensor_fusion_*`, `ailab_observed_runtime_context_size_bytes`).

## Checkpoints principales

```
CP-28.1-PLANNER-RUNTIME-SKELETON-STABLE
CP-28.2-READONLY-EXECUTOR-STABLE
CP-28.2-B-READONLY-BURNIN-STABLE
CP-28.3-SANDBOX-WRITE-STABLE
CP-28.3-B-SANDBOX-WRITE-BURNIN-STABLE
CP-29.2-B-STREAMING-BURNIN-STABLE
CP-29.3-THREE-MODEL-RUNTIME-STABLE
CP-29.4-SLO-ENFORCEMENT-STABLE
CP-29.4.4-ERROR-TAXONOMY-STABLE
CP-29.4.4-C-SLO-HEALTH-ENDPOINT-STABLE
CP-29.4.4-D-PARALLEL-TOOLCALL-HARDENING-STABLE
CP-30A-RUNTIME-STATE-FOUNDATION-STABLE
CP-30B-MODEL-STATE-AWARE-STABLE
CP-30E-GOVERNANCE-VISIBILITY-STABLE
CP-30F-ROUTE-SEMANTICS-STABLE
CP-30G-OPERATIONAL-REPORTING-STABLE
CP-30H-RUNTIME-EVIDENCE-ENFORCEMENT-STABLE
CP-30I-RUNTIME-SENSOR-FUSION-STABLE
```

## Fase actual

**30I** — Runtime Sensor Fusion. 186 tests PASS. 30 tags desde CP-21B-STABLE.
