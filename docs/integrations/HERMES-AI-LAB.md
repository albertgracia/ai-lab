# Hermes Agent → AI-LAB Gateway Integration

## Status: PARTIAL

Integration verified end-to-end but blocked by model context limit (n_ctx=8192 < 12K tokens from Hermes' AGENTS.md + 74 skills).

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
# Basic (may exceed 8K context — use --ignore-rules for compatibility)
hermes -p ai-lab chat -q "query" --ignore-rules

# Via wrapper alias
ai-lab chat -q "query" --ignore-rules
```

## Issues Found

### 1. Model Context Limit (BLOCKER for full integration)

- LM Studio loads `qwen2.5-14b-instruct` with `n_ctx=8192` (default for 16GB VRAM)
- Hermes injects ~12,787 tokens (AGENTS.md 54K chars + 74 skills + SOUL.md)
- Error: `n_keep: 12779 >= n_ctx: 8192`

**Workaround:** Use `--ignore-rules` (skips AGENTS.md injection), reducing context to ~5K tokens

**Resolution options (in priority order):**
1. **Increase LM Studio context length** — Set `n_ctx=16384` in LM Studio model config (reduces VRAM available for batch/concurrent)
2. **Trim AGENTS.md** — Reduce 54K chars to fit within 8K context
3. **Hermes skills profile** — Create profile with fewer/selective skills
4. **Gateway context truncation** — Gateway auto-truncates long contexts before forwarding

### 2. Rate Limit (PATCHED)

- Default: 30 req/60s per IP → bumped to 120 req/60s
- Deployed via SIGTERM restart: PID 62230 → 72412

### 3. Gateway Routing Override (PRE-EXISTING BUG)

- Gateway routing logic overrides requested model with `qwen3-vl-8b-instruct` (not loaded)
- `qwen2.5-14b-instruct` (raw LM Studio ID) is NOT in `_BACKEND_MODEL_MAP` — falls through to broken routing
- Only `qwen/qwen2.5-coder-14b-instruct` and `qwen2.5-coder-14b-instruct` are correctly mapped

### 4. Operational Fastpath (PRE-EXISTING)

- Short prompts like "What is 2+2?" trigger operational fastpath instead of LLM
- Gateway returns hardcoded "Infrastructure" response (not the actual answer)

## Smoke Test Results

| Test | Prompt | Result | Notes |
|------|--------|--------|-------|
| Chat | "Say just OK" | ✅ PASS | Returns "OK", ~13s latency |
| Coding | "Write Python prime function" | ✅ PASS | Returns code + explanation, ~21s |
| Reasoning | "What is 2+2?" | ❌ FAIL | Triggers operational fastpath (pre-existing) |

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
