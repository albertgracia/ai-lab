# AI-LAB Architecture

## 1. Overview

AI-LAB is a local LLM inference gateway and cognitive routing system deployed across a home-lab cluster. It exposes OpenAI-compatible chat completion APIs through two independent invocation paths — a lightweight direct gateway for production traffic and a cognitive router for intent-based model selection — backed by LM Studio on a dedicated GPU node. The stack includes a memory system (Qdrant), a full observability suite (Prometheus/Grafana/Loki), an MCP tool layer for agentic integration, and a set of runtime governance and maturity endpoints for operational control.

## 2. Dual-Path Architecture

AI-LAB has two independent invocation paths. They do **not** call each other.

### Path A: Gateway Direct — `:8008`

| Property | Value |
|----------|-------|
| File | `runtime/gateway/openai_gateway.py` |
| Framework | Raw `BaseHTTPRequestHandler` + `ThreadingHTTPServer` |
| Endpoint | `POST /v1/chat/completions` (OpenAI-compatible) |
| Backend selection | Static from `BACKENDS` list |
| Route classification | Heuristic in `tool_request_classifier.py` (48 greeting markers, QWEN_ESCAPALATION_REASONS) |
| Profile application | `apply_profile()` loads cognitive profile from `runtime/profiles/*.json` |
| SLO enforcement | `RuntimeSLOManager`, `DegradationManager`, `AdaptiveConcurrency` in `runtime/slo/` |
| Streaming | Real SSE relay from LM Studio (`relay_stream()`) |
| Memory injection | Controlled by `AI_LAB_ENABLE_MEMORY_INJECTOR` flag |
| Rate limiting | Graceful shutdown, PID lock singleton (`process_guard.py`) |

**This is the primary path used by OpenCode Desktop and OpenWebUI.** All production chat traffic flows through the gateway.

### Path B: Router Cognitive — `:8083`

| Property | Value |
|----------|-------|
| File | `runtime/llm/router_api.py` |
| Framework | FastAPI via uvicorn |
| Endpoint | `POST /v1/chat/completions` (legacy, receives **zero** production traffic) |
| Model selection | Dynamic via `select_node()` in `model_router.py` |
| Cognitive routing | Classifies intent before model selection |
| Route families | `auto`, `fast`, `reasoning`, `coding` |
| Port guard | Refuses to start on `:8008` |

**The router does not process chat traffic in production.** Its internal API endpoints (`/status`, `/profiles`, `/replay`) are used for observability and tooling.

## 3. Services

All services run on `192.168.1.30` unless otherwise noted.

| Service | Port | Process | Purpose |
|---------|------|---------|---------|
| `ailab-gateway` | 8008 | `openai_gateway.py` | Primary chat entrypoint, OpenAI-compatible API |
| `ailab-router` | 8083 | `router_api.py` (uvicorn) | Internal API (status, profiles, replay) |
| `ailab-live-api` | 8084 | `live_api.py` | State API, embeddings |
| `ailab-docs` | 4322 | Astro preview | Documentation site |
| `ailab-metrics` | 3010 | Next.js SSR | Public dashboard (`metricas.labrazahome.com`) |
| `ailab-heartbeat` | — | Heartbeat process | Cluster liveness |
| `ailab-live-state` | — | State snapshot process | Periodic runtime state snapshot |
| `ailab-runner` | — | GitHub Actions Runner | CI/CD pipeline |
| `ailab-traefik` | 80/443 | Traefik proxy | Reverse proxy, TLS termination |

### Request Flow (Path A — Production)

```
Client (OpenCode / OpenWebUI)
  → ailab-gateway :8008 → POST /v1/chat/completions
    → inject_agent_context()
    → classify_chat_route() → family + variant
    → apply_profile() → model, tokens, temperature
    → SLO degradation check → forced llama / qwen protection
    → memory injection (if enabled + policy allows)
    → quality/hallucination scoring (post-response)
    → LM Studio (192.168.1.50:1234)
    → SLO state evaluation → adaptive concurrency → circuit breaker update
    → response to client
```

## 4. MCP Layer

| Component | Port | Status |
|-----------|------|--------|
| MCP LAN Gateway | 8084 | **Active** — exposes 8 read-only MCP tools (status, health, route preview, operator summary, incidents, SLO, latency, memory search) |
| MCP Semantic Gateway | 8092 | **Deprecated** (legacy, systemd service `ailab-mcp-semantic-gateway.service`) |

**Active MCP server location:** `/mnt/mcp_server/` (outside repo)
**Snapshot in repo:** `mcp/runtime-mcp/`

The LAN Gateway consumes the Gateway (`:8008`) and exposes operations to MCP clients (OpenCode, Cursor, Claude Desktop). Token-auth required for all tools.

### MCP Tools (LAN Gateway — `:8084`)

| Tool | Description |
|------|-------------|
| `ailab_status` | Gateway + Router health check |
| `ailab_runtime_health` | Detailed runtime health summary |
| `ailab_route_preview` | Heuristic route classification (no LLM) |
| `ailab_operator_summary` | NOC-ready operator summary |
| `ailab_incidents_active` | Active incident intelligence |
| `ailab_slo_status` | SLO health + violations |
| `ailab_health_latency` | Latency stats + health score |
| `ailab_memory_search` | Semantic search across Qdrant collections |

## 5. Inference Backend

### LM Studio Node

| Property | Value |
|----------|-------|
| Host | `192.168.1.50` |
| Port | `:1234` |
| Version | llama.cpp v2.14.0 |
| GPU | RX9070 (16 GB VRAM) |
| Platform | Windows |
| Backend | Vulkan / ROCm |

### CPU Nodes

| Node | IP | Role | Status |
|------|-----|------|--------|
| RX9070 | 192.168.1.50 | Primary inference backend | **ONLINE** |
| RX7900XT | 192.168.1.60 | Secondary inventory | **OFFLINE** (node powered off) |
| NAS-N5 | 192.168.1.250 | Storage + secondary LM Studio | **Available** (failover) |

### Model Set (Active)

| Model | Role | Routable | Status |
|-------|------|----------|--------|
| `llama-3.1-8b-instruct` | Primary operational (minimal, greetings, light prompts) | **PRIMARY_OPERATIONAL_MODEL** | Active |
| `qwen2.5-coder-14b-instruct` | Primary coding (coding, report, architecture, reasoning) | **PRIMARY_CODING_MODEL** | Active |
| `nomic-embed-text-v1.5` | Embeddings (semantic recall) | Embedding only | Active |
| `lmstudio-community/qwen2.5-coder-14b-instruct` | Legacy identifier | **NON_ROUTABLE** | Deprecated |
| `qwen3.6-27b` | Inventory only | **DESACTIVADO** | Available for manual tests |
| `qwen2.5-coder-32b` | Inventory only | **DOWN** | Node RX7900XT offline |

### Model State Semantics

- **Loaded**: Listed by LM Studio (does not imply active)
- **Active**: Received real traffic within `ACTIVE_WINDOW_SECONDS`
- **Discoverable**: Visible in inventory scans, not routable for production
- **Disabled**: Explicitly deactivated by runtime config, always reported as DISABLED even if LM Studio lists it
- **Non-routable**: Legacy identifiers not used in production routing

## 6. Memory System

| Component | Detail |
|-----------|--------|
| Vector store | Qdrant on `192.168.1.30:6333` (HTTP) / `6334` (gRPC) |
| Collections | `routing_history`, `incidents`, `cognitive_history` |
| Feature flag | `AI_LAB_ENABLE_MEMORY_INJECTOR` (default: `false`) |

### Memory Policies

| Policy | Max Items | Max Chars | Collections | Min Score | Used By |
|--------|-----------|-----------|-------------|-----------|---------|
| `minimal` | 0 (disabled) | 0 | — | — | `observe` |
| `light` | 1 | 800 | `incidents` | 0.6 | `chat`, `coding`, `report` |
| `full` | 5 | 4000 | `routing_history`, `incidents`, `cognitive_history` | 0.45 | `analysis`, `agent` |

Memory manifests are defined in `runtime/policies/memory/manifest_memory.json`. Quality gate (`runtime/skip/memory_skip_guard.py`) prevents contamination with 8 skip reasons.

## 7. Observability

The observability stack runs on `192.168.1.40`.

| Component | Port | Role |
|-----------|------|------|
| Prometheus | 9090 | **Source of truth** — TSDB, scraping, alerting |
| Grafana | 3000 | Visualization layer — 15 dashboards, 19 alert rules |
| Loki | — | Log aggregation |

### Prometheus Configuration

- Config: `/home/albert/docker/monitorizacion/prometheus/prometheus.yml`
- Alert rules: `/home/albert/docker/monitorizacion/prometheus/config/rules/ai-lab-route-family-alerts.yml`
- Grafana provisioning: `/home/albert/docker/monitorizacion/grafana/provisioning/`

### Scrape Targets

| Target | Endpoint | Labels |
|--------|----------|--------|
| `ai-lab-gateway` | `192.168.1.30:8008/metrics` | `role=gateway` |
| `ai-lab-router` | `192.168.1.30:8083/metrics` | `role=router` |
| `ai-lab-live-api` | `192.168.1.30:8084/metrics` | `role=live-api` |
| `ai-lab-cadvisor` | `192.168.1.30:8081` | Container metrics |
| `ai-lab-node` | `192.168.1.30:9100` | Host (node_exporter) |
| `ai-lab-gpu-rx9070` | `192.168.1.50:9182` | GPU RX9070 |
| `ai-lab-gpu-metrics` | `192.168.1.50:9183` | GPU compute |
| `ai-lab-gpu-rx7900xt` | `192.168.1.60:9182` | **DOWN** — node offline |
| `ai-lab-gpu-metrics` | `192.168.1.60:9183` | **DOWN** — node offline |
| `cloudflare-tunnel` | `cloudflare-tunnel:2000` | Tunnel metrics |

### Key Metrics Categories

- **Profiles and routing**: `ailab_profile_total`, `ailab_route_family_total`, `ailab_greeting_fastpath_total`, `ailab_qwen_escalation_total`
- **Latency**: `ailab_first_token_latency_ms` (TTFB), `ailab_request_total_latency_ms`, `ailab_completion_stream_duration_ms`
- **Tools**: `ailab_tool_call_total`, `ailab_tool_empty_arguments_total`, `ailab_tool_fastpath_total`
- **Memory**: `ailab_memory_recall_total`, `ailab_memory_quality_score`, `ailab_memory_contamination_risk`
- **Quality**: `ailab_quality_score`, `ailab_hallucination_risk`
- **Streaming**: `ailab_stream_chunks_total`, `ailab_stream_stalls_total`, `ailab_stream_finish_inconsistent_total`
- **GPU**: `ailab_gpu_active_requests`, `ailab_gpu_estimated_utilization_pct`
- **SLO**: `ailab_runtime_slo_state`, `ailab_runtime_degradation_level`, `ailab_runtime_timeout_rate`, `ailab_slo_violations_total`, `ailab_circuit_breaker_state`
- **Report grounding**: `ailab_report_grounding_total`, `ailab_report_missing_fields_total`, `ailab_report_ungrounded_total`
- **Precision**: `ailab_operational_precision_score`, `ailab_confidence_integrity_score`, `ailab_authority_conflicts_total`

**Important:** Only the gateway (`:8008`) receives chat traffic and increments counters. Router (`:8083`) and live-api (`:8084`) register identical metric families but never increment them. Grafana queries must target the gateway's series.

### Grafana Dashboards (TIER 1)

- Latency, profiles, tools, errors, GPU, tokens (daily operations)
- Memory, streaming, quality, cold starts, checksums (troubleshooting)
- AI-LAB Runtime Protection (SLO enforcement, 14 panels)
- All dashboards in `AI-LAB` folder, datasource UID `PBFA97CFB590B2093`

### Alert Rules (19 active)

All currently `health=ok`. Covers: route regression, tool fastpath leakage, cognitive explosion, errors, governance, memory fallback, contamination, budget, cold starts, dominance, context caps. Red alerts (STOP burn-in) include tool fastpath leakage, governance unexpected blocks, empty responses, memory recall in minimal mode, stream stalls, and finish inconsistency.

## 8. Governance

### Governance Levels

| State | Resolved To | Description |
|-------|-------------|-------------|
| `NORMAL` | `ENFORCED` | Full enforcement active |
| `ELEVATED` | `ENFORCED` | Full enforcement active |
| `DEGRADED` | `DEGRADED` | Reduced capacity |
| `LOCKDOWN` | `LOCKDOWN` | Minimum viable operation |

Level is resolved dynamically from `control_plane.get_governance_state()`. **Never hardcoded.** The endpoint `/runtime/governance` always responds with `200 OK`, annotated with `source` (`control_plane` | `fallback`) to distinguish real data from fallback.

### Failure Domains

| Node | Failure Domain | Impact When Down |
|------|---------------|------------------|
| Control plane (192.168.1.30) | `control-plane` | Blocks all cognitive routing |
| RX9070 (192.168.1.50) | `inference-gpu` | Blocks requests requiring that GPU |
| RX7900XT (192.168.1.60) | `inference-gpu` | No impact (already offline) |
| Observability (192.168.1.40) | `observability` | No impact on cognitive plane |
| NAS-N5 (192.168.1.250) | `storage` | Episodic memory and replay only |

## 9. API Endpoints

| Endpoint | Port | Service | Always 200? | Description |
|----------|------|---------|-------------|-------------|
| `GET /health` | 8008 | Gateway | Yes | Gateway health |
| `POST /v1/chat/completions` | 8008 | Gateway | — | Chat completion (OpenAI format) |
| `GET /metrics` | 8008 | Gateway | Yes | Prometheus metrics |
| `GET /slo/health` | 8008 | Gateway | Yes | SLO status + violations |
| `GET /runtime/maturity` | 8008 | Gateway | Yes | Runtime descriptor (`build_runtime_descriptor()`) |
| `GET /runtime/precision` | 8008 | Gateway | Yes | Precision engine status |
| `GET /runtime/precision/confidence` | 8008 | Gateway | Yes | Confidence aggregation |
| `GET /runtime/precision/evidence` | 8008 | Gateway | Yes | Evidence classification |
| `GET /runtime/precision/conflicts` | 8008 | Gateway | Yes | Authority conflicts |
| `GET /runtime/precision/partial` | 8008 | Gateway | Yes | Partial state tracking |
| `GET /runtime/precision/discoverable` | 8008 | Gateway | Yes | Discoverable-only models |
| `GET /runtime/precision/score` | 8008 | Gateway | Yes | Precision score |
| `GET /runtime/governance` | 8008 | Gateway | Yes | Governance state |
| `GET /runtime/topology` | 8008 | Gateway | Yes | Topology (works with inference offline) |
| `GET /health` | 8083 | Router | Yes | Router health (no chat traffic) |
| `GET /status` | 8083 | Router | Yes | Router status |
| `POST /v1/chat/completions` | 8083 | Router | — | Legacy (zero production traffic) |
| `GET /metrics` | 8083 | Router | Yes | Prometheus metrics (flatlined) |
| `GET /health` | 8084 | Live API | Yes | Live API health |
| `GET /metrics` | 8084 | Live API | Yes | Prometheus metrics (flatlined) |

### OpenAPI Specification

- `extra/openapi.yaml` — documents the Gateway's `POST /v1/chat/completions`

## 10. Runtime Maturity Endpoints

All endpoints return `200 OK` even when the underlying feature is disabled or the control plane is unavailable. Payload distinguishes active, passive, and fallback states.

| Endpoint | Purpose | Module |
|----------|---------|--------|
| `/runtime/maturity` | Full runtime descriptor (models, state, slo, governance, topology, precision) | `runtime/state/runtime_maturity.py` |
| `/runtime/precision` | Precision engine root status | `runtime/precision/` |
| `/runtime/precision/confidence` | Confidence aggregation (operational, authority, observability, routing, incidents, codebase) | `runtime/precision/engine.py` |
| `/runtime/precision/evidence` | Evidence classification (authority-backed, operational, discoverable-only, stale, degraded) | `runtime/precision/evidence_classifier.py` |
| `/runtime/precision/conflicts` | Authority conflicts between evidence sources | `runtime/precision/conflict_handler.py` |
| `/runtime/precision/partial` | Partial / ambiguous evidence tracking | `runtime/precision/partial_handler.py` |
| `/runtime/precision/discoverable` | Models that are discoverable but not routable | `runtime/precision/discoverable_handler.py` |
| `/runtime/precision/score` | Operational precision score | `runtime/precision/scorer.py` |
| `/runtime/governance` | Governance registry (levels, failure domains, source annotation) | `runtime/state/governance_registry.py` |
| `/runtime/topology` | Topology (node roles + failure domains) | `runtime/state/topology.py` |
| `/slo/health` | SLO health (GREEN/YELLOW/RED, degradation level, violations) | `runtime/slo/slo_health.py` |

---

### Phase Architecture

The runtime is organized as numbered phases tracked via git tags (`CP-21B-STABLE` through `CP-36B-RUNTIME-PRECISION-MODE-STABLE`). Each phase is documented with audit files in `docs/audits/`. Phase closures require tests, build validation, operational proof, documental impact review, and a signed git tag.

### GitNexus

The codebase is indexed by GitNexus — a knowledge graph of 26728 symbols, 42257 relationships, and 300 execution flows. Run `npx gitnexus analyze` to refresh the index. Use `gitnexus_query`, `gitnexus_impact`, and `gitnexus_context` tools before modifying code to understand blast radius.
