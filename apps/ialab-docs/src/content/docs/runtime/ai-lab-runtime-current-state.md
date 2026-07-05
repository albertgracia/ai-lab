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

INVENTARIO OFFLINE
RX7900XT · 192.168.1.60
Nodo apagado — expected_offline, no routable, no activo
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
| ailab-hermes-status | 8095 | hermes/endpoint.py | Estado Hermes Enterprise |
| ailab-docs | 4322 | Astro preview | Documentación |
| ailab-metrics | 3010 | Next.js SSR | Dashboard público |
| ailab-heartbeat | — | Heartbeat persistente | Latido de cluster |
| ailab-live-state | — | State snapshot | Snapshot periódico |
| ailab-runner | — | GitHub Actions Runner | CI/CD |

## Endpoints always-on (10/10)

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
| GET /hermes/status | Estado completo Hermes Enterprise (SOUL, capabilities, operators, hooks, MCP, governance) |

### Hermes Enterprise — componentes disponibles para consulta

Hermes Enterprise Core está desplegado en `runtime/hermes/` y expone los siguientes subsistemas vía `GET /hermes/status` en el puerto `:8095`:

- **SOUL** — semilla ontológica: truth_model, boundaries, protocols, domains, identity, schema
- **Capability Registry** — registro de capacidades del runtime con validación y políticas
- **Operator Registry** — operadores registrados con validación profunda (12 reglas)
- **Hook Registry** — ciclo de vida de hooks (todos declarativos, `enabled: false`)
- **MCP Registry** — servidores MCP declarados (prometheus, marketplace-mcp como planned)
- **Dynamic Governance** — 4 modos (NORMAL/ELEVATED/DEGRADED/LOCKDOWN), 6 señales trigger, anti-flapping 30s

Todos los componentes están en modo declarativo-validación. No hay enforcement activo ni hooks ejecutándose.

## Observabilidad

| Componente | Host | Puerto |
|------------|------|--------|
| Prometheus | 192.168.1.40 | 9090 |
| Grafana | 192.168.1.40 | 3000 |
| Prometheus config | /home/albert/docker/monitorizacion/prometheus/ | prometheus.yml |
| Grafana provisioning | /home/albert/docker/monitorizacion/grafana/provisioning/ | Dashboards JSON auto-load |

100+ métricas `ailab_*`, 15 dashboards (carpeta AI-LAB, TIER 1 y TIER 2), 19 alertas activas.
Sensor fusion: 13 dominios observados, 4 métricas nuevas (`ailab_sensor_fusion_*`, `ailab_observed_runtime_context_size_bytes`).

## Knowledge Base (AnythingLLM Enterprise)

| Recurso | Valor |
|---------|-------|
| Host AnythingLLM | 192.168.1.50:3001 |
| Workspaces activos | 7 |
| Total vectores | 1304 |
| Embedder | text-embedding-multilingual-e5-small (Q8_0) |
| Documentos importados | 84 (canónico) + 53 (evidence) + 19 (MCP/A2A) + 8 (runbooks) + etc. |
| Baseline | Congelada en CP-ANYTHINGLLM-ENTERPRISE-04-COMPLETE |
| Estado | ✅ RAG E2E validation 100% |

## Checkpoints principales

### Fases tempranas (Phase 1–12)

```
phase-1-stable
phase-2-stable
phase-2-gpu-telemetry
phase-3-grounded-opencode-runtime
phase-4-opencode-router-live
phase-5-cognitive-agent-router
phase-6-weighted-intent-routing
phase-6-distributed-cognition-v1
phase8-cognitive-observability-stable
phase12-supervised-self-optimization
```

### Bloques 21–27 — Runtime profiling, memoria, SLO temprano

```
CP-21B-STABLE
CP-22B-STABLE
CP-23A-FOUNDATION
CP-23A-MEMORY-SAFE
CP-23A-MODEL-ALIAS-FIX
CP-23B-QUALITY-GATE
CP-23B-RECALL-STABILITY
CP-24-ANALYTICS
CP-25-OPENCODE-PRODUCTION
CP-26-OPENWEBUI-PRODUCTION
CP-26.1-OBSERVABILITY-v2
CP-26.1.1-COMPLETION-FINALIZATION-FIX
CP-26.1.2-REPORT-ROUTING-FIX
CP-26.2-UX-COGNITIVE-QUALITY
CP-27-RUNTIME-STABILIZATION
```

### Bloques 28–30 — Agentes, streaming, SLO enforcement, sensor fusion

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
CP-30I-B-SENSOR-FUSION-HARDENED-STABLE
CP-30I-C-SENSOR-SUMMARY-EXPOSURE-STABLE
CP-30I-D-SENSOR-SEMANTICS-NORMALIZED-STABLE
CP-30I-E-OPERATIONAL-RESPONSE-FORMATTING-STABLE
CP-30I-F-RUNTIME-COGNITIVE-COMPRESSION-STABLE
CP-30I-F0-RUNTIME-MODEL-ROUTING-CLEANUP-STABLE
CP-30I-G-RUNTIME-GROUNDING-STABLE
```

### Bloques 31–36 — Madurez semántica, cognición, precisión

```
CP-OBS-31A-OBSERVABILITY-SOURCE-OF-TRUTH-STABLE
CP-OBS-31A.1-PROMETHEUS-AUTHORITY-AUDIT-STABLE
CP-OBS-31A.2-GRAFANA-DRIFT-AUDIT-STABLE
CP-OBS-31A.3-RUNTIME-OBSERVABILITY-ALIGNMENT-STABLE
CP-OBS-31A.4-OBSERVABILITY-REMEDIATION-PLAN-STABLE
CP-OBS-31A.5-EXECUTOR-STABLE
CP-31B-RUNTIME-SEMANTIC-MATURITY-STABLE
CP-31B-HF1-OPENCODE-CONTEXT-ALIGNMENT-STABLE
CP-31C-OPERATIONAL-REPORTING-DISCIPLINE-STABLE
CP-35C-LIVE-AUTHORITY-BACKED-COGNITION-STABLE
CP-35D-OPERATIONAL-FAST-PATH-STABLE
CP-35D-HF1-FASTPATH-ROUTING-PRIORITY-STABLE
CP-36A-OPERATIONAL-INCIDENT-INTELLIGENCE-STABLE
CP-DEV-36X-CODEBASE-MEMORY-INTEGRATION-STABLE
CP-DOC-36X-GITNEXUS-STRUCTURAL-COGNITION-STABLE
CP-DOC-36X-SPANISH-LOCALIZATION-STABLE
CP-36B-RUNTIME-PRECISION-MODE-STABLE
```

### Bloques 37–40 — Estabilidad, release hardening, SLO drift watch

```
CP-38A-RUNTIME-DEEP-AUDIT-01-STABLE
CP-38B-GATEWAY-SHUTDOWN-GRACEFUL-01-STABLE
CP-38C-GITNEXUS-NAPI-ERROR-TRIAGE-01-STABLE
CP-38D-RUNTIME-STABILITY-SNAPSHOT-01-STABLE
CP-39A-OPENCODE-GATEWAY-CONTRACT-HARDENING-01-STABLE
CP-39B-RUNTIME-OBSERVABILITY-ALERTS-01-STABLE
CP-39C-COGNITIVE-HEALTH-FOLLOWUP-01-STABLE
CP-39E-RUNTIME-STABILIZATION-RELEASE-CLOSE-01-STABLE
CP-40A-POST-RELEASE-SLO-DRIFT-WATCH-01-STABLE
```

### Gobernanza, routing, multi-GPU readiness

```
CP-GITNEXUS-FIRST-ACTIVATION-01
CP-SLO-ENFORCEMENT-01
CP-VALIDATION-AUTHORITY-01
CP-AUTONOMOUS-OBSERVABILITY-TRIAGE-01
CP-OPERATOR-INTENT-REASONING-01
CP-MULTIGPU-READINESS-01
CP-DYNAMIC-NODE-REGISTRY-01
CP-AI-LAB-MULTI-NODE-ROUTING-01
CP-INTELLIGENT-FALLBACK-ENGINE-01
CP-CAPABILITY-SCHEDULER-01
CP-49A-POOL-ADMIN-API-READONLY-01
```

### Hermes Enterprise

```
CP-E01A-SOUL-ENTERPRISE-SKELETON-STABLE
CP-E02A-CAPABILITY-REGISTRY-SKELETON-STABLE
CP-E02B-CAPABILITY-REGISTRY-VALIDATOR-STABLE
CP-E02C-OPERATOR-REGISTRY-VALIDATOR-STABLE
CP-E03A-OPERATOR-REGISTRY-SKELETON-STABLE
CP-E04A-HOOK-REGISTRY-SKELETON-STABLE
CP-E05-MCP-REGISTRY-SKELETON-STABLE
CP-E06-DYNAMIC-GOVERNANCE-STABLE
CP-E07-ENTERPRISE-RUNTIME-STATUS-ENDPOINT-STABLE
CP-HERMES-ENTERPRISE-CORE-01
CP-HERMES-ENTERPRISE-FOUNDATION-01
CP-HERMES-OPERABILITY-TUNING-01
CP-HERMES-DOCS-ASTRO-ENTERPRISE-01
```

### Knowledge Base (AnythingLLM)

```
CP-ANYTHINGLLM-ENTERPRISE-04-COMPLETE
```

## Fase actual

El runtime se encuentra en una fase consolidada tras la finalización de:

- **Hermes Enterprise Core** — SOUL, Capability Registry, Operator Registry, Hook Registry, MCP Registry, Dynamic Governance y Status Endpoint (`:8095`) completados y documentados. 185 tests PASS.
- **AnythingLLM Enterprise** — Knowledge Base completa con 1304 vectores, 7 workspaces activos, RAG E2E validation 100%. Baseline congelada en CP-ANYTHINGLLM-ENTERPRISE-04-COMPLETE.
- **Documentación Astro** — 10 páginas Hermes Enterprise publicadas. Build exitoso (275 págs, 0 errores).

El baseline observacional se apoya en 30I-D (sensor semantics). Sobre ese baseline, el runtime añadió bloques de estabilidad (37–40), gobernanza federada y capacidades enterprise.

Multi-GPU sigue pospuesto: RX7900XT permanece como inventario expected_offline. No hay scheduler Multi-GPU implementado. Las precondiciones (30H–31B) están cerradas desde CP-31B, pero el nodo RX7900XT sigue apagado y no hay plan activo de reactivación.
