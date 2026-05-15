"""Runtime Optimizer — autonomous optimisation brain (observational only).

Runs a periodic loop that:
  1. Reads historical data (routing, cognitive, affinity, gateway metrics)
  2. Computes recommendations
  3. Writes them to optimizer_history.jsonl

IMPORTANT: This phase does NOT apply changes automatically.
It only OBSERVES, ANALYSES, CALCULATES, and PROPOSES.
"""

import time
from collections import defaultdict


def _read_sources():
    """Read all available data sources.  Returns a dict with all info."""
    data: dict = {}

    # routing history
    try:
        from runtime.routing.routing_history import read_route_history
        data["routing_records"] = read_route_history(200)
    except ImportError:
        data["routing_records"] = []

    # cognitive history
    try:
        from runtime.cognitive.cognitive_history import read_history as _read_cog
        data["cognitive_records"] = _read_cog(50)
    except ImportError:
        data["cognitive_records"] = []

    # model performance
    try:
        from runtime.routing.model_performance import get_model_performance
        data["model_performance"] = get_model_performance()
    except ImportError:
        data["model_performance"] = {}

    # session affinity
    try:
        from runtime.autonomous.session_affinity import snapshot as _aff_snap
        data["affinity"] = _aff_snap()
    except ImportError:
        data["affinity"] = {}

    return data


def _compute_recommendations(data: dict) -> list[dict]:
    recs: list[dict] = []

    pref = data.get("model_performance", {})
    routing = [r for r in data.get("routing_records", []) if r.get("success")]
    cognitive = data.get("cognitive_records", [])

    # ── 1. detect high-latency tasks ───────────────────────────────
    task_latency: dict = defaultdict(list)
    for r in routing:
        if r.get("latency_ms"):
            task_latency[r.get("task_type", "general")].append(r["latency_ms"])
    for task, lats in task_latency.items():
        avg = sum(lats) / len(lats)
        if avg > 15000:
            recs.append({"action": "boost_speed_weight", "task": task, "reason": "latency_high", "avg_latency_ms": round(avg, 1), "confidence": 0.78})

    # ── 2. detect low confidence models ────────────────────────────
    for model, perf in pref.items():
        pi = perf.get("performance_index", 100)
        sr = perf.get("success_rate", 1.0)
        if pi < 50 and perf.get("total_requests", 0) >= 10:
            recs.append({"action": "deprioritize_model", "task": "general", "model": model, "reason": "low_performance", "performance_index": pi, "success_rate": sr, "confidence": 0.85})
        if sr < 0.7 and perf.get("total_requests", 0) >= 10:
            recs.append({"action": "review_model", "task": "general", "model": model, "reason": "high_failure_rate", "success_rate": sr, "confidence": 0.90})

    # ── 3. detect context budget issues ────────────────────────────
    if cognitive:
        recent = cognitive[-10:]
        avg_budget = sum(c.get("budget_used", 0) for c in recent) / max(len(recent), 1)
        if avg_budget > 0.85:
            recs.append({"action": "reduce_context", "reason": "budget_high", "avg_budget_used": round(avg_budget, 3), "confidence": 0.72})

    return recs


def run_optimizer_cycle() -> dict:
    """Run one full optimisation cycle.  Returns dict with recommendations."""
    data = _read_sources()
    recs = _compute_recommendations(data)

    # record to history AND queue pending adjustments (FASE 9.0.3)
    for rec in recs:
        try:
            from runtime.autonomous.optimizer_history import record_optimizer_action
            record_optimizer_action(
                action=rec.get("action", "unknown"),
                task=rec.get("task", "general"),
                reason=rec.get("reason", ""),
                confidence=rec.get("confidence", 0.0),
            )
        except ImportError:
            pass

        # ── safe pending adjustment (FASE 9.0.3) ─────────────────
        target = rec.get("model", rec.get("task", "general"))
        conf = rec.get("confidence", 0.0)
        try:
            from runtime.autonomous.optimizer_policy import validate_action
            allowed, reason = validate_action(rec.get("action", ""), conf)
            if allowed:
                from runtime.autonomous.pending_adjustments import create_pending
                create_pending(
                    action=rec["action"],
                    target=target,
                    task=rec.get("task", ""),
                    reason=rec.get("reason", ""),
                    confidence=conf,
                )
        except ImportError:
            pass

    return {"timestamp": int(time.time()), "recommendations": recs, "sources": {"routing_records": len(data.get("routing_records", [])), "cognitive_records": len(data.get("cognitive_records", [])), "affinity_sessions": data.get("affinity", {}).get("total_sessions", 0)}}
