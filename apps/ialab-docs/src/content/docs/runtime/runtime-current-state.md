---
title: "Runtime Current State"
summary: "Estado actual real del runtime AI-LAB: control plane, observability, backends de inferencia, enterprise layer, knowledge base y checkpoints."
order: 10
---

## Estado actual real

### Control plane

- Hostname: `ubuntu-ialab`
- IP principal: `192.168.1.30`
- Rol: `primary-control-plane`
- Hermes Enterprise status endpoint: `192.168.1.30:8095` (GET /hermes/status)
- Servicios: ailab-gateway (:8008), ailab-router (:8083), ailab-live-api (:8084), ailab-hermes-status (:8095)

### Observability

- Prometheus: `192.168.1.40:9090` — source of truth
- Grafana: `192.168.1.40:3000` — visualization layer (15 dashboards, TIER 1 + TIER 2)
- Alert rules: 19 reglas activas, todas health=ok
- Métricas: 100+ `ailab_*` covering profiles, latency, tools, memory, quality, streaming, GPU, SLO, governance, sensor fusion
- Loki: log layer
- Los sensores del runtime se alimentan de Prometheus y del API de LM Studio.

### Inference backend activo

- GPU: `RX9070`
- Host: `192.168.1.50`
- Estado: `online`
- Fuente operativa: `Prometheus GPU exporter + LM Studio API`

### Inference backend inventariado

- GPU: `RX7900XT`
- Host: `192.168.1.60`
- Estado: `expected_offline / inventory`
- No activo
- No routable
- No debe generar métricas inventadas

### Storage

- Runtime vivo: `/opt/ai-lab`
- Runtime data: `/opt/ai-lab-data`
- Modelos: `/mnt/ai-models`
- Archives históricos: `/mnt/opencode/ai-lab-archives`

## Enterprise layer (Hermes Enterprise Core)

Hermes Enterprise Core is deployed as a read-only declarative layer exposing AI-LAB's enterprise semantics via `GET /hermes/status` on port `:8095`. All components are in validation-only mode — no active enforcement, no hooks executing.

| Component | Status | Description |
|-----------|--------|-------------|
| **SOUL** | ✅ Implemented | Ontological seed: truth_model, boundaries, protocols, domains, identity, schema |
| **Capability Registry** | ✅ Implemented | Runtime capability catalog with cross-validation (24 capabilities) |
| **Operator Registry** | ✅ Implemented | 12 deep validations per operator (IDs, capabilities, MCP, protocols, execution_mode, domains, forbidden_actions) |
| **Hook Registry** | ✅ Implemented | Lifecycle hooks skeleton (all `enabled: false, mode: declarative_only`) |
| **MCP Registry** | ✅ Implemented | Declared MCP servers (prometheus, marketplace-mcp as planned, no active tools) |
| **Dynamic Governance** | ✅ Implemented | 4 modes (NORMAL/ELEVATED/DEGRADED/LOCKDOWN), 6 trigger signals, anti-flapping 30s, capability-governance matrix |
| **Status Endpoint** | ✅ Implemented | GET /hermes/status → :8095, 14 response blocks, always-on 200 |

185 tests PASS. Checkpoint: CP-HERMES-ENTERPRISE-CORE-01.

## Knowledge Base (AnythingLLM Enterprise)

AnythingLLM Enterprise provides the RAG knowledge layer for AI-LAB. All workspaces are configured with LM Studio backend (192.168.1.50:1234) and `text-embedding-multilingual-e5-small` embedder.

| Resource | Value |
|----------|-------|
| Host | 192.168.1.50:3001 |
| Active workspaces | 7 |
| Total vectors | 1304 |
| Embedder | text-embedding-multilingual-e5-small (Q8_0) |
| Document corpus | Architecture (84 canonical), Evidence reports (53), Marketplace (7), Observability+IDS (2), Runbooks+Stack (8), MCP+A2A (19) |
| RAG validation | ✅ E2E 100% |
| Baseline | Frozen at CP-ANYTHINGLLM-ENTERPRISE-04-COMPLETE |

## Qué cambió con 30I

Antes:

```text
LLM + routing + prompts
```

Después:

```text
Runtime observacional cognitivo
→ Prometheus-backed evidence
→ Sensor fusion
→ Evidence-bound reporting
→ GPU operational summaries
→ source_of_truth / freshness / confidence
```

## Checkpoints relevantes

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
CP-30H.1-UNIVERSAL-EVIDENCE-GUARD-STABLE
CP-30H.2-RUNTIME-CONTEXT-INJECTION-STABLE
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
CP-DOC-AUTOMATION-STABLE
CP-DOCS-ASTRO-ARCHITECTURE-UPDATE-01-STABLE
CP-DOCS-AILAB-MCP-INFRASTRUCTURE-UPDATE-01-STABLE
CP-MCP-OPENCODE-WINDOWS-CONNECTION-01-STABLE
CP-MCP-SEMANTIC-GATEWAY-01-STABLE
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

## Límite explícito

Este estado es **pre-Multi-GPU**. RX7900XT sigue siendo inventario. No hay scheduler Multi-GPU documentado como implementado. Aunque las precondiciones semánticas (30H–31B) están cerradas desde CP-31B, el nodo RX7900XT permanece apagado y no hay plan activo de reactivación.
