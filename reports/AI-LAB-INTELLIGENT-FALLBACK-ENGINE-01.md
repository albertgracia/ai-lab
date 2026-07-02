# AI-LAB-INTELLIGENT-FALLBACK-ENGINE-01

**Classification:** PASS

**Date:** 2026-07-02

## Problem

When the deterministic multi-node router selected a node for a model request, and that node failed at runtime (model not loaded, timeout, connection error, 5xx), the gateway returned an error to the client with no fallback attempt.

Existing "model unloaded" retry in the non-streaming path was model-specific and did not use multi-node topology.

## Solution

Intelligent Fallback Engine (IFE) — a deterministic, capability-safe fallback layer integrated into the gateway's error paths.

### New file

`runtime/router/fallback_engine.py`

- `classify_backend_failure(response_status, response_body, exception, error_message)` — classifies failures into 10 types with policy flags (retryable, fallback_allowed, requires_same_model, safe_degrade_allowed, confidence)
- `build_fallback_candidates(requested_model, failed_node_id, registry)` — ordered candidates by preference (same_model > equivalent_model > capability_match)
- `select_fallback_candidate(candidates, requested_model)` — enforces capability safety (vision/large-context/coding/reasoning)
- `build_capacity_unavailable_error(...)` — clear error when no safe fallback exists

### Modified files

- `runtime/gateway/openai_gateway.py` — `_try_fallback()` helper + integration at 3 points (IFE-01, IFE-02, IFE-03)
- `runtime/routing/routing_history.py` — `record_route_result()` accepts 7 new fallback fields
- `runtime/control/control_plane.py` — `get_control_routes()` and `explain_last_route()` expose all fallback fields

## Design Decisions

### No Prometheus metrics
IFE observability lives entirely in route history / control plane. The existing `ailab_fallback_leakage_blocked_total` metric (FASE 30H.1 evidence guard) is unrelated — it prevents unknown→invented leakage in report context injection.

### Fallback is always non-streaming
IFE pops `stream` from payload before retrying. This is safe degradation — the client gets a valid response instead of an error.

### Single attempt
Exactly one fallback candidate is tried. If it fails, the original error is returned.

### Capability safety
Vision models never fall back to text-only nodes. Large-context, coding, and reasoning models have analogous protection.

## Files Changed

| File | Change |
|------|--------|
| `runtime/router/fallback_engine.py` | **NEW** — Failure classification, candidate building, selection, capacity_unavailable error |
| `runtime/gateway/openai_gateway.py` | `_try_fallback()` helper + 3 integration points (IFE-01/02/03) |
| `runtime/routing/routing_history.py` | `record_route_result()` — 7 new fallback params |
| `runtime/control/control_plane.py` | `get_control_routes()` and `explain_last_route()` — expose fallback fields |

## Tests

`tests/test_fallback_engine_01.py` — 26 unit tests:

| Test | Type | Count |
|------|------|-------|
| Failure classification (all 10 types) | Unit | 10 |
| Same-model fallback | Unit | 3 |
| Capability-aware fallback (vision/coding/reasoning) | Unit | 4 |
| Vision protection | Unit | 1 |
| Offline node exclusion | Unit | 2 |
| No safe fallback → None | Unit | 2 |
| `capacity_unavailable` error format | Unit | 2 |
| Equivalent model fallback | Unit | 1 |
| Multi-node fallback ordering | Unit | 1 |

**Total: 26/26 PASS**

All 38 existing Dynamic Node Registry tests remain PASS.

## Validation

| Check | Result |
|-------|--------|
| 26 unit tests | ✅ PASS |
| 38 DNR tests (no regression) | ✅ PASS |
| Gateway health | ✅ OK |
| Router health | ✅ OK |
| `.50` coding request | ✅ `qwen2.5-14b-instruct` via `rx9070-node` |
| `.60` large model request | ✅ `qwen3.6-35b-a3b` via `rx7900xt-node` |
| Default request | ✅ routed + succeeded |
| `.50` reasoning model | ✅ `deepseek-r1-distill-qwen-14b` |
| Route history fallback fields | ✅ All 8 fields present and correct |
| Fallback triggered (live test) | ✅ `llama-3.1-8b` → `rx7900xt-node` via IFE |
| `fallback_unavailable` recorded | ✅ `failure_type="unknown_backend_error"` + `reason_codes=["fallback_unavailable"]` |
| SLO health | ✅ 0 violations, healthy |

## Route History Fields

After deployment, each route entry exposes:

| Field | Example |
|-------|---------|
| `fallback_triggered` | `true` |
| `failure_type` | `model_not_loaded` |
| `original_model` | `llama-3.1-8b-instruct` |
| `original_node` | `rx9070-node` |
| `fallback_model` | `llama-3.1-8b-instruct` |
| `fallback_node` | `rx7900xt-node` |
| `fallback_reason` | `capability_match_on_rx7900xt-node` |
| `reason_codes` | `["intelligent_fallback"]` |

## Rollback

```bash
# Remove fallback_engine.py (restore ModuleNotFoundError → no fallback)
ssh albert@192.168.1.30 "rm /opt/ai-lab/runtime/router/fallback_engine.py"

# Restore original openai_gateway.py, routing_history.py, control_plane.py
ssh albert@192.168.1.30 "cp /opt/ai-lab/runtime/gateway/openai_gateway.py.bak.ife01 /opt/ai-lab/runtime/gateway/openai_gateway.py"
ssh albert@192.168.1.30 "cp /opt/ai-lab/runtime/routing/routing_history.py.bak.ife01 /opt/ai-lab/runtime/routing/routing_history.py"
ssh albert@192.168.1.30 "cp /opt/ai-lab/runtime/control/control_plane.py.bak.ife01 /opt/ai-lab/runtime/control/control_plane.py"

# Restart gateway
ssh albert@192.168.1.30 "pkill -f openai_gateway.py"
```

## Final Questions

### 1. What was the problem?
When deterministic multi-node routing selected a node that failed at runtime, the gateway returned an error with no fallback attempt.

### 2. What changed?
Added `runtime/router/fallback_engine.py` with failure classification, candidate building, and capability-safe selection. Integrated via `_try_fallback()` in gateway error paths. Exposed 8 fallback fields in route history / control plane.

### 3. Does fallback preserve capability safety?
Yes. Vision, large-context, coding, and reasoning models only fall back to nodes with matching capability sets.

### 4. Does fallback add Prometheus metrics?
No. IFE observability is via route history / control plane only. The existing `ailab_fallback_leakage_blocked_total` is from the FASE 30H.1 evidence guard, not IFE.

### 5. Regression?
None. All existing routing unchanged. All 38 DNR tests pass.

### 6. Final classification:
**PASS**
