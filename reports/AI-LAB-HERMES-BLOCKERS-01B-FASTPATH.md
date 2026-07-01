# AI-LAB-HERMES-BLOCKERS-01B-FASTPATH

**Status:** PASS

**Date:** 2026-07-01

## Objective

Resolve operational fastpath capturing trivial/reasoning prompts ("What is 2+2?" → "Infrastructure" instead of LLM).

## Root Cause

Three-layer capture in `tool_request_classifier.py`:

1. `_FASTPATH_INTENTS["infrastructure"]` contained `"what is"`, `"who is"`, `"qué es"`, `"que es"` — bare question words that matched any query starting with those phrases
2. `select_operational_response_profile()` used `detect_operational_fastpath_intent()` which returned `"infrastructure"` → response profile became `"operational_compact"`
3. Gateway fastpath block (line 854) short-circuited to `build_fastpath_response()` instead of forwarding to LLM

Same pattern existed in `operational_fastpath.py`'s `_FAST_MAP` for consistency.

## Fix

**File: `runtime/gateway/tool_request_classifier.py:540-543`**

Removed `"que es", "qué es", "who is", "what is"` from `_FASTPATH_INTENTS["infrastructure"]`. The IP-specific identity check (line 610) remains — it requires both `what is/who is` + IP address pattern, correctly identifying legitimate operational queries like "What is 192.168.1.30?".

**File: `runtime/fastpath/operational_fastpath.py:110`**

Removed `"who is", "what is", "qué es", "que es"` from `_FAST_MAP` `FAST_INFRASTRUCTURE` for consistency.

## Validation

### Direct Gateway (non-streaming)

| Prompt | Before | After |
|--------|--------|-------|
| "What is 2+2?" | ❌ Infrastructure | ✅ "2 + 2 = 4" |
| "Say hello in one word" | ✅ Hola | ✅ Hola |
| "Write a tiny Python function" | ✅ code | ✅ code |
| "Check AI-LAB health" | ✅ operational | ✅ operational |
| "What is 192.168.1.30?" | ✅ operational (IP match) | ✅ operational |
| "estado runtime" | ✅ operational | ✅ operational |

### Hermes (streaming)

| Prompt | Before | After |
|--------|--------|-------|
| "What is 2+2?" | ❌ empty stream error | ✅ "The answer to 2+2 is 4" |
| "Write Python add function" | ✅ code | ✅ code |
| "Check AI-LAB health" | N/A | ❌ pre-existing streaming compat issue |

### Unit Tests

- 28/28 `test_fastpath_routing_priority_35d_hf1.py` PASS
- 25/25 `test_operational_fastpath_35d.py` PASS

## Deploy

1. SCP fixed files to `/tmp/` on 192.168.1.30
2. `cp` to `/opt/ai-lab/runtime/gateway/tool_request_classifier.py` and `/opt/ai-lab/runtime/fastpath/operational_fastpath.py`
3. Backups: `*.bak.20260701-fastpath`
4. SIGTERM → PID 72485 → 169127 (systemd autorestart)

## Files Changed

| File | Change |
|------|--------|
| `runtime/gateway/tool_request_classifier.py` | Removed 4 bare question-word patterns from infrastructure intents |
| `runtime/fastpath/operational_fastpath.py` | Removed same 4 patterns from FAST_INFRASTRUCTURE map |

## Rollback

```bash
cp /opt/ai-lab/runtime/gateway/tool_request_classifier.py.bak.20260701-fastpath /opt/ai-lab/runtime/gateway/tool_request_classifier.py
cp /opt/ai-lab/runtime/fastpath/operational_fastpath.py.bak.20260701-fastpath /opt/ai-lab/runtime/fastpath/operational_fastpath.py
kill -TERM $(cat /opt/ai-lab/runtime/gateway/.gateway_pid)
```

## Remaining Issues

- **Operational health check through Hermes**: Pre-existing streaming compatibility issue (Gateway returns operational fastpath response, Hermes expects SSE stream format). Not related to this fix.
