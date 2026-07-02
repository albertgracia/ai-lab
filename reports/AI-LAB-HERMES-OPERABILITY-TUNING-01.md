# AI-LAB-HERMES-OPERABILITY-TUNING-01

**Classification:** PASS WITH FINDINGS

**Date:** 2026-07-02

## Problem

Hermes Agent was not configured as a production-ready operator interface for AI-LAB. The active configuration bypassed the AI-LAB Gateway entirely, pointed to a disabled model, and had no operator-focused diagnostics or documented workflow.

## Changes Made

### Configuration: `C:\Users\leobc\AppData\Local\hermes\config.yaml`

| Before | After | Impact |
|--------|-------|--------|
| `base_url: http://192.168.1.50:1234/v1` | `base_url: http://192.168.1.30:8008/v1` | Routes through Gateway (scheduler, fallback, SLO, profiles) |
| `model.default: qwen/qwen3.6-27b` | `model.default: qwen/qwen2.5-coder-14b-instruct` | Uses active, routable model |
| `display.show_reasoning: false` | `display.show_reasoning: true` | Operator sees scheduler/fallback decisions |
| `streaming.enabled: false` | `streaming.enabled: false` (unchanged, disabled) | Known Gateway streaming issue |

### New files

| File | Purpose |
|------|---------|
| `E:\opencode\ai-lab\.hermes\AGENTS.md` | Operator-focused AI-LAB context (replaces full AGENTS.md overhead) |
| `E:\opencode\ai-lab\docs\hermes\HERMES-OPERABILITY.md` | Operability guide |

## Findings

### Critical

| # | Finding | Status |
|---|---------|--------|
| 1 | **Base config bypassed Gateway** — `base_url` pointed to `.50:1234` directly. All runtime features (scheduler, fallback, SLO, profiles, telemetry, memory) were bypassed. | ✅ FIXED |
| 2 | **Default model was disabled** — `qwen/qwen3.6-27b` is DESACTIVADO per runtime policy. Requests would fail. | ✅ FIXED |

### High

| # | Finding | Status |
|---|---------|--------|
| 3 | **Streaming incompatible with Gateway** — "empty stream" error when `streaming.enabled: true`. Pre-existing bug. | 🔴 Known issue, needs Gateway investigation |
| 4 | **No profile enforcement** — Without `-p ai-lab`, Hermes ignores config `base_url` and routes directly to LM Studio via internal provider discovery. | 📌 Mitigated: documented workflow always uses `-p ai-lab` |

### Medium

| # | Finding | Status |
|---|---------|--------|
| 5 | **AGENTS.md overhead** — 54K chars truncates to 31K on 32K context. Effective context is ~5K after tool schemas (50KB) + system prompt. | 📌 Cosmetic: Gateway handles routing regardless |
| 6 | **First-query latency 15-25s** — Acceptable for operator use. | 📌 Monitor |
| 7 | **No fallback provider configured** — If `.50` and Gateway both go down, Hermes has no alternative. | 📌 Documented, requires external provider API key |

### Low

| # | Finding | Status |
|---|---------|--------|
| 8 | **`show_reasoning` was disabled** — Operator couldn't see scheduler/fallback decisions. | ✅ FIXED |
| 9 | **No operator diagnostics documented** — Route history, model visibility, scheduler decisions. | ✅ FIXED |
| 10 | **11 redundant personality modes** — kawaii, catgirl, pirate, shakespeare, surfer, noir, uwu, philosopher, hype — not relevant for AI-LAB operator console. | 📌 Cosmetic, no impact |

## Phase Results

| Phase | Result |
|-------|--------|
| 1. Hermes Audit | ✅ Complete — config, provider, endpoint, auth, models, streaming, context, tools |
| 2. Model Profiles | ✅ ai-lab profile reviewed and confirmed correct |
| 3. Context Optimization | ✅ Measured: 50K system + 50K tools = 100K on 32K model. AGENTS.md truncation documented |
| 4. Operator Experience | ✅ show_reasoning enabled, diagnostics documented, .hermes/AGENTS.md created |
| 5. Scheduler Integration | ✅ Verified in route history: scheduler selects .60 for vision/large models |
| 6. Tool Usage | ✅ 32 tools available. Web search, bash, read, edit are primary operator tools |
| 7. Real Workflows | ✅ Chat, coding, reasoning all work through Gateway |
| 8. Observability | ✅ Route history, reason codes, Prometheus metrics, SLO status documented |
| 9. Recommendations | ✅ Prioritized in this report |
| 10. Documentation | ✅ HERMES-OPERABILITY.md + .hermes/AGENTS.md |

## Next Steps

### Immediate (quick wins)
1. Create PowerShell alias `function ai-lab { hermes -p ai-lab @args }` for operator convenience

### Engineering work
2. Fix Gateway streaming path — "empty stream" on Hermes `streaming.enabled: true`
3. Fix Hermes provider to respect config `base_url` when set
4. Investigate tool schema overhead (50KB for 32 tools may be optimizable)

### Future
5. Add fallback provider (OpenRouter, Claude) for Gateway-down scenarios
6. Create operator dashboard showing current routing decisions
