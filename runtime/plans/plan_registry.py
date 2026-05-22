from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any


PLAN_CONTRACT_VERSION = "28.4"


def _strict_mode() -> bool:
    return os.environ.get("STRICT_VALIDATION_MODE", "false").lower() in ("true", "1", "yes")


def build_plan_registry() -> dict[str, Any]:
    """Registry of plan surfaces (planner/executors) and their tool usage."""

    plans = [
        {
            "plan_id": "planner_readonly_28_1",
            "plan_type": "planner",
            "capability": "readonly",
            "tools": ["readonly_executor"],
            "artifacts": ["execution_audit"],
            "lifecycle": "active",
            "deterministic": True,
            "source": "runtime.agentic.planner",
        },
        {
            "plan_id": "executor_readonly_28_2",
            "plan_type": "executor",
            "capability": "readonly",
            "tools": ["readonly_executor"],
            "artifacts": ["execution_audit"],
            "lifecycle": "active",
            "deterministic": True,
            "source": "runtime.agentic.readonly_executor",
        },
        {
            "plan_id": "executor_sandbox_write_28_3",
            "plan_type": "executor",
            "capability": "sandbox_write",
            "tools": ["sandbox_write_executor"],
            "artifacts": ["sandbox_artifacts"],
            "lifecycle": "active",
            "deterministic": True,
            "source": "runtime.agentic.sandbox_executor",
        },
        {
            "plan_id": "validation_burnin_33b",
            "plan_type": "validation",
            "capability": "validation",
            "tools": ["runtime_validation_33b"],
            "artifacts": ["validation_report"],
            "lifecycle": "historical",
            "deterministic": True,
            "source": "runtime.validation",
        },
        {
            "plan_id": "crossplan_gc_28_4",
            "plan_type": "gc",
            "capability": "gc",
            "tools": ["crossplan_gc_28_4"],
            "artifacts": ["gc_inventory"],
            "lifecycle": "active",
            "deterministic": True,
            "source": "runtime.gc.crossplan_gc",
        },
    ]

    return {
        "contract_version": PLAN_CONTRACT_VERSION,
        "generated_at": 0.0 if _strict_mode() else time.time(),
        "plans": plans,
        "total_plans": len(plans),
    }


def build_plan_dependencies() -> dict[str, Any]:
    reg = build_plan_registry()
    tools = set()
    artifacts = set()
    for p in reg.get("plans", []):
        for t in p.get("tools", []):
            tools.add(t)
        for a in p.get("artifacts", []):
            artifacts.add(a)
    return {
        "contract_version": PLAN_CONTRACT_VERSION,
        "tools": sorted(tools),
        "artifacts": sorted(artifacts),
        "total_tools": len(tools),
        "total_artifacts": len(artifacts),
    }


def build_cross_plan_references() -> dict[str, Any]:
    """Cross-plan graph nodes and edges: plan → tool → artifact."""
    reg = build_plan_registry()
    nodes = []
    edges = []

    for p in reg.get("plans", []):
        pid = p.get("plan_id")
        nodes.append({"node_type": "plan", "id": pid, "capability": p.get("capability"), "lifecycle": p.get("lifecycle")})
        for t in p.get("tools", []):
            nodes.append({"node_type": "tool", "id": t})
            edges.append({"src": pid, "dst": t, "relationship": "uses_tool"})
        for a in p.get("artifacts", []):
            nodes.append({"node_type": "artifact", "id": a})
            edges.append({"src": pid, "dst": a, "relationship": "produces_artifact"})

    # Dedup nodes
    seen = set()
    uniq_nodes = []
    for n in nodes:
        key = (n.get("node_type"), n.get("id"))
        if key in seen:
            continue
        seen.add(key)
        uniq_nodes.append(n)

    return {
        "contract_version": PLAN_CONTRACT_VERSION,
        "nodes": uniq_nodes,
        "edges": edges,
        "total_nodes": len(uniq_nodes),
        "total_edges": len(edges),
        "loops_detected": False,
    }


def build_plan_lifecycle_summary() -> dict[str, Any]:
    reg = build_plan_registry()
    counts: dict[str, int] = {}
    for p in reg.get("plans", []):
        lc = p.get("lifecycle", "unknown")
        counts[lc] = counts.get(lc, 0) + 1
    return {
        "contract_version": PLAN_CONTRACT_VERSION,
        "lifecycle_counts": counts,
    }


def detect_orphan_plans() -> list[str]:
    # Orphan = plan references tools not present in tool registry.
    try:
        from runtime.tools.tool_registry import build_tool_contracts
        tools = {t["tool_id"] for t in build_tool_contracts()}
    except Exception:
        tools = set()
    reg = build_plan_registry()
    orphan = []
    for p in reg.get("plans", []):
        for t in p.get("tools", []):
            if tools and t not in tools:
                orphan.append(p.get("plan_id"))
    return sorted(set([p for p in orphan if p]))


def detect_stale_plans() -> list[str]:
    # No persistent plan store in this phase.
    return []


def detect_invalid_plan_references() -> list[dict[str, Any]]:
    invalid = []
    graph = build_cross_plan_references()
    for e in graph.get("edges", []):
        if not e.get("src") or not e.get("dst"):
            invalid.append({"edge": e, "reason": "missing src/dst"})
    return invalid
