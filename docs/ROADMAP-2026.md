# AI-LAB Roadmap 2026

**Current checkpoint:** `CP-40A-POST-RELEASE-SLO-DRIFT-WATCH-01-STABLE`
**HEAD:** `0f5e3ab8`

---

## Legacy — Phase 1–12

Pre-CP naming era. Foundation, GPU telemetry, grounded OpenCode runtime, router, cognitive agent, intent routing, distributed cognition, cognitive observability, supervised self-optimization.

| # | Tag |
|---|-----|
| 1 | `phase-1-stable` |
| 2 | `phase-2-gpu-telemetry` |
| 3 | `phase-2-stable` |
| 4 | `phase-3-grounded-opencode-runtime` |
| 5 | `phase-4-opencode-router-live` |
| 6 | `phase-5-cognitive-agent-router` |
| 7 | `phase-6-weighted-intent-routing` |
| 8 | `phase-6-distributed-cognition-v1` |
| 9 | `phase8-cognitive-observability-stable` |
| 10 | `phase12-supervised-self-optimization` |

**10 tags** — Foundation phase: first GPU metrics, OpenCode integration, router, agent layer, self-optimization loop.

---

## Block 21 — Profile Architecture

Declarative cognitive profiles (`runtime/profiles/`), de-hardcoding of runtime parameters, observability of profile selection.

| # | Tag |
|---|-----|
| 1 | `CP-21B-STABLE` |

**1 tag** — From hardcoded gateway to profile-driven behavior.

---

## Block 22 — Tool Policies & Safety

Tool runtime policies (3 modes), bash sanitizer, confirmation gate, greeting classifier fix.

| # | Tag |
|---|-----|
| 1 | `CP-22B-STABLE` |

**1 tag** — Tool governance with safety gates.

---

## Block 23 — Memory Architecture

Three memory policies (minimal/light/full), quality gate, contamination guard, recall stability.

| # | Tag |
|---|-----|
| 1 | `CP-23A-FOUNDATION` |
| 2 | `CP-23A-MEMORY-SAFE` |
| 3 | `CP-23A-MODEL-ALIAS-FIX` |
| 4 | `CP-23B-QUALITY-GATE` |
| 5 | `CP-23B-RECALL-STABILITY` |

**5 tags** — Memory subsystem with quality gates and recall stability.

---

## Block 24 — Cognitive Analytics

Cognitive traceability, audit log, telemetry pipeline.

| # | Tag |
|---|-----|
| 1 | `CP-24-ANALYTICS` |

**1 tag** — First cognitive analytics layer.

---

## Block 25 — OpenCode Production

Production-grade profile for OpenCode integration.

| # | Tag |
|---|-----|
| 1 | `CP-25-OPENCODE-PRODUCTION` |

**1 tag** — OpenCode production readiness.

---

## Block 26 — OpenWebUI Production & UX

OpenWebUI production profile, burn-in (280 reqs, 83% success), completion finalization fix, report routing fix, UX and cognitive quality improvements.

| # | Tag |
|---|-----|
| 1 | `CP-26-OPENWEBUI-PRODUCTION` |
| 2 | `CP-26.1-OBSERVABILITY-v2` |
| 3 | `CP-26.1.1-COMPLETION-FINALIZATION-FIX` |
| 4 | `CP-26.1.2-REPORT-ROUTING-FIX` |
| 5 | `CP-26.2-UX-COGNITIVE-QUALITY` |

**5 tags** — Production profiles validated with burn-in.

---

## Block 27 — Runtime Stabilization

Runtime stabilization, baseline observability burn-in.

| # | Tag |
|---|-----|
| 1 | `CP-27-RUNTIME-STABILIZATION` |

**1 tag** — Stabilization milestone.

---

## Block 28 — Governed Agentic Runtime

Planner runtime skeleton, read-only executor, sandbox write runtime, burn-in validation, tool contracts and cross-plan GC.

| # | Tag |
|---|-----|
| 1 | `CP-28.1-PLANNER-RUNTIME-SKELETON-STABLE` |
| 2 | `CP-28.2-READONLY-EXECUTOR-STABLE` |
| 3 | `CP-28.2-B-READONLY-BURNIN-STABLE` |
| 4 | `CP-28.3-SANDBOX-WRITE-STABLE` |
| 5 | `CP-28.3-B-SANDBOX-WRITE-BURNIN-STABLE` |
| 6 | `CP-28.4-TOOL-CONTRACTS-CROSSPLAN-GC-STABLE` |

**6 tags** — Planner + executor + sandbox with GC.

---

## Block 29 — SLO Enforcement & Streaming

Report presentation fix, runtime identity grounding, error taxonomy, SLO health endpoint, parallel tool call hardening, burn-in validation.

| # | Tag |
|---|-----|
| 1 | `CP-29.4.2-REPORT-PRESENTATION-STABLE` |
| 2 | `CP-29.4.3-RUNTIME-IDENTITY-GROUNDING-STABLE` |
| 3 | `CP-29.4.4-ERROR-TAXONOMY-STABLE` |
| 4 | `CP-29.4.4-B-ERROR-TAXONOMY-BURNIN-STABLE` |
| 5 | `CP-29.4.4-C-SLO-HEALTH-ENDPOINT-STABLE` |
| 6 | `CP-29.4.4-D-PARALLEL-TOOLCALL-HARDENING-STABLE` |

**6 tags** — SLO enforcement, error taxonomy, streaming reliability.

---

## Block 30 — Runtime Maturity

Runtime state foundation, model state awareness (active/loaded/discoverable), completion metadata, degraded mode, topology failure domains, governance visibility, route semantics, operational reporting, evidence enforcement, sensor fusion, cognitive compression, deterministic runtime grounding, storage hardening.

| # | Tag |
|---|-----|
| 1 | `CP-30A-RUNTIME-STATE-FOUNDATION-STABLE` |
| 2 | `CP-30B-MODEL-STATE-AWARE-STABLE` |
| 3 | `CP-30B.1-COMPLETION-METADATA-STABLE` |
| 4 | `CP-30C-DEGRADED-MODE-EXPLICIT-STABLE` |
| 5 | `CP-30D-TOPOLOGY-FAILURE-DOMAIN-STABLE` |
| 6 | `CP-30E-GOVERNANCE-VISIBILITY-STABLE` |
| 7 | `CP-30F-ROUTE-SEMANTICS-STABLE` |
| 8 | `CP-30G-OPERATIONAL-REPORTING-STABLE` |
| 9 | `CP-30Z-RUNTIME-MATURITY-CONSOLIDATED` |
| 10 | `CP-30H-RUNTIME-EVIDENCE-ENFORCEMENT-STABLE` |
| 11 | `CP-30H-EVIDENCE-BURNIN-STABLE` |
| 12 | `CP-DOC-30H-RUNTIME-MATURITY-DOCS-STABLE` |
| 13 | `CP-30H.1-UNIVERSAL-EVIDENCE-GUARD-STABLE` |
| 14 | `CP-30H.2-RUNTIME-CONTEXT-INJECTION-STABLE` |
| 15 | `CP-30I-RUNTIME-SENSOR-FUSION-STABLE` |
| 16 | `CP-30I-DOCS-RUNTIME-OBSERVABILITY-STABLE` |
| 17 | `CP-30I-B-SENSOR-FUSION-HARDENED-STABLE` |
| 18 | `CP-30I-C-SENSOR-SUMMARY-EXPOSURE-STABLE` |
| 19 | `CP-STORAGE-HARDENING-ARCHIVE-POLICY-STABLE` |
| 20 | `CP-30I-D-SENSOR-SEMANTICS-NORMALIZED-STABLE` |
| 21 | `CP-DOC-30I-RUNTIME-SENSOR-FUSION-DOCS-STABLE` |
| 22 | `CP-30I-E-OPERATIONAL-RESPONSE-FORMATTING-STABLE` |
| 23 | `CP-30I-F-RUNTIME-COGNITIVE-COMPRESSION-STABLE` |
| 24 | `CP-30I-F0-RUNTIME-MODEL-ROUTING-CLEANUP-STABLE` |
| 25 | `CP-30I-G-RUNTIME-GROUNDING-STABLE` |

**25 tags** — Largest block: runtime maturity, evidence, sensor fusion, grounding.

---

## Block OBS-31 — Observability Source of Truth

Prometheus authority audit, Grafana drift audit, runtime-observability alignment, remediation plan, safe quick wins, semantic maturity, OpenCode context alignment, reporting discipline, active/inventory/discoverable separation, topology awareness.

| # | Tag |
|---|-----|
| 1 | `CP-OBS-31A-OBSERVABILITY-SOURCE-OF-TRUTH-STABLE` |
| 2 | `CP-OBS-31A.1-PROMETHEUS-AUTHORITY-AUDIT-STABLE` |
| 3 | `CP-OBS-31A.2-GRAFANA-DRIFT-AUDIT-STABLE` |
| 4 | `CP-OBS-31A.3-RUNTIME-OBSERVABILITY-ALIGNMENT-STABLE` |
| 5 | `CP-OBS-31A.4-OBSERVABILITY-REMEDIATION-PLAN-STABLE` |
| 6 | `CP-OBS-31A.5-EXECUTOR-STABLE` |
| 7 | `CP-31B-RUNTIME-SEMANTIC-MATURITY-STABLE` |
| 8 | `CP-31B-HF1-OPENCODE-CONTEXT-ALIGNMENT-STABLE` |
| 9 | `CP-31C-OPERATIONAL-REPORTING-DISCIPLINE-STABLE` |
| 10 | `CP-31E-ACTIVE-INVENTORY-DISCOVERABLE-SEPARATION-STABLE` |
| 11 | `CP-31D-RUNTIME-TOPOLOGY-AWARENESS-STABLE` |

**11 tags** — Prometheus as source of truth, observability alignment, semantic maturity.

---

## Block 32 — UI & Grafana Alignment

Runtime UI alignment, validator refinement, Grafana semantic cleanup.

| # | Tag |
|---|-----|
| 1 | `CP-32A-RUNTIME-UI-ALIGNMENT-STABLE` |
| 2 | `CP-32A-VALIDATOR-REFINEMENT-STABLE` |
| 3 | `CP-32B-GRAFANA-SEMANTIC-CLEANUP-STABLE` |

**3 tags** — UI and Grafana dashboard alignment.

---

## Block 33 — Governance Registry & Pre-Pilot

Runtime governance registry, pre-pilot validation.

| # | Tag |
|---|-----|
| 1 | `CP-33A-RUNTIME-GOVERNANCE-REGISTRY-STABLE` |
| 2 | `CP-33B-RUNTIME-PRE-PILOT-VALIDATION-STABLE` |

**2 tags** — Governance registry and validation.

---

## Block 34 — Operational Hardening

Runtime operational hardening, live observability diagnostics, performance governance calibration.

| # | Tag |
|---|-----|
| 1 | `CP-34A-RUNTIME-OPERATIONAL-HARDENING-STABLE` |
| 2 | `CP-OBS-34B-LIVE-OBSERVABILITY-DIAGNOSTICS-STABLE` |
| 3 | `CP-34C-RUNTIME-PERFORMANCE-GOVERNANCE-CALIBRATION-STABLE` |

**3 tags** — Hardening and calibration.

---

## Block 35 — Identity & Fast Path

Infrastructure identity registry, semantic sterilization/identity hygiene, live authority-backed cognition, operational fast path, fastpath routing priority fix.

| # | Tag |
|---|-----|
| 1 | `CP-35A-INFRASTRUCTURE-IDENTITY-REGISTRY-STABLE` |
| 2 | `CP-35B-SEMANTIC-STERILIZATION-IDENTITY-HYGIENE-STABLE` |
| 3 | `CP-35C-LIVE-AUTHORITY-BACKED-COGNITION-STABLE` |
| 4 | `CP-35D-OPERATIONAL-FAST-PATH-STABLE` |
| 5 | `CP-35D-HF1-FASTPATH-ROUTING-PRIORITY-STABLE` |

**5 tags** — Identity, fast path, authority-backed cognition.

---

## Block 36 — Incident Intelligence & Precision

Operational incident intelligence, codebase memory integration, GitNexus structural cognition docs, Spanish localization, runtime precision mode.

| # | Tag |
|---|-----|
| 1 | `CP-36A-OPERATIONAL-INCIDENT-INTELLIGENCE-STABLE` |
| 2 | `CP-DEV-36X-CODEBASE-MEMORY-INTEGRATION-STABLE` |
| 3 | `CP-DOC-36X-GITNEXUS-STRUCTURAL-COGNITION-STABLE` |
| 4 | `CP-DOC-36X-SPANISH-LOCALIZATION-STABLE` |
| 5 | `CP-36B-RUNTIME-PRECISION-MODE-STABLE` |

**5 tags** — Incident intelligence, precision mode, GitNexus.

---

## Post-36B Infra — Cross-cutting Infrastructure

Gateway metrics consistency, init decoupling, canonical model registry, cognitive runtime dashboard, resilience burn-in, federation storm simulation, cognitive SLO, architecture governance, Prometheus alerting, autonomous observability triage, GitNexus graph-aware reasoning, Astro cognitive runtime realignment.

| # | Tag |
|---|-----|
| 1 | `CP-INFRA-HF-GATEWAY-METRICS-CONSISTENCY-STABLE` |
| 2 | `CP-ARCH-HF-INIT-DECOUPLING-STABLE` |
| 3 | `CP-MODEL-REGISTRY-CANONICAL-01-STABLE` |
| 4 | `CP-COGNITIVE-RUNTIME-DASHBOARD-01-STABLE` |
| 5 | `CP-RUNTIME-RESILIENCE-BURNIN-01-STABLE` |
| 6 | `CP-FEDERATION-STORM-SIMULATION-01-STABLE` |
| 7 | `CP-COGNITIVE-SLO-01-STABLE` |
| 8 | `CP-ARCHITECTURE-GOVERNANCE-01-STABLE` |
| 9 | `CP-PROMETHEUS-ALERTING-COGNITIVE-01-STABLE` |
| 10 | `CP-36D-AUTONOMOUS-OBSERVABILITY-TRIAGE-01-STABLE` |
| 11 | `CP-GITNEXUS-GRAPH-AWARE-REASONING-01-STABLE` |
| 12 | `CP-ASTRO-COGNITIVE-RUNTIME-REALIGNMENT-01-STABLE` |

**12 tags** — Infrastructure, federation, alerting, triage, graph reasoning.

---

## Block 37 — Cognitive Health Layer

Cognitive health layer, graph-runtime correlation, Nexus AI prompt hardening, router fix (no usable choices), critical path analysis, fix01, graph hotspot history, governance drift detection, router model policy fix.

| # | Tag |
|---|-----|
| 1 | `CP-37A-COGNITIVE-HEALTH-LAYER-01-STABLE` |
| 2 | `CP-37B-GRAPH-RUNTIME-CORRELATION-01-STABLE` |
| 3 | `CP-NEXUS-AI-ARCHITECTURE-PROMPT-HARDENING-01-STABLE` |
| 4 | `CP-ROUTER-NO-USABLE-CHOICES-FIX-01-STABLE` |
| 5 | `CP-37C-CRITICAL-PATH-ANALYSIS-01-STABLE` |
| 6 | `CP-37C-CRITICAL-PATH-ANALYSIS-01-STABLE-FIX01` |
| 7 | `CP-37D-GRAPH-HOTSPOT-HISTORY-01-STABLE` |
| 8 | `CP-37E-GOVERNANCE-DRIFT-DETECTION-01-STABLE` |
| 9 | `CP-ROUTER-HF-MODEL-POLICY-01-STABLE` |

**9 tags** — Health layer, critical path, governance drift detection.

---

## Block 38 — Deep Audit & Stability

Runtime deep audit, graceful gateway shutdown, GitNexus N-API error triage, runtime stability snapshot.

| # | Tag |
|---|-----|
| 1 | `CP-38A-RUNTIME-DEEP-AUDIT-01-STABLE` |
| 2 | `CP-38B-GATEWAY-SHUTDOWN-GRACEFUL-01-STABLE` |
| 3 | `CP-38C-GITNEXUS-NAPI-ERROR-TRIAGE-01-STABLE` |
| 4 | `CP-38D-RUNTIME-STABILITY-SNAPSHOT-01-STABLE` |

**4 tags** — Audit, graceful shutdown, stability snapshot.

---

## Block 39 — Release Hardening

OpenCode gateway contract hardening, runtime observability alerts, cognitive health followup, runtime stabilization release close.

| # | Tag |
|---|-----|
| 1 | `CP-39A-OPENCODE-GATEWAY-CONTRACT-HARDENING-01-STABLE` |
| 2 | `CP-39B-RUNTIME-OBSERVABILITY-ALERTS-01-STABLE` |
| 3 | `CP-39C-COGNITIVE-HEALTH-FOLLOWUP-01-STABLE` |
| 4 | `CP-39E-RUNTIME-STABILIZATION-RELEASE-CLOSE-01-STABLE` |

**4 tags** — Release hardening and close.

---

## Block 40 — Post-Release SLO Drift Watch

SLO drift monitoring after release.

| # | Tag |
|---|-----|
| 1 | `CP-40A-POST-RELEASE-SLO-DRIFT-WATCH-01-STABLE` |

**1 tag** — Ongoing SLO watch.

---

## Cross-cutting & Additional Tags

Additional tags not part of the numbered block sequence. Includes memory governance, incident schema, MCP semantic gateway, documentation automation.

| # | Tag |
|---|-----|
| 1 | `AI-LAB_BLOCK37_STABLE_01` |
| 2 | `CP-GITNEXUS-GOVERNED-RUNTIME-CHANGE-POLICY-01-STABLE` |
| 3 | `CP-QDRANT-MEMORY-GOVERNANCE-POLICY-01-STABLE` |
| 4 | `CP-MEMORY-INJECTION-TELEMETRY-01-STABLE` |
| 5 | `CP-MEMORY-INJECTION-QDRANT-PERSISTENCE-FIX-01-STABLE` |
| 6 | `CP-INCIDENTS-WATCHDOG-DEDUP-01-STABLE` |
| 7 | `CP-INCIDENTS-GOVERNANCE-SCHEMA-01-STABLE` |
| 8 | `CP-MCP-SEMANTIC-GATEWAY-01-STABLE` |
| 9 | `CP-MCP-OPENCODE-WINDOWS-CONNECTION-01-STABLE` |
| 10 | `CP-DOCS-AILAB-MCP-INFRASTRUCTURE-UPDATE-01-STABLE` |
| 11 | `CP-DOCS-ASTRO-ARCHITECTURE-UPDATE-01-STABLE` |
| 12 | `CP-DOC-AUTOMATION-STABLE` |

**12 tags** — Memory Qdrant, incidents schema, MCP gateway, doc automation.

> **Note:** `CP-GATEWAY-SHUTDOWN-GRACEFUL-01-STABLE` and `CP-RUNTIME-STABILITY-SNAPSHOT-01-STABLE` are aliases for `CP-38B` and `CP-38D` respectively (not duplicated here).

---

## Future Phases

| Phase | Description | Status |
|-------|-------------|--------|
| Hermes Integration | Fast inter-agent messaging bus | Planned |
| Operator Intent Reasoning | Intent classification and operator-driven decisions | Planned |
| Autonomous Observability Triage | Self-healing observability pipeline | Planned |
| Validation Authority Recovery | Restore Prometheus scrape targets, fix authority gaps | Next |
| Multi-GPU Scheduling | Scheduler for multi-GPU inference across nodes | On hold |
| Marketplace Integration | Model/agent marketplace | Planned |
| AnythingLLM | External LLM integration layer | Planned |
| Cloudflare Workers AI | Edge AI deployment | Exploratory |

---

**Total tags (all blocks):** ~145
**Checkpoint progress:** Block 40 complete — entering post-release monitoring phase.
