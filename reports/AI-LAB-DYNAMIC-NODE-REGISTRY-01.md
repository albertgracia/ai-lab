# AI-LAB Dynamic Node Registry Report

**Phase:** AI-LAB-DYNAMIC-NODE-REGISTRY-01
**Date:** 2026-07-01
**Status:** COMPLETE

---

## Summary

Implemented the Dynamic Node Registry — a live runtime inventory that distinguishes required baseline nodes from optional on-demand nodes. Three nodes defined: NAS-N5 (baseline/required), RX9070 (on_demand/optional), RX7900XT (on_demand/optional). All live-validated against LM Studio, GPU exporters, and Prometheus.

## Deliverables

| Deliverable | File | Status |
|-------------|------|--------|
| Registry module | `runtime/state/dynamic_node_registry.py` | ✅ 180 lines |
| Live API endpoints | `runtime/state/live_api.py` | ✅ 3 new endpoints |
| Tests | `tests/test_dynamic_node_registry_01.py` | ✅ 38/38 PASS |
| Documentation | `docs/architecture/DYNAMIC-NODE-REGISTRY.md` | ✅ Created |

## Live API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/nodes/registry` | Full registry (all nodes, status, models, metrics) |
| `GET /api/nodes/capabilities` | Capability matrix (online eligible nodes only) |
| `GET /api/nodes/eligible?capability=vision` | Filtered eligible nodes |

## Live Validation Results

| Node | Status | Models | Latency | GPU Exporter |
|------|--------|--------|---------|-------------|
| 192.168.1.250 (NAS-N5) | **offline** | 0 | timeout | ✅ (windows_exporter) |
| 192.168.1.50 (RX9070) | **online** | 6 | 2.54ms | ✅ |
| 192.168.1.60 (RX7900XT) | **online** | 11 | 2.19ms | ✅ |

## Key Design Decisions

1. **Baseline vs on-demand separation** — offline optional nodes do NOT degrade system health
2. **Live discovery** — every request re-checks LM Studio and GPU exporters (no stale cache)
3. **Role-independent status** — operational state overrides semantic role labels (e.g., "inventory-offline" role with online=true → treated as online)
4. **Evidence tracking** — each node carries `evidence[]` explaining how its state was determined
5. **GPU exporter redundancy** — Prometheus cross-check for scrape health

## Existing Infrastructure Preserved

| Component | Status |
|-----------|--------|
| `/api/control/nodes` | ✅ Unchanged |
| SLO health | ✅ 0 violations, healthy |
| Runtime health | ✅ 89.6, redundancy_ok |
| Governance | ✅ NORMAL |
| Prometheus targets | ✅ All UP |
| All prior tests | ✅ 117/117 + 38 new = 155/155 PASS |

## Success Criteria

| Criterion | Status |
|-----------|--------|
| AI-LAB distinguishes required baseline from optional on-demand | ✅ PASS |
| Offline optional nodes do not degrade the whole system | ✅ PASS |
| Online .50/.60 nodes become eligible compute capacity | ✅ PASS |
| Future scheduler has a reliable live registry to consume | ✅ PASS |
| No routing behavior changes | ✅ PASS |

## Next

- Multi-node routing (route some traffic to .60 for large-context/reasoning)
- Multi-GPU Scheduler (after routing exists)

## Classification

**PASS** — Dynamic Node Registry implemented, tested (38/38), exposed read-only, no routing changes.
