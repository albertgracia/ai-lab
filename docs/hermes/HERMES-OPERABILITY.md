# Hermes Operability Guide

## Overview

Hermes Agent v0.17.0 — primary operator interface for AI-LAB.

## Architecture

```
Operator → Hermes Agent (Windows 192.168.1.50)
  → AI-LAB Gateway (:8008) — routing, SLO, profiling, scheduler, fallback
    → LM Studio (192.168.1.50:1234 / 192.168.1.60:1234) — inference
```

Hermes must always use `-p ai-lab` to route through the AI-LAB Gateway. Without the profile, Hermes routes directly to LM Studio bypassing all runtime features.

## Configuration

### Active config: `C:\Users\leobc\AppData\Local\hermes\config.yaml`

| Key | Value | Notes |
|-----|-------|-------|
| `model.default` | `qwen/qwen2.5-coder-14b-instruct` | Primary coding model (active) |
| `model.provider` | `lmstudio` | OpenAI-compatible transport |
| `model.base_url` | `http://192.168.1.30:8008/v1` | AI-LAB Gateway endpoint |
| `streaming.enabled` | `false` | Gateway streaming compatibility issue (see Known Issues) |
| `display.streaming` | `true` | Display streaming enabled |
| `display.show_reasoning` | `true` | Operator diagnostics |

### AI-LAB profile: `C:\Users\leobc\AppData\Local\hermes\profiles\ai-lab\config.yaml`

Overrides `base_url` to the Gateway. Must be enabled with `-p ai-lab` flag.

## Daily Workflow

### Recommended alias
```powershell
function ai-lab { hermes -p ai-lab @args }
```

### Common commands

```powershell
# Interactive session from workspace
hermes -p ai-lab chat

# Single query
hermes -p ai-lab chat -q "status of AI-LAB"

# Coding task
hermes -p ai-lab chat -q "implement a fibonacci function in Python"

# With skills
hermes -p ai-lab chat -s "python-patterns" -q "refactor this function"
```

### Operator diagnostics

```powershell
# Gateway health
curl -s http://192.168.1.30:8008/health

# Runtime models
curl -s http://192.168.1.30:8008/v1/models

# Route history (last 5)
ssh albert@192.168.1.30 "tail -5 /opt/ai-lab/runtime/state/routing_history.jsonl"

# Prometheus metrics
curl -s http://192.168.1.30:8008/metrics | grep ailab_

# SLO status
curl -s http://192.168.1.30:8008/slo/health

# LM Studio models
curl -s http://192.168.1.50:1234/v1/models
```

## Model Routing

The Gateway handles routing automatically. The operator does NOT need to specify models.

| Capability | Gateway Decision | Nodo |
|------------|-----------------|------|
| Normal chat/coding | DNR routing → .50 | rx9070-node |
| Vision (moondream2, qwen-vl) | Capability Scheduler → .60 | rx7900xt-node |
| Large context (30b+, 35b, xl) | Capability Scheduler → .60 | rx7900xt-node |
| rx7900xt-only models | Capability Scheduler → .60 | rx7900xt-node |

### Reason codes in route history

- `scheduler_selected` → Capability Scheduler chose the node
- `capability_match_on_*` → Node matched required capability
- `model_available_on_*` → Model found on node
- `intelligent_fallback` → Fallback Engine activated after failure
- `fallback_unavailable` → No safe fallback found
- `scheduler_skip_no_capability` → Normal routing (no scheduler needed)

## Known Issues

### 1. Streaming empty stream (CRITICAL)

**Symptom:** `Provider returned an empty stream with no finish_reason`
**Cause:** Gateway streaming path has compatibility issue with Hermes agent.
**Workaround:** `streaming.enabled: false` (default).
**Fix:** Needs Gateway streaming path investigation.

### 2. AGENTS.md truncation (LOW)

**Symptom:** `Context file AGENTS.md TRUNCATED: 54640 chars exceeds limit of 31457`
**Cause:** Hermes loads `AGENTS.md` from workspace root (54K chars). Truncated to 31K.
**Impact:** Cosmetic — Gateway handles routing regardless of AGENTS.md content.
**Workaround:** Use `--ignore-rules` for isolated queries.

### 3. Base config ignores base_url (MEDIUM)

**Symptom:** Without `-p ai-lab`, Hermes routes to `192.168.1.50:1234` directly.
**Cause:** Hermes `lmstudio` provider has internal discovery that overrides config `base_url`.
**Impact:** Without `-p ai-lab`, all runtime features are bypassed.
**Workaround:** Always use `-p ai-lab`.

### 4. High latency on first query (LOW)

**Symptom:** First query takes 15-25s, subsequent queries 5-10s.
**Cause:** Hermes context initialization + Gateway warmup.
**Impact:** Acceptable for operator use.

## Tool Usage

Hermes has 32 tools available. Common tools for AI-LAB operations:

| Tool | Purpose | Used by operator |
|------|---------|-----------------|
| `bash` | Run commands (including curl diagnostics) | Frequently |
| `web_search` | Research | Occasionally |
| `read` | Read files | Frequently |
| `edit` | Edit files | Coding tasks |

## Health Checks

```bash
# Quick health
hermes -p ai-lab chat -q "check AI-LAB health"

# Runtime status via MCP
# ailab_runtime_health returns: services, nodes, GPU, models, governance
```

## Files

| File | Purpose |
|------|---------|
| `C:\Users\leobc\AppData\Local\hermes\config.yaml` | Main Hermes configuration |
| `C:\Users\leobc\AppData\Local\hermes\profiles\ai-lab\config.yaml` | AI-LAB profile (Gateway endpoint) |
| `C:\Users\leobc\AppData\Local\hermes\profiles\ai-lab\.env` | Environment overrides |
| `E:\opencode\ai-lab\.hermes\AGENTS.md` | AI-LAB operator instructions |
| `E:\opencode\ai-lab\docs\hermes\HERMES-OPERABILITY.md` | This guide |
