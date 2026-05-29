---
title: "Roadmap"
summary: "Roadmap realista stabilization-first: authority + precision + governance + burn-in + memory maturity antes de reactivar Multi-GPU."
order: 8
---



## Known issues operativos

| Issue | Estado |
|-------|--------|
| Live API bind en 0.0.0.0 | Pendiente de refactor Traefik (LIVE-API-BIND-LOCALHOST-HARDENING-02) |
| /api/history endpoint 404 | No implementado en live_api.py |
| openai_gateway.py monolito | ~5700 lineas, risk HIGH, pendiente de auditoria |
| LM Studio apagado | Voluntario; 502 en chat es esperado |
| Router/LM Studio diagnosis | Pendiente cuando LM Studio este online |
| Stash antiguo pre-sync-mcp | Pendiente de revision/limpieza |

## Estado actual (real)

AI-LAB está en modo **stabilization-first** y **governance-first** tras:

- ARCH-STABILIZATION-PASS-01
- 36A (incident intelligence)
- DEV-36X / DOC-36X (GitNexus structural cognition)
- 36B (precision semantics)
- OBS-HF-LMSTUDIO-OPERATIONAL-TRUTH
- WORKTREE-GOVERNANCE-CLEANUP
- 36C (operator intent reasoning)

### Completado (21 fases desde 30I-D)

| FASE | Estado |
|------|--------|
| 30I-D — Sensor Semantics Normalization | ✅ |
| 30I-E — Operational Response Formatting | ✅ |
| 30I-F — Runtime Cognitive Compression | ✅ |
| 30I-F0 — Runtime Model Routing Cleanup | ✅ |
| 30I-G — Deterministic Runtime Grounding | ✅ |
| OBS-31A — Observability Source-of-Truth Audit | ✅ |
| OBS-31A.1 — Prometheus Authority Audit | ✅ |
| OBS-31A.2 — Grafana Drift Audit | ✅ |
| OBS-31A.3 — Runtime-Observability Alignment | ✅ |
| OBS-31A.4 — Observability Remediation Plan | ✅ |
| OBS-31A.5 — Safe Quick Wins Execution | ✅ |
| 31B — Runtime Semantic Maturity | ✅ |
| 31C — Operational Reporting Discipline | ✅ |
| 31E — Active/Inventory/Discoverable Separation | ✅ |
| 31D — Runtime Topology Awareness | ✅ |
| 32A — Runtime UI Alignment | ✅ |
| 32B — Grafana Semantic Cleanup | ✅ |
| 33A — Runtime Governance Registry | ✅ |
| 33B — Runtime Pre-Pilot Validation Framework | ✅ |
| 28.4 — Tool Contracts & Cross-Plan GC | ✅ |

## Próximas prioridades

1. Semantic stabilization (contratos y semántica operativa consistente)
2. Authority hardening (freshness/gaps/confidence por dominio)
3. Precision semantics (degradación segura, conflict handling)
4. Burn-in operacional y cognitivo (no solo tests)
5. Memory maturity (Qdrant governance, recall ROI, contaminación)
6. Distributed cognition (topología + dominios + authority chain)

## Roadmap futuro

- Pilot técnico
- Pilot operador
- Multi-GPU federation (futuro)

## Roadmap futuro oficial (37A+)

- `37A` — GRAPH-RUNTIME-CORRELATION-01
- `37B` — CRITICAL-PATH-ANALYSIS-01
- `37C` — GRAPH-HOTSPOT-HISTORY-01
- `37D` — GOVERNANCE-DRIFT-DETECTION-01
- `37E` — GRAPH-AWARE-INCIDENT-REASONING-01
- `38A` — NEXUS-AI-RUNTIME-OPERATOR-01
- `38B` — COGNITIVE-MEMORY-LAYER-01
- `38C` — TOPOLOGY-AWARE-PROMPTING-01
- `39A` — FEDERATION-INTELLIGENCE-01
- `39B` — RUNTIME-DIGITAL-TWIN-01
- `40` — AI-LAB COGNITIVE CONTROL PLANE

### Multi-GPU
No documentado como funcionalidad operativa cerrada. Pendiente de:
- Runtime maturity estable
- Governance semantics cerradas
- Scheduler contracts definidos
- RX7900XT recovery (actualmente inventory/expected_offline)
