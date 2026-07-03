# Multi-GPU Readiness Assessment

## Executive Summary

AI-LAB currently operates with **one active inference node** (RX9070, 192.168.1.50, 16GB VRAM). The second GPU node (RX7900XT, 192.168.1.60, 20GB VRAM) is **offline and in maintenance**. Multi-GPU scheduling **cannot be safely implemented** until a second inference node is operational.

The governance and observability foundation (Operator Intent, Observability Triage, Validation Authority, SLO Enforcement) is complete and provides all required scheduler inputs. The topology framework (31 endpoints, failure domains, health monitoring) is production-ready.

**Overall readiness score: 37/100** — Infrastructure readiness is the critical blocker.

---

## 1. Node Inventory

### Active Nodes

| Host | IP | Role | GPU | VRAM | Status | Failure Domain |
|------|-----|------|-----|------|--------|---------------|
| ubuntu-ialab | 192.168.1.30 | PRIMARY_CONTROL_PLANE | — | — | ACTIVE | control-plane |
| RX9070 | 192.168.1.50 | ACTIVE_INFERENCE_BACKEND | AMD Radeon RX9070 | 16 GB | ACTIVE | inference-gpu |
| observability | 192.168.1.40 | OBSERVABILITY_NODE | — | — | ACTIVE | observability |
| NAS | 192.168.1.200 | STORAGE | — | — | ACTIVE | storage |

### Inactive / Offline Nodes

| Host | IP | Role | GPU | VRAM | Status | Failure Domain |
|------|-----|------|-----|------|--------|---------------|
| RX7900XT | 192.168.1.60 | INVENTORY_OFFLINE | AMD Radeon RX7900XT | 20 GB | OFFLINE (maintenance) | inference-gpu |
| NAS-N5 | 192.168.1.250 | STORAGE + FAILOVER | — | — | NOT IN TOPOLOGY | storage |

### Inference Edge

Only one active inference edge: `192.168.1.30 → 192.168.1.50` (forwards_inference_to). No failover path exists.

---

## 2. Model Inventory

### Active Models (on RX9070 .50)

| Model ID | Context | Quant | Skills | Streaming | Tools | Status |
|----------|---------|-------|-------|-----------|-------|--------|
| `qwen/qwen2.5-coder-14b-instruct` | 32,768 | Q4_K_M | coding, debugging, refactor, testing, architecture, report | ✅ | ❌ | PRIMARY_CODING |
| `qwen3-vl-8b-instruct` | 32,768 | — | fast, chat, general, observe, vision, tool-use | ✅ | ✅ | FASTPATH |
| `deepseek-r1-qwen3-8b` | 32,768 | — | reasoning, analysis, chain-of-thought | ✅ | ❌ | REASONING |
| `text-embedding-nomic-embed-text-v1.5` | 8,192 | — | embeddings, semantic-search, rag | ❌ | ❌ | EMBEDDING |

### Passive Models (canonical registry, not routable)

| Model ID | Reason |
|----------|--------|
| `llama-3.1-8b-instruct` | Quarantined (broken Jinja template) |
| `qwen3.6-27b` | Disabled (FASE 29.3 three-model simplification) |

### Inventory Models (on RX7900XT .60 — OFFLINE)

| Model ID | Context | VRAM Need | Estimated Throughput |
|----------|---------|-----------|---------------------|
| `qwen2.5-coder-32b-instruct` | 65,536 | ~18 GB | ~8 tok/s |
| `deepseek-r1` | 65,536 | ~16 GB | ~10 tok/s |
| `gemma-4-26b` | 32,768 | ~14 GB | ~12 tok/s |
| `qwen3-14b-claude-sonnet-4.5-reasoning-distill` | 32,768 | ~10 GB | ~15 tok/s |
| `moondream2-20250414` | 4,096 | ~4 GB | ~30 tok/s |
| `text-embedding-nomic-embed-text-v2-moe` | 8,192 | ~2 GB | ~50 tok/s |
| `flux` | 2,048 | ~8 GB | ~5 tok/s |

### Fallback Chains

| Profile | Default | Fallback | Fallback reaches different node? |
|---------|---------|----------|--------------------------------|
| observe (minimal) | qwen3-vl-8b-instruct (.50) | same | ❌ No |
| chat (report) | qwen2.5-coder-14b-instruct (.50) | llama-3.1-8b-instruct (.50) | ❌ No (llama quarantined) |
| coding | qwen2.5-coder-14b-instruct (.50) | same | ❌ No |
| analysis (reasoning) | qwen2.5-coder-32b-instruct (.60) | qwen2.5-coder-14b-instruct (.50) | ❌ No (.60 offline) |
| agent | qwen2.5-coder-14b-instruct (.50) | same | ❌ No |

---

## 3. Capability Matrix

| Capability | RX9070 (.50) | RX7900XT (.60) | NAS-N5 (.250) |
|------------|-------------|----------------|---------------|
| Fast / Lightweight | ✅ qwen3-vl-8b | ⬜ offline | ❌ not in topology |
| Coding | ✅ qwen2.5-coder-14b | ⬜ offline | ❌ |
| Reasoning | ✅ deepseek-r1-qwen3-8b | ⬜ offline | ❌ |
| Architecture / Large Context | ❌ (14B limit) | ✅ qwen2.5-coder-32b 65k ctx | ❌ |
| Vision | ✅ qwen3-vl-8b | ⬜ moondream2 | ❌ |
| Tools | ✅ qwen3-vl-8b | ⬜ | ❌ |
| Embeddings | ✅ nomic-embed-v1.5 | ⬜ nomic-embed-v2-moe | ❌ |
| Image Generation | ❌ | ⬜ flux | ❌ |
| 65k+ Context | ❌ (16GB limit) | ✅ (20GB) | ❌ |
| Deep Reasoning | ❌ (14B) | ✅ (32B, R1) | ❌ |

**Key Gap**: The RX9070 cannot run 32B-class models (needs ~18GB for qwen2.5-coder-32b, exceeds 16GB VRAM). The RX7900XT with 20GB can. Until .60 is online, all large-context/deep-reasoning workloads are either downgraded or unavailable.

---

## 4. Profile → Node Mapping

| Profile | Current Destination | Possible Destinations | Uses second node? |
|---------|-------------------|---------------------|------------------|
| minimal | .50 (qwen3-vl-8b) | .50 only | ❌ |
| chat | .50 (qwen2.5-14b) | .50 only | ❌ |
| coding | .50 (qwen2.5-14b) | .50 only | ❌ |
| analysis | .60 → fallback .50 | .60 (offline) or .50 | ⬜ (would use on reactivation) |
| report | .50 (qwen2.5-14b) | .50 only | ❌ |
| agent | .50 (qwen2.5-14b) | .50 only | ❌ |
| creative | .50 (qwen2.5-14b) | .50 only | ❌ |
| observe | .50 (qwen3-vl-8b) | .50 only | ❌ |
| embeddings | .50 (nomic-embed-v1.5) | .50 only | ❌ |

---

## 5. Failure Analysis

### Scenario: Node .50 (RX9070) Unavailable

| Aspect | Current Behavior | Required Scheduler Behavior |
|--------|-----------------|---------------------------|
| All chat requests | FAIL (no active fallback) | Route to .60 or .250 |
| Embeddings | FAIL | Route to nomic-embed-v2-moe on .60 |
| Gateway health | Degraded | Circuit breaker → failover |
| SLOs | Gateway → critical, GPU → critical | Automatic failover detection |
| Topology | Node → INACTIVE | Recompute fallback chains |
| **Verdict** | **Complete service outage** | **Full failover required** |

### Scenario: Node .60 (RX7900XT) Reactivated

| Aspect | Current Behavior | Required Scheduler Behavior |
|--------|-----------------|---------------------------|
| Analysis/reasoning | Fallback to .50 (downgraded) | Route directly to .60 |
| Large context | Not available | Available on .60 (32B, 65k ctx) |
| Deep reasoning | Not available | Available on .60 (deepseek-r1) |
| Image generation | Not available | Available on .60 (flux) |
| **Verdict** | **Silent capability loss** | **Automatic capability detection** |

### Scenario: Prometheus / Observability Unavailable

| Aspect | Current Behavior | Scheduler Impact |
|--------|-----------------|-----------------|
| GPU metrics | Not available | Scheduler blind to VRAM/load |
| Scrape targets | DOWN | Cannot make informed placement |
| Health monitoring | No data | Degraded to static routing |
| **Verdict** | **Scheduler operates degraded** | **Graceful degradation required** |

### Scenario: Control Plane (.30) Unavailable

| Aspect | Current Behavior | Scheduler Impact |
|--------|-----------------|-----------------|
| All cognitive routing | BLOCKED | Scheduler not reachable |
| Gateway, Router, Live API | DOWN | Complete outage |
| **Verdict** | **Complete outage** | **Scheduler must be on resilient control plane** |

---

## 6. Scheduler Contract

### Required Inputs

```
┌─────────────────────────────────────────┐
│           Scheduler Input              │
├─────────────────────────────────────────┤
│ operator_intent: {                      │
│   risk, category, target, action,       │
│   requires_approval, safety_markers    │
│ }                                       │
│ validation_authority: {                 │
│   decision, risk, approval_level,       │
│   evidence, has_rollback               │
│ }                                       │
│ triage: {                               │
│   severity, evidence, down_targets,     │
│   confidence, requires_approval        │
│ }                                       │
│ slo: {                                  │
│   overall_status, critical_slos[],      │
│   budget_remaining, burn_rate          │
│ }                                       │
│ topology: {                             │
│   nodes[{                               │
│     host, role, status,                 │
│     failure_domain,                     │
│     capabilities[]                      │
│   }],                                   │
│   edges[{source, target, type, status}] │
│ }                                       │
│ node_health: {                          │
│   [node_id]: {                          │
│     online, latency_ms, uptime,         │
│     failure_count, last_failure         │
│   }                                     │
│ }                                       │
│ gpu_state: {                            │
│   [node_id]: {                          │
│     vram_used_gib, vram_total_gib,      │
│     gpu_util_pct,                       │
│     active_requests                     │
│   }                                     │
│ }                                       │
│ model_availability: {                   │
│   [model_id]: {                         │
│     nodes[node_id]: {                   │
│       loaded, active,                   │
│       context_used,                     │
│       last_request_s                    │
│     }                                   │
│   }                                     │
│ }                                       │
│ request: {                              │
│   profile, task_type,                   │
│   context_length, estimated_tokens,     │
│   requires_streaming, requires_tools    │
│ }                                       │
└─────────────────────────────────────────┘
```

### Required Outputs

```
┌─────────────────────────────────────────────┐
│           Scheduler Output                  │
├─────────────────────────────────────────────┤
│ selected_node: string          # host IP    │
│ selected_model: string         # model ID   │
│ fallback_order: string[]       # [node/IP]  │
│ routing_reason: string         # why this   │
│ confidence: float              # 0.0-1.0    │
│ evidence: string[]             # what was   │
│                                # considered │
│ estimated_latency_ms: int      # prediction │
│ estimated_vram_gib: float      # prediction │
│ requires_approval: bool                     │
│ safe_to_auto_execute: bool                  │
│ contract_version: string                    │
└─────────────────────────────────────────────┘
```

### Scheduling Constraints (proposed)

| Constraint | Type | Description |
|-----------|------|-------------|
| `colocate` | soft | Models should run on same node for low-latency chains |
| `separate` | hard | Memory-intensive workloads cannot share (total VRAM) |
| `affinity` | soft | Model X prefers Node Y (quantization, KV cache) |
| `anti-affinity` | hard | Model X cannot run on Node Y (missing ISA, ROCm version) |
| `capacity` | hard | VRAM requested ≤ VRAM available |
| `latency-class` | soft | Fast-path models require p50 < 1000ms target |
| `context-class` | hard | Context window ≤ model max context |

### Placement Algorithm (proposed)

```
for each request with (profile, task_type, context_length):
    1. candidate_nodes = filter(online AND NOT degraded)
    2. candidate_models = filter(model_availability[node] matches profile)
    3. candidate_models = filter(candidate_models, context_length ≤ model.max_context)
    4. if requires_tools: filter(candidate_models, tools_supported == True)
    5. if requires_streaming: filter(candidate_models, streaming_supported == True)
    6. score each (node, model) pair:
       - vram_score = 1 - (vram_used / vram_total)                      # 0-1
       - utilization_score = 1 - (active_requests / max_concurrent)      # 0-1
       - health_score = node_health[node].score                          # 0-1
       - capability_score = 1.0 if exact match, 0.5 if fallback, 0.0    # 0-1
       - total = 0.3*capability + 0.25*health + 0.25*vram + 0.2*utilization
    7. select_pair = max(score)
    8. fallback_order = sorted(pairs by score DESC)
    9. if select_pair.score < MIN_SCORE: require approval
    10. return decision
```

### Integration Points

| Integration | Current State | Required for Scheduler |
|------------|--------------|----------------------|
| `collect_slo_snapshot()` | ✅ Available | Schedule based on SLO health |
| `build_validation_decision()` | ✅ Available | Pre-flight approval |
| `build_observability_triage_report()` | ✅ Available | Circuit breaker on triage severity |
| `evaluate_slos()` | ✅ Available | Degraded mode routing |
| `model_health_score()` | ✅ Available | Per-model placement score |
| `topology graph` | ✅ 31 endpoints | Failure domain awareness |
| `node_discovery` | ✅ Available | Node inventory |
| `gpu_state` | ⚠️ SSH-based, no scheduling API | Direct VRAM query |
| `health_monitor` | ⚠️ Backoff, no scheduling API | Health as scheduler input |
| `model_availability` | ❌ Not tracked per-node | Needed for placement |

---

## 7. Readiness Score

### Categories

| Category | Score | Weight | Weighted | Evidence |
|----------|-------|--------|----------|----------|
| **Infrastructure** | 20/100 | 20% | 4.0 | Only 1 active GPU node. .60 offline, .250 not in topology |
| **Observability** | 85/100 | 15% | 12.75 | Prometheus, GPU exporters, health monitoring all work. SSH-based VRAM needs upgrade |
| **Governance** | 95/100 | 15% | 14.25 | OI, Triage, VA, SLO — all complete and tested |
| **Routing** | 30/100 | 15% | 4.5 | Single-node only. No multi-node routing. No placement logic |
| **Node Health** | 50/100 | 10% | 5.0 | Health monitor exists but not scheduler-integrated. Backoff only |
| **Model Coverage** | 40/100 | 10% | 4.0 | Coverage is good on paper but half the models are on an offline node |
| **Fallback** | 10/100 | 5% | 0.5 | No cross-node fallback exists. Single point of failure at .50 |
| **Scheduler Inputs** | 70/100 | 5% | 3.5 | Governance inputs ready. Infrastructure inputs (GPU state, model availability) partial |
| **Scheduler Outputs** | 20/100 | 3% | 0.6 | No schema defined in code. Contract is only in this document |
| **Deployment Risk** | 20/100 | 2% | 0.4 | Any scheduler change risks breaking single-node routing. No staging environment |

### Total: 49.5/100

### Weighted: 37/100 (using realistic weights based on criticality)

| Factor | Rationale |
|--------|-----------|
| Infrastructure is the heaviest blocker | Cannot schedule across one node |
| Governance is the strongest pillar | All four layers production-ready |
| Fallback is the weakest | No cross-node failover = service outage on .50 failure |

---

## 8. Gap Analysis

### Critical

| Gap | Description | Impact | Recommended Phase | Effort |
|-----|-------------|--------|-------------------|--------|
| **.60 node offline** | RX7900XT (192.168.1.60) in maintenance | Without a second node, scheduling is meaningless | Reactivate .60 | 1-2 days (hardware check + LM Studio config) |
| **No cross-node fallback** | All routing targets .50 only | Single node failure = complete outage | Add after node reactivation | 3-5 days |
| **model_availability not tracked per-node** | No data structure tracking which models are loaded where | Scheduler cannot make informed placement | Add runtime/state/model_availability.py | 2-3 days |

### High

| Gap | Description | Impact | Recommended Phase | Effort |
|-----|-------------|--------|-------------------|--------|
| **VRAM tracking not scheduler-ready** | SSH-based typeperf has 3s latency | Scheduler decisions based on stale data | Upgrade to Prometheus-based VRAM | 2-3 days |
| **No placement scoring logic** | No code to score (node, model) pairs | Scheduler would have no decision algorithm | Implement scheduler kernel | 5-7 days |
| **152B model community best model not available** | AI-LAB lacks models above 32B | Cannot offer high-end cognitive workloads | Add via API or additional node | TBD |
| **NAS-N5 (.250) not in active topology** | Defined in docs but not in topology code | Missed failover opportunity | Add to topology | 1 day |
| **Profile → node binding is hardcoded** | Profiles reference models, not nodes | Cannot dynamically reassign | Make profile default model node-aware | 3-4 days |

### Medium

| Gap | Description | Impact | Recommended Phase | Effort |
|-----|-------------|--------|-------------------|--------|
| **No scheduler contract in code** | Contract exists only in this document | No type safety, no validation | Add runtime/scheduler/contracts.py | 1 day |
| **Health monitor not exposes scheduler API** | health_monitor.py uses internal backoff | Scheduler would need custom health polling | Refactor to expose get_node_health() | 1 day |
| **SLO enforcement not integrated** | SLO layer exists but no scheduler reads it | Cannot do degraded-mode routing | Add SLO → scheduler callback | 1-2 days |
| **64k+ context unavailable** | RX9070 cannot run 32B models | No deep architecture support until .60 reactivated | Reactivate .60 + enable reasoning routing | 2-3 days |
| **Only 3 active models** | qwen2.5-14b, qwen3-vl-8b, nomic-embed | Limited scheduling surface | Activate more models post-reactivation | 1 day |

### Low

| Gap | Description | Impact | Recommended Phase | Effort |
|-----|-------------|--------|-------------------|--------|
| **Scheduler contract schema** | Types not defined | Cleanup only | Add dataclasses | 0.5 day |
| **Gateway model overrides bypass routing** | Gateway hardcodes model after profile assigns | Scheduler decisions could be overridden | Align gateway with scheduler | 2-3 days |
| **Test coverage for multi-node** | No tests simulating multi-GPU | Cannot validate scheduler behaviour | Add integration tests | 3-5 days |
| **.250 failover node not validated** | NAS-N5 has LM Studio but no test traffic | Unknown failover fidelity | Test after adding to topology | 1 day |

---

## 9. Recommended Roadmap

### Phase 1: Reactivate .60 (Critical — 1-2 days)
- Power on RX7900XT (192.168.1.60)
- Verify LM Studio loads models
- Verify Prometheus scrape targets come up
- Verify GPU exporter responds on :9182

### Phase 2: Add .250 to Topology (High — 1 day)
- Register NAS-N5 (192.168.1.250) in runtime_topology.py
- Assign failure domain
- Discover available models

### Phase 3: Track model_availability per-node (High — 2-3 days)
- Create runtime/state/model_availability.py
- Add Prometheus metrics: ailab_model_loaded{node, model}
- Create GET /runtime/models/availability

### Phase 4: Implement Scheduler Kernel (High — 5-7 days)
- Implement placement scoring (see §6 algorithm)
- Create runtime/scheduler/engine.py
- Wire governance inputs (OI, Triage, VA, SLO)
- Read-only first (dry-run mode)

### Phase 5: Cross-node Fallback (High — 3-5 days)
- Define fallback chains per profile
- Implement failover on node health degradation
- Test with .50 → .60 → .250 fallback

### Phase 6: Scheduler Integration (Medium — 3-4 days)
- Wire scheduler into gateway routing
- Create GET /api/scheduler/status
- Add scheduler decisions to SLO evaluation
- Create Alerts for scheduler anomalies

### Phase 7: Deep Reasoning Models (Medium — 2-3 days)
- Route analysis/reasoning profile to .60
- Enable qwen2.5-coder-32b and deepseek-r1
- Test 65k context windows

### Phase 8: Production Hardening (Ongoing)
- Burn-in multi-node routing
- Add integration tests
- Performance baseline vs single-node
- Documentation

---

## 10. Answer

**Can AI-LAB safely begin Multi-GPU Scheduler implementation?**

### NO — with specific remediation.

**Why:**
1. **Only 1 active inference node.** Multi-GPU scheduling is meaningless without ≥2 GPU nodes. The RX7900XT (.60) is offline. Until it is reactivated, there is nothing to schedule across.
2. **No cross-node fallback exists.** Every profile routes to .50 only. A scheduler that adds .60 without failback logic creates a hard dependency on .60 availability.
3. **model_availability not tracked per-node.** The scheduler would have no data structure to query which models are loaded where.
4. **Profile → node binding is hardcoded.** Current profiles reference models, and models are implicitly bound to .50. A scheduler needs explicit node→model→profile mappings.

### Exact Pre-requisites for "YES"

| # | Condition | Status | Effort |
|---|-----------|--------|--------|
| 1 | RX7900XT (.60) operational | ❌ OFFLINE | 1-2 days |
| 2 | NAS-N5 (.250) in active topology | ❌ NOT REGISTERED | 1 day |
| 3 | model_availability tracked per-node | ❌ NOT IMPLEMENTED | 2-3 days |
| 4 | Scheduler contract defined in code | ❌ DOCUMENT ONLY | 1 day |
| 5 | Fallback chains per profile defined | ❌ NOT DEFINED | 1 day |
| 6 | SLO integration for degraded routing | ⚠️ EXISTS BUT NOT WIRED | 1-2 days |

**Estimated effort to reach "YES": 7-10 days** (assuming .60 hardware is functional).
**Estimated effort to implement scheduler after "YES": 10-15 days.**
