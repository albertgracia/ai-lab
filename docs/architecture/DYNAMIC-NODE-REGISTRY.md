# Dynamic Node Registry

## Purpose

Live runtime inventory of compute nodes. Distinguishes required baseline nodes from optional on-demand nodes. The registry is consumed by future routing, fallback, and scheduler logic — it does NOT make routing decisions.

## Node Classification

| Node | IP | Role | Policy | Offline = Failure? |
|------|-----|------|--------|--------------------|
| NAS-N5 | 192.168.1.250 | baseline | required | ✅ YES |
| RX9070 | 192.168.1.50 | on_demand | optional | ❌ NO |
| RX7900XT | 192.168.1.60 | on_demand | optional | ❌ NO |

### Baseline (required)

Always-on infrastructure. Offline = critical incident.

### On-Demand (optional)

Started dynamically. Offline = informational. Must NOT degrade system health.

## Schema

### NodeRegistryEntry

| Field | Type | Description |
|-------|------|-------------|
| `node_id` | str | Unique identifier |
| `hostname` | str | Human-readable name |
| `ip` | str | IP address |
| `role` | baseline / on_demand / burst / storage / control_plane | Node role |
| `status` | online / offline / degraded / unknown | Current state |
| `availability_policy` | required / optional / burst | Infra criticality |
| `capabilities` | list[str] | Inferred from model inventory |
| `models` | list[NodeModel] | Loaded LM Studio models |
| `metrics` | NodeMetrics | Latency, health, GPU data |
| `routing_eligible` | bool | Eligible for traffic |
| `fallback_eligible` | bool | Eligible for failover |
| `offline_is_failure` | bool | Whether offline = critical |
| `last_seen` | float | Unix timestamp |
| `evidence` | list[str] | Sources confirming state |

### NodeModel

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Model ID from LM Studio |
| `backend_id` | str | Inference backend (lmstudio) |
| `context` | int | Context window |
| `loaded` | bool | Currently loaded in VRAM |
| `node` | str | Hosting node |
| `suitability` | list[str] | Task types this model fits |

### NodeMetrics

| Field | Type | Description |
|-------|------|-------------|
| `latency_ms` | float or null | RTT to LM Studio |
| `health_score` | float | 0.0-1.0 |
| `gpu_utilization` | float or null | GPU % |
| `vram_total_gib` | float or null | Total VRAM in GiB |
| `vram_used_gib` | float or null | Used VRAM in GiB |
| `scrape_health` | str | Prometheus scrape status |

## Data Sources

| Source | What it provides |
|--------|-----------------|
| LM Studio `/v1/models` | Model inventory + latency + online status |
| GPU exporter `:9182/metrics` | VRAM usage |
| Prometheus `/api/v1/targets` | Scrape health per target |
| Node definitions (static) | Identity, role, policy |

## Rules

1. **Required baseline offline = critical**. System health is affected.
2. **Optional node offline = informational**. No system degradation.
3. **Online node with models = routing_eligible**. Even if role is "on_demand".
4. **Online node without required model = not eligible** for that capability.
5. **Role label ≠ operational state**. A node with role "inventory-offline" but operational online=true is treated as online.

## Live API

| Endpoint | Description |
|----------|-------------|
| `GET /api/nodes/registry` | Full registry with all nodes |
| `GET /api/nodes/capabilities` | Capability matrix (online eligible nodes only) |
| `GET /api/nodes/eligible?capability=vision&capability=reasoning` | Filtered eligible nodes |

## Module

`runtime/state/dynamic_node_registry.py`

### Pure Functions

| Function | Returns | Description |
|----------|---------|-------------|
| `build_node_registry()` | list[NodeRegistryEntry] | Live registry from all sources |
| `collect_lmstudio_models(node_def)` | list[NodeModel] | Models from LM Studio |
| `collect_prometheus_node_state()` | dict | Prometheus target health |
| `classify_node_availability(node_def)` | str | required/optional/burst |
| `build_capability_matrix(entries)` | dict[node_id] → list[capabilities] | Matrix of online eligible nodes |
| `select_eligible_nodes(entries, requirements)` | list[NodeRegistryEntry] | Filtered by capability requirements |

## Current Live State

As of 2026-07-01:

| Node | Status | Models | Capabilities | Routing Eligible |
|------|--------|--------|-------------|-----------------|
| NAS-N5 (.250) | **offline** | 0 | (none) | ❌ |
| RX9070 (.50) | **online** | 6 | chat, coding, embeddings, fast, reasoning | ✅ |
| RX7900XT (.60) | **online** | 11 | chat, coding, embeddings, fast, large-context, multimodal, reasoning, vision | ✅ |

Two operational GPU nodes are available. The primary blocker for Multi-GPU scheduling is no longer infrastructure — it's routing (100% of traffic → .50).

## Contract Version

`DYNAMIC-NODE-REGISTRY-01`
