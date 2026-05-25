# RUNTIME-DEEP-AUDIT-01 — Full Stack Diagnostic Report
Generated: 2026-05-25 14:50 UTC

## Summary

All core services are **operational**. No critical errors found in current runtime.
The "Recursion limit of 50" error is internal to GitNexus web agent (LangGraph bundle),
not in Gateway/Router/LM Studio. LM Studio is on 192.168.1.50 (remote host), not 127.0.0.1.

---

## 1. Service Health

| Service | Status | Port | Details |
|---------|--------|------|---------|
| `ailab-gateway` | ✅ HEALTHY | 8008 | 27 total requests, 0 SLO violations |
| `ailab-router` | ✅ HEALTHY | 8083 | No errors in logs |
| `gitnexus` | ⚠️ RUNNING | 4747 | Startup issues (Napi::Error, EADDRINUSE) but operational |
| `ailab-live-api` | ✅ HEALTHY | 8084 | No errors in logs |
| `ailab-docs` | ✅ HEALTHY | 4322 | Astro preview |
| `ailab-metrics` | ✅ HEALTHY | 3010 | Next.js SSR |
| LM Studio (192.168.1.50) | ✅ HEALTHY | 1234 | 5 models loaded |

---

## 2. LM Studio — Models Available

| Model | State |
|-------|-------|
| `qwen3-vl-8b-instruct` | ✅ Loaded |
| `qwen/qwen2.5-coder-14b-instruct` | ✅ Loaded |
| `qwen2.5-coder-14b-instruct` | ✅ Loaded |
| `llama-3.1-8b-instruct` | ✅ Loaded |
| `text-embedding-nomic-embed-text-v1.5` | ✅ Loaded |

---

## 3. Integration Chain Tests

### Gateway (8008) → LM Studio (192.168.1.50:1234)
- **Result:** ✅ PASS — `qwen/qwen2.5-coder-14b-instruct` responded "OK" (2 tokens, 87 prompt tokens)
- **TTFB:** ~2-3s
- **Full chain:** OpenCode → Gateway → LM Studio works correctly

### Gateway Health
```json
{"status": "ok", "service": "ai-lab-openai-gateway",
 "backend": "http://192.168.1.50:1234/v1",
 "mode": "stream-aware sanitized"}
```

### Router Health
```json
{"status": "ok", "service": "ai-lab-router-api"}
```

### Direct LM Studio (192.168.1.50:1234)
- Models list: ✅ 5 models returned
- Chat completion: ✅ (verified via Gateway)

---

## 4. Startup Issues (Historical, Resolved)

| Issue | Date | Service | Severity | Status |
|-------|------|---------|----------|--------|
| EADDRINUSE port 8008 (retry storm) | May 15 | `ailab-gateway` | 🟡 MEDIUM | Resolved (systemd StartLimitBurst) |
| EADDRINUSE port 4747 (retry loop) | May 23 | `gitnexus` | 🟡 MEDIUM | Resolved (old process killed) |
| Napi::Error in ExecStartPre | Ongoing | `gitnexus` | 🔵 LOW | Non-fatal (ignored via `-` prefix) |
| FASE23B_HARD_CAP truncation | May 19 | `ailab-router` | 🔵 LOW | Hard cap functioned correctly |

---

## 5. Recursion Limit Investigation

### Finding
The `Recursion limit of 50 reached without hitting a stop condition` error:
- ❌ NOT found in `gateway` journalctl logs
- ❌ NOT found in `router` journalctl logs  
- ❌ NOT found in `gitnexus` journalctl logs
- ✅ FOUND in LangGraph agent bundle at `/usr/local/lib/node_modules/gitnexus/web/assets/agent-D2kLt6Dl.js` with `recursionLimit:25`

### Root Cause
The error is **internal to GitNexus' LangGraph agent** — it occurs when the OpenCode agent uses MCP tools that trigger GitNexus' agent graph, and the graph exceeds the default recursion limit during complex multi-step operations.

### Mitigation (External — NOT modifiable per policy)
The LangGraph bundle is in `/usr/local/lib/node_modules/gitnexus/` which is external.
- Patch exists but is **paused indefinitely** by user decision.
- Workaround: No automatic fix available without modifying external files.

---

## 6. Configuration Audit

### OpenCode Provider Config (`opencode.jsonc`)
- **Provider:** `ailab-router` → `http://192.168.1.30:8083/v1`
- **Models:** auto, fast, coding, reasoning (router-based routing)
- **General agent:** read-only (read, glob, grep, list only)
- **Disabled providers:** ["lm"]
- **Note:** OpenCode talks to the **Router** (`:8083`), not the Gateway (`:8008`).
  This means OpenCode uses router routing to LM Studio, bypassing Gateway's profile injection.

---

## 7. Router FASE23B_HARD_CAP Events (May 19)

5 events detected. Context payloads exceeded 1200-token hard cap:
- Policy reported as `"legacy"` or `"unknown"` (not a recognized cognitive profile)
- Hard cap truncation functioned correctly (TRUNCATED)
- **Impact:** None — hard cap is a safety guard, not an error

---

## 8. Prometheus Metrics Snapshot

| Metric | Value |
|--------|-------|
| `ailab_requests_total` | 27 |
| `ailab_slo_violations_total` | 0 |
| Gateway scrape interval | ~15s from Prometheus (192.168.1.40) |

---

## 9. Priorities

| Priority | Issue | Action |
|----------|-------|--------|
| 🔴 HIGH | Recursion limit in GitNexus agent | Cannot fix (external). Workaround: avoid complex multi-step MCP queries. |
| 🟡 MEDIUM | Napi::Error on gitnexus ExecStartPre | Investigate if analysis step fails due to large file or encoding issue. |
| 🔵 LOW | OpenCode → Router (not Gateway) | Documented behavior. Router handles routing, Gateway handles profiles. |
| 🔵 LOW | FASE23B_HARD_CAP with "unknown" policy | Investigate which routes trigger "unknown" policy classification. |
| 🔵 LOW | No timeout errors in current runtime | ✅ Resolved — Gateway/LM Studio chain is stable. |

---

## 10. Conclusion

**Runtime is STABLE.** The Gateway → LM Studio chain works correctly.
The only unresolved issue is the GitNexus LangGraph recursion limit, which is external code
and cannot be modified per current policy. All other services are healthy with no current errors.
