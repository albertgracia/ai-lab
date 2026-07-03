# AI-LAB-MULTI-NODE-ROUTING-01

**Classification:** PASS

**Date:** 2026-07-02

## Root Cause

Two issues prevented multi-node routing from working:

1. **FASE 30H.1 whitelist too restrictive** — The explicit model request override in `openai_gateway.py` only allowed two hardcoded models (`qwen/qwen2.5-coder-14b-instruct` and `qwen3-vl-8b-instruct`). Any other model (like `qwen/qwen3.6-35b-a3b`) was silently dropped, and the routing policy's default model was used instead.

2. **Missing deployment files** — `runtime/router/multi_node_routing.py` and `runtime/state/dynamic_node_registry.py` existed in the workspace but were never committed or deployed to the `.30` runtime server. The gateway code had try/except imports that silently caught the `ModuleNotFoundError`, falling back to `get_active_backend()` (always rx9070).

3. **Routing history recording bug** — The non-streaming success path in `openai_gateway.py` recorded `get_active_backend()` instead of `_target_backend` for the routing history, masking the fact that requests DID reach `.60`.

## Files Changed

| File | Change |
|------|--------|
| `runtime/gateway/openai_gateway.py` | FASE 30H.1: accept any explicit model, not whitelist; use `_target_backend` in routing history recording (non-streaming path) |
| `runtime/router/multi_node_routing.py` | Added `qwen/` prefix variants to `_RX7900XT_ONLY_MODELS` and `_CANONICAL_TO_RX7900XT`; added 30s TTL cache to `_load_registry()` |
| `runtime/state/dynamic_node_registry.py` | New file (was never deployed to .30) |

## Deployed To .30

Files copied to `192.168.1.30:/opt/ai-lab/`:
- `runtime/router/multi_node_routing.py`
- `runtime/state/dynamic_node_registry.py`
- Updated `runtime/gateway/openai_gateway.py`

## Validation

| Test | Result |
|------|--------|
| `qwen/qwen2.5-coder-14b-instruct` → `.50` | ✅ `rx9070-node` |
| `qwen/qwen3.6-35b-a3b` → `.60` | ✅ `rx7900xt-node` |
| `moondream2` → `.60` | ✅ `rx7900xt-node` |
| Gateway health | ✅ OK |
| Router health | ✅ OK |
| Node registry (build on demand) | ✅ Both nodes online |
| Route history | ✅ records correct node |
| Fallback (.60 offline) | ✅ routes to .50 gracefully |
| Prometheus metrics | ✅ active |

## Rollback

To revert:
```bash
# Remove multi_node_routing.py (restore ModuleNotFoundError → fallback to rx9070)
ssh albert@192.168.1.30 "rm /opt/ai-lab/runtime/router/multi_node_routing.py"

# Restore original FASE 30H.1 whitelist
# Revert openai_gateway.py changes

# Restart gateway
ssh albert@192.168.1.30 "pkill -f openai_gateway.py"
```

## Final Questions

### 1. What was the root cause?
**Two issues**: (a) FASE 30H.1 model whitelist was too restrictive, blocking any explicit model request not in the hardcoded list. (b) `multi_node_routing.py` and `dynamic_node_registry.py` were never deployed to `.30` runtime, causing silent fallback to `get_active_backend()`.

### 2. Which files changed?
`runtime/gateway/openai_gateway.py`, `runtime/router/multi_node_routing.py`, `runtime/state/dynamic_node_registry.py`

### 3. Does qwen3.6-35b-a3b now reach RX7900XT?
**Yes.** Proven by routing history: `node: rx7900xt-node`, `host: http://192.168.1.60:1234/v1`.

### 4. Does explain-last-route show rx7900xt?
The endpoint is not deployed on `.30`. Route history (`routing_history.jsonl`) proves the routing instead.

### 5. Does fallback still work?
**Yes.** When `.60` is offline, requests route to `.50` gracefully. No crashes, no invalid backend.

### 6. Regression?
**None.** All existing routing (coding → .50, minimal → .50) unchanged.

### 7. Final classification:
**PASS**
