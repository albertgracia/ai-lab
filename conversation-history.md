# AI-LAB Conversation History — Historical Timeline

**Current state:** HEAD `cde3d64` · 117 git tags · latest tag: `CP-HERMES-OPERABILITY-TUNING-01`

---

## Block Overview (21 → 40)

| Block | Approx. Period | Tags | Key Milestone |
|-------|---------------|------|--------------|
| 21 | Jul 2025 | 1 | Declarative profiles, prompts, de-hardcoding |
| 22 | Jul–Aug 2025 | 1 | Tool runtime policies, bash sanitizer, confirmation gate |
| 23 | Aug 2025 | 5 | Memory architecture (3 policies, quality gate, replay) |
| 24 | Aug–Sep 2025 | 1 | Cognitive traceability + audit log |
| 25 | Sep 2025 | 1 | OpenCode production profile |
| 26 | Sep–Oct 2025 | 5 | OpenWebUI production, observability v2, UX quality |
| 27 | Oct–Nov 2025 | 1 | Runtime stabilization baseline |
| 28 | Nov–Dec 2025 | 6 | Governed agentic runtime skeleton (planner, executor, sandbox, GC) |
| 29 | Dec 2025–Jan 2026 | 7+ | Gateway hardening, real streaming, SLO enforcement |
| 30 | Jan–Feb 2026 | 20+ | Runtime state → model awareness → degraded mode → topology → governance → evidence → sensor fusion → grounding |
| OBS-31 | Feb–Mar 2026 | 7+ | Observability source-of-truth audit, Prometheus/Grafana/Loki alignment |
| 32 | Mar 2026 | 3 | Grafana semantic cleanup, UI alignment validator |
| 33 | Mar–Apr 2026 | 2 | Governance registry, pre-pilot validation framework |
| 34 | Apr 2026 | 3 | Operational hardening, live observability diagnostics, performance calibration |
| 35 | Apr–May 2026 | 5 | Infrastructure identity registry, semantic sterilization, authority-backed cognition, operational fast-path |
| 36 | May 2026 | 6 | Incident intelligence, codebase memory, GitNexus docs, precision mode |
| 37 | May–Jun 2026 | 9 | Cognitive health layer, graph-runtime correlation, critical path analysis, governance drift |
| 38 | Jun 2026 | 4 | Runtime deep audit, graceful shutdown, GitNexus error triage, stability snapshot |
| 39 | Jun 2026 | 4 | OpenCode contract hardening, observability alerts, stabilization release close |
| 40 | Jul 2026 | 1 | Post-release SLO drift watch |
| (41) | Jul 2026 | 1 | SLO enforcement read-only, Multi-GPU readiness assessment |

---

## Blocks 37–40 (Detailed)

### Block 37 — Cognitive Health & Graph Correlation
- **CP-37A-COGNITIVE-HEALTH-LAYER-STABLE** — First cognitive health layer. Three sub-planes (anomaly, governance, stability) with Prometheus-backed always-on endpoints.
- **CP-37B-GRAPH-RUNTIME-CORRELATION-STABLE** — Maps runtime events to GitNexus knowledge graph for structural root-cause analysis.
- **CP-NEXUS-AI-PROMPT-HARDENING** — System prompt hardening for Nexus AI MCP gateway. Prevents prompt injection in tool descriptions.
- **CP-ROUTER-NO-USABLE-CHOICES-FIX** — Router crash fix when LM Studio returns zero usable models. Falls back to trusted model set.
- **CP-37C-CRITICAL-PATH-ANALYSIS (fix01)** — Critical path discovery via GitNexus graph. Identifies most-traversed execution flows for targeted optimization.
- **CP-37D-GRAPH-HOTSPOT-HISTORY-STABLE** — Historical hotspot persistence. Stores GraphHotspot snapshots for trend analysis.
- **CP-37E-GOVERNANCE-DRIFT-DETECTION** — Prometheus alert rules for governance state transitions. Detects drift before it becomes incident.
- **CP-ROUTER-HF-MODEL-POLICY** — Model routing policy hardening with fallback chains and policy-aware selection.

### Block 38 — Deep Audit & Stability Snapshot
- **CP-38A-RUNTIME-DEEP-AUDIT** — Comprehensive audit of startup sequence, initialization order, error handling gaps across all runtime components.
- **CP-38B-GATEWAY-SHUTDOWN-GRACEFUL** — Gateway graceful shutdown with drain logic, inflight request completion, metric flush before exit.
- **CP-38C-GITNEXUS-NAPI-ERROR-TRIAGE** — Structured error classification pipeline for GitNexus MCP integration errors (NAPI layer).
- **CP-38D-RUNTIME-STABILITY-SNAPSHOT** — Codifies all stability invariants into testable assertions. Snapshot-driven regression prevention.

### Block 39 — Release Stabilization
- **CP-39A-OPENCODE-GATEWAY-CONTRACT-HARDENING** — OpenCode→Gateway contract hardening. Validates prompt/response shape, enforces protocol invariants.
- **CP-39B-RUNTIME-OBSERVABILITY-ALERTS** — Prometheus alert rules consolidation. Removes dead signals, adds actionable thresholds.
- **CP-39C-COGNITIVE-HEALTH-FOLLOWUP** — Closes gaps from 37A (degraded mode coverage, anomaly correlation).
- **CP-39E-RUNTIME-STABILIZATION-RELEASE-CLOSE** — Final burn-in, documentation sync, tag cleanup. Release gate closure.

### Block 40 — Post-Release Watch
- **CP-40A-POST-RELEASE-SLO-DRIFT-WATCH** — Post-release SLO monitoring across all dimensions. Drift detection with automated notification.

### Post-40 Phases (SMB Workspace — E:\opencode\ai-lab)
- **CP-SLO-ENFORCEMENT-01** — SLO enforcement read-only layer. `collect_slo_snapshot()`, `evaluate_slos()`, `build_slo_report()`. 13 SLOs covering gateway, router, runtime, GPU, observability, governance. `GET /api/slo/status` + `GET /api/slo/report`. 26/26 tests PASS. 117/117 global.
- **CP-VALIDATION-AUTHORITY-01** — Validation authority read-only. `build_validation_decision()` in `runtime/governance/validation_authority.py`. Evidence assessment, rollback, approval levels. 57/57 tests PASS.
- **CP-AUTONOMOUS-OBSERVABILITY-TRIAGE-01** — Autonomous observability triage. `collect_prometheus_snapshot()` + `build_observability_triage_report()`. `GET /api/observability/triage`. 34/34 tests PASS.
- **CP-OPERATOR-INTENT-REASONING-01** — Operator intent reasoning. `analyze_operator_intent()` with risk/approval/target/action. `GET /api/operator/intent`. 25/25 tests PASS.
- **CP-MULTIGPU-READINESS-01** — Readiness assessment for Multi-GPU scheduling. 10-phase read-only analysis. Score: 37/100. No runtime changes.
- **CP-INTELLIGENT-FALLBACK-ENGINE-01** — Deterministic fallback on node failure. `runtime/router/fallback_engine.py`. 10 failure types, capability-safe selection. 26/26 tests. Gateway integration in error paths. No Prometheus metrics (observability via route history).
- **CP-CAPABILITY-SCHEDULER-01** — Deterministic capability-based node selection. `runtime/router/capability_scheduler.py`. Vision/large-context/rx7900xt-only routing. 37/37 tests. Runs before DNR; skip for normal chat/coding. Live-validated: moondream2→.60, qwen3.6-35b→.60, qwen2.5-14b→.50. Fallback path reason_codes aligned.
- **CP-HERMES-OPERABILITY-TUNING-01** — Hermes configured as AI-LAB operator console. Gateway endpoint, correct model, operator diagnostics, .hermes/AGENTS.md, operability guide. Findings: streaming empty stream (pre-existing), base_url override issue, AGENTS.md truncation.

### Auxiliary Tags (Blocks 37–40 scope)
- `AI-LAB_BLOCK37_STABLE_01` · `CP-GATEWAY-SHUTDOWN-GRACEFUL` · `CP-RUNTIME-STABILITY-SNAPSHOT`
- `CP-GITNEXUS-GOVERNED-CHANGE-POLICY` · `CP-QDRANT-MEMORY-GOVERNANCE-POLICY`
- `CP-MEMORY-INJECTION-TELEMETRY` · `CP-MEMORY-INJECTION-QDRANT-PERSISTENCE-FIX`
- `CP-INCIDENTS-WATCHDOG-DEDUP` · `CP-INCIDENTS-GOVERNANCE-SCHEMA`
- `CP-MCP-SEMANTIC-GATEWAY` · `CP-MCP-OPENCODE-WINDOWS-CONNECTION`
- `CP-DOCS-AILAB-MCP-INFRASTRUCTURE-UPDATE` · `CP-DOCS-ASTRO-ARCHITECTURE-UPDATE`
- `CP-DOC-AUTOMATION-STABLE`

---

## Blocks 21–36 (Compact)

### Block 21 — Profiles & Prompts
- `CP-21B-STABLE` — Declarative prompts (`runtime/prompts/`), cognitive profiles (`runtime/profiles/`), 26 hardcodes eliminated

### Block 22 — Tool Policies
- `CP-22B-STABLE` — Tool runtime policies (3 modes), bash sanitizer, confirmation gate 428, greeting classifier fix

### Block 23 — Memory Architecture
- `CP-23A-FOUNDATION` — Memory architecture foundation (3 policies: minimal/light/full)
- `CP-23A-MEMORY-SAFE` — Safety guards, contamination prevention
- `CP-23A-MODEL-ALIAS-FIX` — Model alias resolution fix
- `CP-23B-QUALITY-GATE` — Quality gate with hallucination risk scoring
- `CP-23B-RECALL-STABILITY` — Recall stability, 8 skip reasons, replay inspector

### Block 24 — Traceability
- `CP-24-ANALYTICS` — Cognitive traceability, audit log, Prometheus counters for each cognitive step

### Block 25 — OpenCode Profile
- `CP-25-OPENCODE-PRODUCTION` — Production-tuned cognitive profile for OpenCode

### Block 26 — OpenWebUI & UX
- `CP-26-OPENWEBUI-PRODUCTION` — OpenWebUI production profile
- `CP-26.1-OBSERVABILITY-v2` — Observability upgrade with Prometheus integration
- `CP-26.1.1` — Completion finalization fix
- `CP-26.1.2` — Report routing (heavy/light) fix
- `CP-26.2-UX-COGNITIVE-QUALITY` — UX quality improvements, cognitive response formatting

### Block 27 — Stabilization
- `CP-27-RUNTIME-STABILIZATION` — Runtime stabilization baseline, burn-in 306/306 OK

### Block 28 — Agentic Runtime
- `CP-28.1-PLANNER` — Planner runtime skeleton with simulation-only mode
- `CP-28.2-READONLY-EXECUTOR` — Readonly executor runtime (safe operations)
- `CP-28.2-B-BURNIN` — Burn-in validation 74/74 tests
- `CP-28.3-SANDBOX-WRITE` — Sandbox write runtime (controlled mutations)
- `CP-28.3-B-BURNIN` — Burn-in with rollback validation
- `CP-28.4-TOOL-CONTRACTS-CROSSPLAN-GC` — Tool contracts, plan registry, cross-plan graph, GC dry-run governance

### Block 29 — Gateway & SLO
- `CP-29.4.2-REPORT-PRESENTATION` — Report presentation formatting fix
- `CP-29.4.3-RUNTIME-IDENTITY-GROUNDING` — Runtime identity grounding for reports
- `CP-29.4.4-ERROR-TAXONOMY` — Error taxonomy + failure attribution (147/148 tests)
- `CP-29.4.4-B` — Error taxonomy burn-in
- `CP-29.4.4-C` — SLO health endpoint always-on 200
- `CP-29.4.4-D` — Parallel tool call hardening
- *(Pre-29.4.2: gateway hardening, real streaming, three-model runtime, SLO baseline enforcement)*

### Block 30 — Runtime State & Maturity (20+ tags)
- `CP-30A` → `CP-30I-G` — Progressive buildout: runtime state descriptors → model awareness (active/loaded/discoverable) → single-node degraded mode → topology roles & failure domains → governance visibility → cognitive route semantics → operational reporting → evidence enforcement → universal evidence guard → context injection → sensor fusion → sensor summary → semantics normalization → operational response formatting → cognitive compression → model routing cleanup → deterministic runtime grounding

### Block OBS-31 — Observability Audit
- `CP-OBS-31A` → `.5` — Source-of-truth audit: Prometheus authority, Grafana drift, runtime alignment, remediation plan, quick wins execution
- `CP-31B` — Runtime semantic maturity + degraded mode governance
- `CP-31C` — Operational reporting discipline
- `CP-31E` — Active vs inventory vs discoverable separation (46 tests)
- `CP-31D` — Runtime topology awareness (7 dataclasses, 14 nodes, 27 tests)

### Block 32 — UI & Grafana Alignment
- `CP-32A-RUNTIME-UI-ALIGNMENT` — UI alignment validator, 5 endpoints, 5 metrics, score 85.0
- `CP-32A-VALIDATOR-REFINEMENT` — Validator refinement, RX9070XT→RX9070 correction
- `CP-32B-GRAFANA-SEMANTIC-CLEANUP` — Grafana semantic cleanup, 20 tests, score 93.9

### Block 33 — Registry & Validation
- `CP-33A-RUNTIME-GOVERNANCE-REGISTRY` — Governance registry (15 domains, 7 endpoints), score 95.8
- `CP-33B-RUNTIME-PRE-PILOT-VALIDATION` — Pre-pilot validation framework (10 invariants, 7 safety gates, 25 tests)

### Block 34 — Hardening
- `CP-34A-OPERATIONAL-HARDENING` — Operational hardening for production traffic patterns
- `CP-OBS-34B-LIVE-OBSERVABILITY-DIAGNOSTICS` — Live observability diagnostics integration
- `CP-34C-PERFORMANCE-GOVERNANCE-CALIBRATION` — Performance governance calibration with SLO tuning

### Block 35 — Identity & Fast-Path
- `CP-35A-INFRASTRUCTURE-IDENTITY-REGISTRY` — Infrastructure identity registry for nodes/services
- `CP-35B-SEMANTIC-STERILIZATION` — Semantic sterilization (eliminates `NO DISPONIBLE` leakage)
- `CP-35C-LIVE-AUTHORITY-BACKED-COGNITION` — Authority-backed cognition (always-on 200, source-tagged payloads)
- `CP-35D-OPERATIONAL-FAST-PATH` — Operational fast-path routing for operational queries
- `CP-35D-HF1` — FastPath routing priority fix (deep exclusion keywords, 28 tests)

### Block 36 — Intelligence & Precision
- `CP-36A-OPERATIONAL-INCIDENT-INTELLIGENCE` — Incident intelligence (watchdog, dedup, governance schema)
- `CP-DEV-36X-CODEBASE-MEMORY` — Codebase memory integration (GitNexus graph grounding)
- `CP-DOC-36X-GITNEXUS-STRUCTURAL-COGNITION` — GitNexus documentation (15 files, 208 pages)
- `CP-DOC-36X-SPANISH-LOCALIZATION` — Spanish localization of all DOC-36X content
- `CP-36B-RUNTIME-PRECISION-MODE` — Precision mode (evidence classification, conflict/partial handling, 8 Prometheus metrics, 25 tests)

### Post-36B / Inter-Block Tags
- `CP-INFRA-HF` · `CP-ARCH-HF` — Infrastructure and architecture hotfixes
- `CP-MODEL-REGISTRY-CANONICAL` — Canonical model registry with roles, aliases, contracts
- `CP-COGNITIVE-RUNTIME-DASHBOARD` — Cognitive runtime dashboard (evidence, registry, LM Studio health)
- `CP-RUNTIME-RESILIENCE-BURNIN` — Runtime resilience burn-in suite (15–60 min, 3 workers, 5 checkpoints)
- `CP-FEDERATION-STORM` — Federation storm simulation burn-in
- `CP-COGNITIVE-SLO` — Cognitive SLO framework (7+ metrics, `/runtime/slo/*` endpoints)
- `CP-ARCHITECTURE-GOVERNANCE` — Architecture governance (AST import parsing, 6 policies, 40 tests)
- `CP-PROMETHEUS-ALERTING` — Prometheus alert rule overhaul
- `CP-36D-AUTONOMOUS-OBSERVABILITY-TRIAGE` — Initial autonomous triage pipeline
- `CP-GITNEXUS-GRAPH-AWARE-REASONING` — Graph-aware reasoning integration
- `CP-ASTRO-COGNITIVE-REALIGNMENT` — Astro documentation realignment with runtime state

---

## Future Phases (Planned)

| Phase | Scope |
|-------|-------|
| **Hermes Integration** | ✅ Complete — Gateway model mapping fix, rate limit, context resolution, fastpath narrowed |
| **Hermes BLOCKERS-01A-CONTEXT** | ✅ Closed — n_ctx=32768 was adequate, false alarm |
| **Hermes BLOCKERS-01B-FASTPATH** | ✅ PASS — removed bare "what is"/"who is" from infrastructure intents |
| **Operator Intent Reasoning** | ✅ PASS — FASE 36C, `GET /api/operator/intent`, risk/approval/target/action |
| **Autonomous Observability Triage** | ✅ PASS — FASE 36D, `GET /api/observability/triage`, Prometheus snapshot + runtime triage |
| **Validation Authority** | ✅ PASS — `GET /api/validation/authority`, evidence-based decision engine on top of OI + triage |
| **SLO Enforcement** | ✅ PASS — `GET /api/slo/status` + `GET /api/slo/report`, 13 SLOs, 26/26 tests |
| **Multi-GPU Readiness** | ✅ PASS — Readiness score 37/100, scheduler contract, 10-phase read-only assessment |
| **Validation Authority Recovery (37B)** | Restore Prometheus scrape targets, authority chain repair |
| **Multi-GPU Scheduling** | Cross-GPU load balancing (requires .60 node reactivation + pre-requisites: 7-10d) |
| **Marketplace Integration** | Model marketplace for community-contributed cognitive profiles |
| **AnythingLLM** | AnythingLLM RAG integration with AI-LAB runtime context |
| **Cloudflare Workers AI** | Edge inference via Cloudflare Workers AI for lightweight tasks |

---

> **Full phase details:** `git log --oneline --decorate` and individual tag messages.
> **Runtime reference:** `AGENTS.md` (current operational truth, service topology, metrics).
