"""Backfill incidents collection from cluster_state, routing history, and system state.

Usage:
    python3 backfill_incidents.py

Scans existing data and creates incident records in Qdrant for:
  - Node failures (backoff_skip, offline)
  - High-latency degradations
  - Context overflows
  - Any routing errors/failovers
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, "/opt/ai-lab")
from runtime.memory.qdrant_store import store_embedding, count_points

CLUSTER_STATE = Path("/opt/ai-lab/runtime/state/cluster_state.json")
ROUTING_HISTORY = Path("/opt/ai-lab/runtime/state/routing_history.jsonl")
COGNITIVE_HISTORY = Path("/opt/ai-lab/runtime/state/cognitive_history.jsonl")
BACKUP_ROUTING = Path("/opt/ai-lab/backups/pre-qdrant-seed-20260516-133327/routing_history.jsonl")

INCIDENT_SCHEMA_VERSION = "1.0"

LATENCY_THRESHOLDS = {
    "fast": 30_000,
    "coding": 60_000,
    "reasoning": 120_000,
}


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def backfill_from_cluster_state() -> list[dict]:
    incidents = []
    if not CLUSTER_STATE.exists():
        return incidents

    state = json.loads(CLUSTER_STATE.read_text())

    for node in state.get("nodes", []):
        name = node.get("name", "unknown")
        status = node.get("status", "")
        error = node.get("error", "")

        if status == "backoff_skip" or not node.get("online", True):
            incidents.append({
                "event_type": "node_failure",
                "severity": "critical",
                "node": name,
                "host": node.get("host", ""),
                "status": status,
                "error": error,
                "message": f"Node {name} skipped after consecutive failures",
                "timestamp": state.get("timestamp", time.time()),
                "schema_version": INCIDENT_SCHEMA_VERSION,
                "source": "cluster_state",
                "resolved": False,
            })

    for node in state.get("discovered_nodes", []):
        if not node.get("online", False):
            name = node.get("host", "unknown")
            incidents.append({
                "event_type": "node_offline",
                "severity": "warning",
                "node": name,
                "host": name,
                "status": "offline",
                "error": node.get("error", "Connection timeout"),
                "message": f"Node {name} is offline",
                "timestamp": state.get("updated_at", time.time()),
                "schema_version": INCIDENT_SCHEMA_VERSION,
                "source": "cluster_state",
                "resolved": False,
            })

    return incidents


def backfill_from_routing_history(entries: list[dict]) -> list[dict]:
    incidents = []

    for entry in entries:
        ts = entry.get("timestamp", time.time())
        node = entry.get("node", "unknown")
        task_type = entry.get("task_type", "unknown")
        model = entry.get("model", "unknown")
        latency = entry.get("latency_ms", 0) or 0

        if not entry.get("success", True):
            incidents.append({
                "event_type": "routing_error",
                "severity": "critical",
                "node": node,
                "host": entry.get("host", ""),
                "model": model,
                "task_type": task_type,
                "error": entry.get("error", "Unknown error"),
                "message": f"Routing failure on {node} for {task_type}/{model}",
                "timestamp": ts,
                "schema_version": INCIDENT_SCHEMA_VERSION,
                "source": "routing_history",
                "resolved": False,
            })

        if entry.get("failover", False):
            incidents.append({
                "event_type": "failover",
                "severity": "warning",
                "node": node,
                "host": entry.get("host", ""),
                "model": model,
                "task_type": task_type,
                "message": f"Failover triggered for {task_type}/{model} on {node}",
                "timestamp": ts,
                "schema_version": INCIDENT_SCHEMA_VERSION,
                "source": "routing_history",
                "resolved": False,
            })

        threshold = LATENCY_THRESHOLDS.get(task_type, 30_000)
        if latency > threshold:
            incidents.append({
                "event_type": "high_latency",
                "severity": "warning" if latency > threshold * 1.5 else "info",
                "node": node,
                "host": entry.get("host", ""),
                "model": model,
                "task_type": task_type,
                "latency_ms": latency,
                "threshold_ms": threshold,
                "message": f"High latency on {node}: {latency}ms ({task_type}, threshold={threshold}ms)",
                "timestamp": ts,
                "schema_version": INCIDENT_SCHEMA_VERSION,
                "source": "routing_history",
                "resolved": False,
            })

    return incidents


def backfill_from_cognitive_history(entries: list[dict]) -> list[dict]:
    incidents = []
    for entry in entries:
        ts = entry.get("timestamp", time.time())
        budget = entry.get("budget_used", 0) or 0

        if budget > 0.9:
            incidents.append({
                "event_type": "context_overflow",
                "severity": "warning",
                "task_type": entry.get("task_type", "unknown"),
                "model": entry.get("model", "unknown"),
                "context_size": entry.get("context_size", 0),
                "budget_used": budget,
                "message": f"Context budget near limit: {budget:.0%} used",
                "timestamp": ts,
                "schema_version": INCIDENT_SCHEMA_VERSION,
                "source": "cognitive_history",
                "resolved": False,
            })

    return incidents


def deduplicate(incidents: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for inc in incidents:
        key = (inc["event_type"], inc.get("node", ""), inc.get("message", "")[:80])
        if key not in seen:
            seen.add(key)
            unique.append(inc)
    return unique


def main():
    print("=" * 55)
    print("Backfill Incidents — Scan data → Qdrant")
    print("=" * 55)

    before = count_points("incidents")
    print(f"Incidents in Qdrant before: {before}")

    incidents = []

    print("\n📡 Cluster state...")
    cluster_inc = backfill_from_cluster_state()
    print(f"   {len(cluster_inc)} incidents from cluster state")
    incidents.extend(cluster_inc)

    print("\n📦 Routing history (live)...")
    routing = load_jsonl(ROUTING_HISTORY)
    print(f"   {len(routing)} entries")
    routing_inc = backfill_from_routing_history(routing)
    print(f"   {len(routing_inc)} incidents from routing history")
    incidents.extend(routing_inc)

    print("\n📦 Routing history (backup seed)...")
    routing_bak = load_jsonl(BACKUP_ROUTING)
    print(f"   {len(routing_bak)} entries")
    routing_bak_inc = backfill_from_routing_history(routing_bak)
    print(f"   {len(routing_bak_inc)} incidents from backup routing")
    incidents.extend(routing_bak_inc)

    print("\n🧠 Cognitive history (live)...")
    cognitive = load_jsonl(COGNITIVE_HISTORY)
    print(f"   {len(cognitive)} entries")
    cog_inc = backfill_from_cognitive_history(cognitive)
    print(f"   {len(cog_inc)} incidents from cognitive history")
    incidents.extend(cog_inc)

    incidents = deduplicate(incidents)
    print(f"\n{'=' * 55}")
    print(f"Total unique incidents to store: {len(incidents)}")

    ok = 0
    fail = 0
    for i, inc in enumerate(incidents):
        try:
            if store_embedding("incidents", inc):
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f"  [{i+1}/{len(incidents)}] FAIL: {e}")
            fail += 1
        if (i + 1) % 5 == 0 or i == len(incidents):
            print(f"  [{i+1}/{len(incidents)}] ok={ok} fail={fail}")

    after = count_points("incidents")
    print(f"\n{'=' * 55}")
    print(f"Stored: {ok}")
    print(f"Failed: {fail}")
    print(f"Incidents in Qdrant: {before} → {after} (+{after - before})")
    print(f"{'=' * 55}")


if __name__ == "__main__":
    main()
