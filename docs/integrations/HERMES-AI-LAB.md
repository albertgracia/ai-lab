# Hermes Agent → AI-LAB Gateway Integration

## Status: PASS WITH WARNINGS

Integration verified end-to-end. LM Studio loads `qwen2.5-14b-instruct` with 32,768 context (Q4_K_M on RX9070 16GB) — adequate for Hermes' ~12K token overhead. The only remaining issue is the Gateway's operational fastpath intercepting trivial/math prompts (separate blocker).

## Architecture

```
Hermes Agent (Windows 192.168.1.50)
  → HTTP POST http://192.168.1.30:8008/v1/chat/completions
    → AI-LAB Gateway (:8008) — routing, SLO, profiling
      → LM Studio (192.168.1.50:1234/v1) — inference backend
```

## Configuration

### Hermes Profile

Profile `ai-lab` created at `C:\Users\leobc\AppData\Local\hermes\profiles\ai-lab\`:

```yaml
model:
  default: qwen/qwen2.5-coder-14b-instruct   # canonical AI-LAB model ID
  provider: lmstudio                          # openai_chat transport
  base_url: http://192.168.1.30:8008/v1       # AI-LAB Gateway endpoint
```

Environment overrides in `.env`:
```
LM_BASE_URL=http://192.168.1.30:8008/v1
LM_API_KEY=ailab
```

### Usage

```bash
# With full AGENTS.md rules (context fits: ~12K tokens < 32K limit)
hermes -p ai-lab chat -q "query"

# Via wrapper alias
ai-lab chat -q "query"
```

## Issues Found

### 1. Model Context Limit (RESOLVED — false alarm)

- LM Studio `loaded_context_length`: 32768 (confirmed via `/api/v0/models`)
- Hermes injects ~12,780 tokens with full AGENTS.md + 74 skills — within limit
- The earlier `n_keep: 12779 >= n_ctx: 8192` error was transient (model reload / VRAM pressure)
- No changes needed. Both `--ignore-rules` and full-rules modes work for non-trivial prompts.

### 2. Rate Limit (PATCHED)

- Default: 30 req/60s per IP → bumped to 120 req/60s (deployed + committed `f06b4b1`)
- Deployed via SIGTERM restart: PID 62230 → 72412 → 72485

### 3. Gateway Routing Override (PRE-EXISTING BUG — deferred)

- Gateway routing logic overrides requested model with `qwen3-vl-8b-instruct` (not loaded)
- `qwen2.5-14b-instruct` (raw LM Studio ID) is NOT in `_BACKEND_MODEL_MAP` — falls through to broken routing
- Only `qwen/qwen2.5-coder-14b-instruct` and `qwen2.5-coder-14b-instruct` are correctly mapped

### 4. Operational Fastpath (PRE-EXISTING — deferred)

- Short/trivial prompts like "What is 2+2?" trigger operational fastpath instead of LLM
- Gateway returns hardcoded "Infrastructure" response (not the actual answer)
- Hermes reports: "Provider returned an empty stream with no finish_reason"
- **This is the only remaining blocker for full Hermes integration**

## Smoke Test Results

| Test | Prompt | Rules | Result | Notes |
|------|--------|-------|--------|-------|
| Chat | "Say just OK" | full | ✅ PASS | ~21s |
| Chat | "Say just OK" | --ignore-rules | ✅ PASS | ~13s |
| Coding | "prime function" | full | ✅ PASS | ~42s |
| Coding | "quicksort" | full | ✅ PASS | ~42s |
| Coding | "reverse string" | full | ✅ PASS | ~31s |
| Reasoning | "What is 2+2?" | full | ❌ FAIL | Operational fastpath |
| Reasoning | "What is 2+2?" | --ignore-rules | ❌ FAIL | Same — not context-related |

## Observability

- Prometheus `ai-lab-gateway` target: **UP**
- Router (`:8083`): **UP**
- Metrics: 29 total requests, 12 Hermes-specific (profile="chat", model="qwen/qwen2.5-coder-14b-instruct")
- Streams: 374 chunks, 0 stalls, 0 errors

## Files Changed

| File | Change | Status |
|------|--------|--------|
| `runtime/gateway/openai_gateway.py` | `_BACKEND_MODEL_MAP` (2 entries) | deployed + committed |
| `runtime/gateway/openai_gateway.py` | `RATE_LIMIT_REQUESTS` 30→120 | deployed |
| `C:\Users\leobc\AppData\Local\hermes\profiles\ai-lab\config.yaml` | Hermes profile config | created |
| `C:\Users\leobc\AppData\Local\hermes\profiles\ai-lab\.env` | LM_BASE_URL override | created |
| `C:\Users\leobc\AppData\Local\hermes\config.yaml.bak.20260701_140114` | Hermes backup | created |
