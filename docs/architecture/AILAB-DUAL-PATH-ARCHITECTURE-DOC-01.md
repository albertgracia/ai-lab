# AI-LAB Dual-Path Architecture

> **Source of Truth** — Documented 2026-06-16  
> **Phase:** AILAB-DUAL-PATH-ARCHITECTURE-DOC-01  
> **Status:** ACTIVE

---

## Table of Contents

1. [Architectural Overview](#1-architectural-overview)
2. [Component Description](#2-component-description)
3. [Port Map](#3-port-map)
4. [Path A: Gateway Direct](#4-path-a-gateway-direct)
5. [Path B: Router Cognitive](#5-path-b-router-cognitive)
6. [Request Flow Comparison](#6-request-flow-comparison)
7. [When to Use Each Path](#7-when-to-use-each-path)
8. [Relationship with Other Services](#8-relationship-with-other-services)
9. [Obsolete Assumptions](#9-obsolete-assumptions)
10. [Risks of Confusion](#10-risks-of-confusion)

---

## 1. Architectural Overview

AI-LAB has **two independent invocation paths** for LLM inference. They do NOT call each other. Both terminate at an LM Studio node.

```mermaid
graph TB
    subgraph "AI-LAB Server (192.168.1.30)"
        GC[("Gateway<br/>Port 8008<br/>openai_gateway.py")]
        RC[("Router<br/>Port 8083<br/>router_api.py")]
        MC[("MCP LAN Gateway<br/>Port 8084")]
        SC[("MCP Semantic Gateway<br/>Port 8092")]
        LC[("Live API<br/>Port 8091 (localhost)")]
    end

    subgraph "LM Studio Nodes"
        LS250[("LM Studio .250<br/>192.168.1.250:1234<br/>RX9070")]
        LS50[("LM Studio .50<br/>192.168.1.50:1234<br/>RX7900XT")]
    end

    subgraph "External"
        OC[("OpenCode Desktop")]
        OW[("OpenWebUI")]
    end

    OC -->|Path A| GC
    OW -->|Path A| GC
    OC -.->|Path B| RC

    GC -->|requests.post()| LS250
    GC -.->|requests.post()| LS50
    RC -->|select_node + call_lmstudio| LS250
    RC -.->|select_node + call_lmstudio| LS50

    MC -->|MCP tools| GC
    SC -->|MCP tools| GC
    LC -->|Runtime state| RC
```

### ASCII diagram

```
                           AI-LAB SERVER (192.168.1.30)
  ┌──────────────────────────────────────────────────────────────────┐
  │                                                                  │
  │  PATH A (Direct)                        PATH B (Cognitive)      │
  │  ┌──────────────┐                      ┌──────────────┐        │
  │  │  Gateway     │                      │  Router      │        │
  │  │  :8008       │                      │  :8083       │        │
  │  │  openai_     │                      │  router_api  │        │
  │  │  gateway.py  │                      │  .py         │        │
  │  └──────┬───────┘                      └──────┬───────┘        │
  │         │ requests.post()                     │ select_node()  │
  │         │                                     │ call_lmstudio()│
  │         ▼                                     ▼                │
  │  ┌──────────────────────────────────────────────────────┐      │
  │  │              LM Studio Nodes (External)              │      │
  │  │  .250:1234 (RX9070)   .50:1234 (RX7900XT - DOWN)    │      │
  │  └──────────────────────────────────────────────────────┘      │
  │                                                                  │
  │  MCP LAN Gateway (:8084) ──► Gateway (:8008)                    │
  │  MCP Semantic Gateway (:8092) ──► Gateway (:8008)               │
  │                                                                  │
  └──────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Description

### Gateway (`openai_gateway.py`)

| Property | Value |
|----------|-------|
| **File** | `runtime/gateway/openai_gateway.py` |
| **Port** | 8008 |
| **Framework** | Raw `BaseHTTPRequestHandler` + `ThreadingHTTPServer` |
| **Lines** | 5,787 |
| **PID example** | 1476 |
| **Service** | `ailab-gateway.service` |

**Responsibilities:**
- OpenAI-compatible API endpoint (primary entry point for OpenCode Desktop and OpenWebUI)
- Requests proxied directly to configured LM Studio backend via `requests.post()`
- Backend selection from `BACKENDS` list (line 625):
  ```python
  BACKENDS = [
      {"name": "rx9070", "url": "http://192.168.1.50:1234/v1", "enabled": True},
      {"name": "nas-n5", "url": "http://192.168.1.200:12345/v1", "enabled": False},
      {"name": "rx7900xt", "url": "http://192.168.1.60:1234/v1", "enabled": False},
  ]
  ```
- Rate limiting (IP-based)
- Graceful shutdown
- Metrics at `/metrics`
- **Does NOT call the Router**

### Router (`router_api.py`)

| Property | Value |
|----------|-------|
| **File** | `runtime/llm/router_api.py` |
| **Port** | 8083 |
| **Framework** | FastAPI via uvicorn |
| **Lines** | 1,303+ |
| **PID example** | 1512 |
| **Service** | `ailab-router.service` |

**Responsibilities:**
- Cognitive routing engine (intent-based route classification)
- OpenAI-compatible `/v1/chat/completions` and `/chat/completions` endpoints
- Model selection via `select_node()` in `model_router.py`
- LLM invocation via `call_lmstudio()` in `invoke.py`
- Route families: auto, fast, reasoning, coding
- Metrics at `/metrics`
- Memory search, incident search, runtime recall endpoints
- **Does NOT call the Gateway**

### MCP LAN Gateway

| Property | Value |
|----------|-------|
| **Port** | 8084 |
| **Framework** | Python |
| **Service** | `ailab-mcp-lan-gateway.service` |

**Responsibilities:**
- MCP tools exposed over LAN (read-only, token-auth)
- Consumes Gateway (8008) internally
- Provides `ailab_status`, `ailab_runtime_health`, `ailab_route_preview`, etc.

### MCP Semantic Gateway

| Property | Value |
|----------|-------|
| **Port** | 8092 |
| **Framework** | Python |
| **Service** | `ailab-mcp-semantic-gateway.service` |

**Responsibilities:**
- Modular MCP tools (semantic analysis, cognitive metrics)
- Consumes Gateway (8008) internally
- Legacy duplication of 3 tools from runtime-mcp (documented as LEGACY)

### Live API

| Property | Value |
|----------|-------|
| **Port** | 8091 (localhost only) |
| **Service** | `ailab-live-api.service` |

**Responsibilities:**
- Internal runtime state API
- Localhost only — not exposed externally

---

## 3. Port Map

| Port | Service | Process | Framework | Status |
|------|---------|---------|-----------|--------|
| 8008 | Gateway | python | BaseHTTPRequestHandler | OK |
| 8083 | Router | uvicorn | FastAPI | OK (4 route models) |
| 8084 | MCP LAN Gateway | python | Custom | OK |
| 8091 | Live API (internal) | python | Custom | OK (localhost) |
| 8092 | MCP Semantic Gateway | python | Custom | OK |
| 3010 | Metrics Dashboard | next-server | Next.js SSR | OK |
| 4322 | (node process) | node | — | OK |
| 4747 | (node process) | node | — | OK |
| 6333 | Qdrant HTTP | qdrant | — | OK |
| 6334 | Qdrant gRPC | qdrant | — | OK |
| 80/443 | Traefik | traefik | Reverse proxy | OK |
| 9090 | Prometheus | prometheus | — | External (192.168.1.40) |
| 3000 | Grafana | grafana | — | External (192.168.1.40) |

### LM Studio Nodes

| Node | Address | Status | Models |
|------|---------|--------|--------|
| RX9070 (primary) | 192.168.1.250:1234 | OK | 3 (1 LLM + 2 embeddings) |
| RX7900XT (secondary) | 192.168.1.50:1234 | DOWN | N/A |
| NAS-N5 (inactive) | 192.168.1.200:12345 | Disabled | N/A |

---

## 4. Path A: Gateway Direct

**This is the primary path used by OpenCode Desktop and OpenWebUI.**

### Flow

```
External Client
  └── HTTP request to :8008
        └── GatewayHandler.do_GET() / do_POST()
              ├── check_rate_limit()
              ├── detect_intent()
              ├── classify_chat_route()
              ├── select_node() (from model_router.py)
              └── requests.post(f"{backend_url}/chat/completions")
                    └── LM Studio node (external HTTP)
```

### Key characteristics

- **No middleware framework** — raw Python HTTP server
- **No Router interaction** — Gateway is self-contained
- **Backend is configured** via `BACKENDS` list in source code
- **Rate limiting** is inline, not middleware
- **Metrics** served at `/metrics` (Prometheus format)
- **Health** at `/health`
- **Direct streaming** support

### Source code entry point

```python
# runtime/gateway/openai_gateway.py:5711
def run():
    server = GracefulThreadingHTTPServer((HOST, PORT), GatewayHandler)
    # PORT = 8008 (line 622)
```

---

## 5. Path B: Router Cognitive

**This is the secondary path, used for cognitive routing and intent-based model selection.**

### Flow

```
External Client
  └── HTTP request to :8083
        └── FastAPI router
              └── chat_completions() @ /v1/chat/completions
                    ├── detect_intent()
                    ├── classify_chat_route()
                    ├── select_node() (from model_router.py)
                    │     ├── discover_all_models()
                    │     ├── infer_task()
                    │     ├── get_model_metadata()
                    │     └── merge_registry_with_discovery()
                    └── route_prompt()
                          └── call_lmstudio() (in invoke.py)
                                └── requests.post(f"http://{host}:{port}/v1/chat/completions")
                                      └── LM Studio node (external HTTP)
```

### Key characteristics

- **FastAPI framework** — standard ASGI application
- **Cognitive routing** — classifies intent before model selection
- **Intent-aware** — uses `detect_intent()` from `intent_router.py`
- **Route families**: auto, fast, reasoning, coding
- **Node selection** — `select_node()` picks best LM Studio node based on:
  - Live model discovery
  - Model registry
  - Task inference
  - VRAM estimation
  - Capability matching
- **Independent from Gateway** — has its own models endpoint, metrics, and health

### Routes served by Router

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Root (service info) |
| `/health` | GET | Health check |
| `/v1/models` | GET | Available models |
| `/v1/chat/completions` | POST | Chat completion |
| `/chat/completions` | POST | Chat completion (alias) |
| `/metrics` | GET | Prometheus metrics |
| `/runtime/entities/*` | GET | Entity registry |
| `/runtime/reporting/*` | GET | Operational reports |
| `/api/memory/*` | GET/POST | Memory operations |
| `/api/incidents/*` | GET | Incident analytics |
| `/agentic/*` | GET | Agentic execution state |
| *(49 routes total)* | | |

---

## 6. Request Flow Comparison

| Aspect | Path A (Gateway :8008) | Path B (Router :8083) |
|--------|----------------------|----------------------|
| **Framework** | BaseHTTPRequestHandler | FastAPI/uvicorn |
| **Middleware** | None (inline checks) | None (no Depends) |
| **Backend selection** | Static BACKENDS list | Dynamic select_node() |
| **Intent classification** | Basic | Cognitive routing |
| **Node failover** | None (single backend) | Multi-node selection |
| **Streaming** | Yes | Yes |
| **Rate limiting** | Yes (inline) | No |
| **Graceful shutdown** | Yes | No (systemd restart) |
| **OpenAI compatibility** | Yes | Yes |
| **Metrics** | Yes (/metrics) | Yes (/metrics) |
| **Consumed by** | OpenCode Desktop, OpenWebUI | Direct API calls |
| **MCP relation** | Consumed by MCP Gateways | Not consumed by MCP |
| **Documented** | Contract only (39A) | Partially (Phase 5) |

**Same gap in both paths:** Both use `requests.post()` with dynamically constructed URLs to external LM Studio nodes. This is an inherent limitation — GitNexus cannot track calls outside the indexed codebase.

---

## 7. When to Use Each Path

### Use Gateway (:8008) when

- You are an **external client** (OpenCode Desktop, OpenWebUI)
- You need **OpenAI-compatible API**
- You want **direct LM Studio access** without cognitive routing
- You need **rate limiting** and **graceful shutdown**
- You do NOT need intent-based route classification

### Use Router (:8083) when

- You need **cognitive routing** (intent → model selection)
- You want **multi-node failover** with dynamic node selection
- You need **route families** (auto, fast, reasoning, coding)
- You access **runtime APIs** (entities, incidents, memory, reporting)
- You want **model registry-aware** selection

### Both paths work independently

- They can be used simultaneously
- They do NOT share state
- Both serve the same LM Studio nodes
- Both have OpenAI-compatible chat completion endpoints

---

## 8. Relationship with Other Services

### MCP Tools

The MCP runtime (`mcp/runtime-mcp/`) exposes 8 tools via the MCP LAN Gateway (:8084):
- `ailab_status`, `ailab_runtime_health`, `ailab_health_latency`
- `ailab_incidents_active`, `ailab_operator_summary`
- `ailab_route_preview`, `ailab_memory_search`, `ailab_slo_status`

These tools *consume* the Gateway (:8008) internally. They do NOT use the Router (:8083).

### OpenCode Desktop

OpenCode Desktop connects to **Gateway (:8008)** via the `opencode.json` MCP configuration:
```json
{
  "mcpServers": {
    "ailab-runtime": {
      "url": "http://192.168.1.30:8084"
    }
  }
}
```
OpenCode → MCP LAN Gateway (:8084) → Gateway (:8008) → LM Studio

### OpenWebUI

OpenWebUI connects to **Gateway (:8008)** as an OpenAI-compatible endpoint:
```
OpenWebUI → Gateway (:8008) → LM Studio
```

### Traefik

Traefik (ports 80/443) acts as a reverse proxy. It may route to Gateway (:8008) or other services depending on configuration.

---

## 9. Obsolete Assumptions

This section documents assumptions that have been proven incorrect during the GitNexus graph quality audit (2026-06-16).

### Assumption 1: Router listens on port 8001

| Field | Value |
|-------|-------|
| **Assumption** | The Router API listens on port 8001 |
| **Reality** | The Router listens on port **8083** |
| **Source** | Initial GitNexus health check (T4a) used port 8001 |
| **Correction date** | 2026-06-16 |
| **Related documents** | `reports/T5-PORTS-CONFIRMATION-01.md` |

### Assumption 2: Gateway → Router → LM Studio (single chain)

| Field | Value |
|-------|-------|
| **Assumption** | The Gateway forwards requests to the Router, which forwards to LM Studio |
| **Reality** | **Two independent paths.** Gateway and Router are separate entry points that do NOT call each other. Both call LM Studio independently. |
| **Source** | Implicit architectural expectation during GitNexus audit |
| **Correction date** | 2026-06-16 |
| **Related documents** | This document; `reports/T5-PORTS-CONFIRMATION-01.md` |

### Assumption 3: Gateway uses middleware framework

| Field | Value |
|-------|-------|
| **Assumption** | The Gateway uses middleware (Flask/FastAPI middleware chain) |
| **Reality** | The Gateway uses raw `BaseHTTPRequestHandler`. No middleware framework exists. Rate limiting and shutdown guards are inline checks. |
| **Source** | G5 middleware audit expectation |
| **Correction date** | 2026-06-16 |
| **Related documents** | `reports/G5-MIDDLEWARE-GAP-AUDIT-01.md` |

### Assumption 4: Router is the primary inference endpoint

| Field | Value |
|-------|-------|
| **Assumption** | The Router is the main entry point for LLM inference |
| **Reality** | The **Gateway** is the primary entry point for OpenCode and OpenWebUI. The Router is a secondary, specialized endpoint for cognitive routing. |
| **Source** | ARCHITECTURE.md only described Router path; Gateway was not documented |
| **Correction date** | 2026-06-16 |
| **Related documents** | This document |

---

## 10. Risks of Confusion

### Risk 1: Dual maintenance burden

Both paths have independent LM Studio invocation code. A bug fix in one (`call_lmstudio`) may not apply to the other (Gateway's direct `requests.post`). Any change to the LM Studio API contract must be verified against both paths.

### Risk 2: Undocumented Gateway

The Gateway (port 8008) is the **primary entry point** used by OpenCode Desktop and OpenWebUI, yet it was previously undocumented in ARCHITECTURE.md. This gap is now closed.

### Risk 3: Router health ≠ Gateway health

One path can be down while the other is healthy. Monitoring must check both independently. The Gateway health endpoint reports only its own status and backend reachability.

### Risk 4: Port confusion

Three different services expose OpenAI-compatible endpoints:
- Gateway: `:8008` — production, used by OpenCode
- Router: `:8083` — cognitive routing
- LM Studio: `:1234` — raw LM Studio (if accessed directly)

External clients should use **Gateway (:8008)** unless they specifically need cognitive routing features.

---

## Appendix A: Service Units (systemd)

| Service | Unit File |
|---------|-----------|
| Gateway | `ailab-gateway.service` |
| Router | `ailab-router.service` |
| MCP LAN Gateway | `ailab-mcp-lan-gateway.service` |
| MCP Semantic Gateway | `ailab-mcp-semantic-gateway.service` |
| Metrics Dashboard | `ailab-metrics.service` |
| Docs Portal | `ailab-docs.service` |
| Live API | `ailab-live-api.service` |
| Live State | `ailab-live-state.service` |
| Heartbeat | `ailab-heartbeat.service` |
| GitNexus | `gitnexus.service` |
| Traefik | `ailab-traefik.service` |
| Runner | `ailab-runner.service` |

## Appendix B: Source Files

| Component | File | Port |
|-----------|------|------|
| Gateway | `runtime/gateway/openai_gateway.py` | 8008 |
| Router | `runtime/llm/router_api.py` | 8083 |
| Model Router | `runtime/llm/model_router.py` | — |
| LM Studio Invoke | `runtime/llm/invoke.py` | — |
| MCP LAN | `mcp/runtime-mcp/server/lan_server.py` | 8084 |
| MCP Semantic | `mcp/runtime-mcp/server/server.py` | 8092 |
| MCP Tools | `mcp/runtime-mcp/tools/__init__.py` | — |

## Appendix C: Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-06-16 | GitNexus Audit | Initial documentation of dual-path architecture |
