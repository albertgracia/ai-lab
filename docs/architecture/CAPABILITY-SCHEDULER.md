# Capability Scheduler

## Purpose

Deterministic capability-based scheduling — selects a node/model pair when the requested model requires a specific capability (vision, large-context, or rx7900xt-only model).

Scheduler runs BEFORE deterministic multi-node routing. If the scheduler selects a node, that node is used. If the scheduler skips (normal chat/coding), the existing DNR routing handles it.

## Design Constraints

- **NOT adaptive learning** — Deterministic, explainable scheduling. Every decision records `reason_codes[]`, `evidence[]`, `rejected_candidates[]`.
- **Does NOT replace deterministic routing** — Only activates for vision, large-context, or rx7900xt-required models. Normal chat/coding always goes through DNR.
- **Does NOT replace fallback engine** — Fallback engine still fires if the scheduled node fails at runtime.
- **Does NOT auto-start nodes** — Only uses online, routing-eligible nodes from Dynamic Node Registry.
- **No silent unsafe degradation** — Vision models never route to text-only nodes. Large-context models never route to small-context nodes.
- **No Prometheus metrics** — Observability lives in route history `reason_codes[]`.

## How It Works

### 1. Capability Extraction (`extract_capability_requirements`)

Deterministic extraction from (in priority order):

| Source | Example |
|--------|---------|
| Requested model ID prefix | `moondream2-*` → vision, `qwen3.6-35b-*` → large-context |
| Profile name | `coding` → coding_required |
| Route family | `tool_fastpath` → tool_required |
| Operator intent | `required_capabilities: ["vision"]` |
| Message content | Image in messages → vision, code keywords → coding |

### 2. Triggering Capabilities

Only three capabilities trigger the scheduler:
- `vision_required` (model_prefix: moondream, vision, llava, qwen-vl, etc.)
- `large_context_required` (model_prefix: 30b, 32b, 35b, 70b, xl)
- `requires_rx7900xt` (model explicitly canonically mapped to .60)

Coding, reasoning, and embedding models exist on both .50 and .60, so they use DNR + fallback, NOT the scheduler.

### 3. Candidate Building (`build_scheduler_candidates`)

Consumes Dynamic Node Registry (only `online` + `routing_eligible` nodes). Each candidate includes:
- `node_id`, `url`, `model`, `capability_match`, `health_score`, `slo_ok`, `score`, `reasons[]`

### 4. Scoring (`score_candidate`)

Deterministic scoring with gates:

| Gate | Condition | Score |
|------|-----------|-------|
| rx7900xt-required model | model not on .60 → **rejected** | 0 |
| Vision/Large-context mismatch | node lacks capability → **rejected** | 0 |
| Model available | model found on node | +2.0 |
| Capability match | node has the capability | +2.0 |
| Health score | node health (0.0–1.0) | +health×1.0 |
| SLO ok | node not degraded | +1.0 (or -1.0 if degraded) |
| Role preference | GPU node preferred | +0.5 |

### 5. Selection (`select_best_candidate`)

Highest score wins. Tie-breaking: vision/large-context prefers .60; normal prefers .50.

### 6. Decision Pipeline (`build_scheduler_decision`)

Returns one of:
- `decision: "skip"` — No triggering capability; caller falls through to DNR
- `decision: "selected"` — Scheduler decided; caller uses `selected_node`, `selected_model`, `backend_url`
- `decision: "capacity_unavailable"` — No eligible candidates

## Gateway Integration

In `openai_gateway.py`, the scheduler runs BEFORE DNR:

```python
# CAPABILITY-SCHEDULER-01: deterministic capability scheduling
_scheduler_decision = build_scheduler_decision(...)
if _scheduler_decision.get("decision") == "selected":
    # Override target backend with scheduler choice
    _target_backend = {"name": ..., "url": ...}
    _scheduler_selected = True

if not _scheduler_selected:
    # Fall through to DNR (existing multi-node routing)
    _target_backend = get_active_backend()
    resolve_backend_for_model(...)
```

Route history records `reason_codes` from the scheduler (e.g. `["scheduler_selected", "capability_match_on_rx7900xt-node"]`).

## Files

| File | Role |
|------|------|
| `runtime/router/capability_scheduler.py` | Scheduler engine (651 lines) |
| `runtime/gateway/openai_gateway.py` | Integration (3 insertion points: routing + 2 fallback paths) |
| `tests/test_capability_scheduler_01.py` | 37 unit tests |

## Validation

- **37/37 unit tests** PASS (extraction, candidate scoring, selection, SLO, output contract, reason codes, Hermes profile)
- **101/101 combined tests** PASS (37 scheduler + 26 fallback + 38 DNR)
- **Live validation**: moondream2 → .60 ✅, qwen3.6-35b → .60 ✅, qwen2.5-14b → .50 (skip) ✅
- **Route history**: scheduler reason_codes visible in JSONL ✅
- **Fallback preserved**: IFE fallback still works independently ✅
