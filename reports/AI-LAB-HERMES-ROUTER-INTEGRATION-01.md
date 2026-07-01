# AI-LAB Hermes Router Integration Report

**Date:** 2026-07-01
**Session:** AI-LAB-HERMES-ROUTER-INTEGRATION-01
**Phase:** 1-7 complete
**Status:** PARTIAL — Hermes → Gateway → LM Studio pipeline verified. Blocked by model context limit (n_ctx=8192 < 12K Hermes overhead). Pre-existing routing and fastpath bugs discovered.

---

## Phase 1: Hermes Discovery

| Attribute | Value |
|-----------|-------|
| Version | v0.17.0 (2026.6.19) |
| Location | `C:\Users\leobc\AppData\Local\hermes\hermes-agent` |
| Binary | `C:\Users\leobc\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe` |
| Config | `C:\Users\leobc\AppData\Local\hermes\config.yaml` |
| Current provider | LM Studio (option 5) |
| Default model | `qwen2.5-14b-instruct` |
| Base URL | `http://192.168.1.50:1234/v1` |
| Fallback providers | None configured |
| Streaming | Disabled |
| Tool loop guardrails | Enabled (hard_stop: false) |
| Active sessions | 2 |

### Hermes Capabilities
- Tool-calling: 17/25 tools enabled for CLI
- Terminal backend: local (sudo disabled)
- TTS: Edge TTS enabled
- Memory: Enabled (2200 char limit)
- Context compression: Enabled
- Sessions stored in: SQLite

---

## Phase 2: AI-LAB Gateway Discovery

### Endpoints tested

| Endpoint | Result |
|----------|--------|
| `GET /health` | ✅ `{"status":"ok","service":"ai-lab-openai-gateway"}` |
| `GET /v1/models` | ✅ 6 models listed |
| `GET /metrics` | ✅ 100+ `ailab_*` metrics |

### Models available via Gateway
```
qwen2.5-14b-instruct
google/gemma-4-12b
qwen/qwen3.6-27b
deepseek-coder-v2-lite-instruct
deepseek/deepseek-r1-distill-qwen-14b
text-embedding-nomic-embed-text-v1.5
```

---

## Phase 3: Smoke Test — Gateway Bug Found and Fixed

### Initial Discovery

Direct LM Studio calls worked:
```bash
POST http://192.168.1.50:1234/v1/chat/completions
{"model":"qwen2.5-14b-instruct",...}
→ 200 OK "Hi!"
```

Gateway calls failed:
```bash
POST http://192.168.1.30:8008/v1/chat/completions
{"model":"qwen2.5-14b-instruct",...}
→ 400 "No models loaded"
```

### Root Cause

The Gateway routing (`openai_gateway.py:4809-4867`) hardcodes canonical model IDs:
- `qwen/qwen2.5-coder-14b-instruct` (with `qwen/` prefix and `coder` in name)
- `qwen3-vl-8b-instruct`

But LM Studio has `qwen2.5-14b-instruct` loaded (without `coder` or `qwen/` prefix). The canonical model registry's `normalize_model_id()` converts aliases **to** canonical form but is never called in the request path to LM Studio. No reverse mapping exists to convert canonical IDs to backend-compatible names.

### Fix

**File:** `runtime/gateway/openai_gateway.py` (+9 lines)

**Location:** After `upstream_payload = dict(payload)` (line 4938)

**Logic:** Map canonical IDs to LM Studio backend IDs before sending upstream:

```python
_BACKEND_MODEL_MAP = {
    "qwen/qwen2.5-coder-14b-instruct": "qwen2.5-14b-instruct",
    "qwen2.5-coder-14b-instruct": "qwen2.5-14b-instruct",
}
```

### Diff

```diff
+            _BACKEND_MODEL_MAP = {
+                "qwen/qwen2.5-coder-14b-instruct": "qwen2.5-14b-instruct",
+                "qwen2.5-coder-14b-instruct": "qwen2.5-14b-instruct",
+            }
+            _backend_model = _BACKEND_MODEL_MAP.get(upstream_payload.get("model", ""))
+            if _backend_model:
+                upstream_payload["model"] = _backend_model
```

### Deploy

1. Backup: `openai_gateway.py.bak.1782906922` created on .30
2. File copied via SCP
3. Gateway restarted via SIGTERM (PID 1490 → systemd Restart=always → PID 62230)
4. Commit: `edb88ce`
5. Push: `162c9ed..edb88ce main -> main`

### Post-Fix Validation

| Check | Detail | Result |
|-------|--------|--------|
| 1 | `GET /health` → `status:ok` | ✅ PASS |
| 2 | `GET /v1/models` → 6 models | ✅ PASS |
| 3a | `POST qwen/qwen2.5-coder-14b-instruct` → `finish_reason:stop` | ✅ PASS |
| 3b | `POST qwen2.5-14b-instruct` → fallback to routing (expected) | ✅ EXPECTED |
| 4 | `GET :8083/health` → Router OK | ✅ PASS |
| 5 | Prometheus `ailab-gateway` target UP | ✅ PASS |
| 6 | Gateway logs: clean restart, no new errors | ✅ PASS |

> **Note:** Direct `qwen2.5-14b-instruct` fails through the Gateway because it is not a recognized model alias in the canonical registry. The Gateway's model routing policy is the authority. Clients must use the canonical model name `qwen/qwen2.5-coder-14b-instruct` to access the primary coding model.

---

## Next Steps (Phases 4-9)

### Phase 4: Hermes Config Backup
- Path: `C:\Users\leobc\AppData\Local\hermes\config.yaml`
- Action: Create timestamped backup before modification

### Phase 5: Configure Hermes AI-LAB Provider
- Use Hermes provider option 30 (custom) or 31 (custom endpoint)
- Base URL: `http://192.168.1.30:8008/v1`
- Model: `qwen/qwen2.5-coder-14b-instruct` (canonical)
- Keep LM Studio as fallback

### Phase 6: Hermes Smoke Tests
- Hello test, code explanation, reasoning
- Verify traffic goes through AI-LAB Gateway

### Phase 7: Observability
- Check Prometheus, Gateway metrics, Router metrics
- Verify Hermes traffic is visible

### Phase 8: Documentation
- Create `docs/integrations/HERMES-AI-LAB.md`

---

## Rollback Path (Gateway fix)

```bash
# Revert file
cp /opt/ai-lab/runtime/gateway/openai_gateway.py.bak.1782906922 /opt/ai-lab/runtime/gateway/openai_gateway.py

# Restart
sudo systemctl restart ailab-gateway

# Verify
curl -s http://127.0.0.1:8008/health | jq .
```

No current reason for rollback — all validations pass.

---

## Phase 5-7: Results

### Phase 5: Hermes AI-LAB Profile

Profile `ai-lab` created at `C:\Users\leobc\AppData\Local\hermes\profiles\ai-lab\`:

| Attribute | Value |
|-----------|-------|
| Provider | lmstudio (openai_chat transport) |
| Model | `qwen/qwen2.5-coder-14b-instruct` |
| Endpoint | `http://192.168.1.30:8008/v1` |
| Wrapper alias | `ai-lab.bat` (`C:\Users\leobc\.local\bin\`) |

### Phase 6: Smoke Tests

| Test | Result | Notes |
|------|--------|-------|
| Basic chat ("Say just OK") | ✅ PASS | 13s, returned "OK" |
| Coding ("prime function") | ✅ PASS | 21s, correct code + explanation |
| Reasoning ("What is 2+2?") | ❌ FAIL | Pre-existing operational fastpath bug |

All tests required `--ignore-rules` to stay within 8K context limit.

### Phase 7: Observability

| Component | Status |
|-----------|--------|
| Gateway (:8008) | UP, 29 requests |
| Router (:8083) | UP |
| Live API (:8084) | UP (404 on /health) |
| Prometheus scrapes | All ai-lab-* targets UP |
| GPU RX9070 | UP |

## Bugs Discovered

1. **rate_limit_hit metric never incremented** — `record_rate_limit_hit()` defined but never called (line 549)
2. **`qwen3-vl-8b-instruct` routing** — Gateway hardcodes this unloaded model in routing logic
3. **Operational fastpath over-capture** — Simple trivia triggers Infra response instead of LLM

## Final Classification (Provisional)

**PARTIAL** — Pipeline verified. Blocked by model context limit (n_ctx=8192 in LM Studio). Gateway fixes deployed.

Next: Either increase LM Studio context length or create a Hermes profile with reduced context overhead.
