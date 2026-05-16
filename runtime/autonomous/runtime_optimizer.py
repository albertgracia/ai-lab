"""Runtime Optimizer — autonomous optimisation brain.

Pipeline:
  1. Collect data (routing, cognitive, model perf, affinity)
  2. Run pattern_learner → detect patterns
  3. Run context_efficiency → score context value
  4. Run recommendation_engine → convert to proposals
  5. Run _evaluate_outcomes → check if past adjustments helped
  6. Validate against policy → queue pending adjustments

IMPORTANT: This cycle does NOT apply changes automatically.
It OBSERVES, ANALYSES, EXTRACTS PATTERNS, and PROPOSES.
"""

import time
from collections import defaultdict

from runtime.autonomous.action_types import (
    INCREASE_SPEED_BIAS,
    PENALIZE_MODEL_WEIGHT,
    DECREASE_CONTEXT_BUDGET,
)


def _read_sources():
    """Read all available data sources.  Returns a dict with all info."""
    data: dict = {}

    try:
        from runtime.routing.routing_history import read_route_history
        data["routing_records"] = read_route_history(200)
    except ImportError:
        data["routing_records"] = []

    try:
        from runtime.cognitive.cognitive_history import read_history as _read_cog
        data["cognitive_records"] = _read_cog(50)
    except ImportError:
        data["cognitive_records"] = []

    try:
        from runtime.routing.model_performance import get_model_performance
        data["model_performance"] = get_model_performance()
    except ImportError:
        data["model_performance"] = {}

    try:
        from runtime.autonomous.session_affinity import snapshot as _aff_snap
        data["affinity"] = _aff_snap()
    except ImportError:
        data["affinity"] = {}

    return data


def _compute_recommendations(data: dict) -> list[dict]:
    """Original detection logic (kept for backward compat)."""
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
            recs.append({
                "action": INCREASE_SPEED_BIAS,
                "task": task,
                "reason": "latency_high",
                "avg_latency_ms": round(avg, 1),
                "confidence": 0.78,
            })

    # ── 2. detect low confidence models ────────────────────────────
    for model, perf in pref.items():
        pi = perf.get("performance_index", 100)
        sr = perf.get("success_rate", 1.0)
        if pi < 50 and perf.get("total_requests", 0) >= 10:
            recs.append({
                "action": PENALIZE_MODEL_WEIGHT,
                "task": "general",
                "model": model,
                "reason": "low_performance",
                "performance_index": pi,
                "success_rate": sr,
                "confidence": 0.85,
            })
        if sr < 0.7 and perf.get("total_requests", 0) >= 10:
            recs.append({
                "action": PENALIZE_MODEL_WEIGHT,
                "task": "general",
                "model": model,
                "reason": "high_failure_rate",
                "success_rate": sr,
                "confidence": 0.90,
            })

    # ── 3. detect context budget issues ────────────────────────────
    if cognitive:
        recent = cognitive[-10:]
        avg_budget = sum(c.get("budget_used", 0) for c in recent) / max(len(recent), 1)
        if avg_budget > 0.85:
            recs.append({
                "action": DECREASE_CONTEXT_BUDGET,
                "reason": "budget_high",
                "avg_budget_used": round(avg_budget, 3),
                "confidence": 0.72,
            })

    return recs


def _queue_recommendations(recs: list[dict]):
    """Queue each recommendation as a pending adjustment (if policy allows)."""
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

        target = rec.get("target", rec.get("model", rec.get("task", "general")))
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


def _evaluate_outcomes() -> list[dict]:
    """Check if past adjustments improved metrics.

    Looks at adjustments applied > 1 hour ago and compares
    before/after metrics where available.
    """
    results = []
    try:
        from runtime.autonomous.pending_adjustments import all_adjustments
        adjustments = all_adjustments(50)
    except ImportError:
        return results

    now = time.time()
    for adj in adjustments:
        if adj.get("status") not in ("applied", "failed"):
            continue
        applied_at = adj.get("applied_at") or adj.get("timestamp", 0)
        if now - applied_at < 3600:
            continue  # too recent to evaluate

        results.append({
            "id": adj.get("id", ""),
            "action": adj.get("action", ""),
            "target": adj.get("target", ""),
            "status": adj.get("status", ""),
            "applied_at": applied_at,
            "hours_ago": round((now - applied_at) / 3600, 1),
            "evaluation": "pending_manual_review",
        })

    return results


def run_optimizer_cycle() -> dict:
    """Run one full optimisation cycle with pattern learning + recommendations.

    Returns dict with recommendations, patterns, efficiency and sources.
    """
    data = _read_sources()

    # ── original detectors ─────────────────────────────────────────
    recs = _compute_recommendations(data)

    # ── FASE 12: pattern learning ──────────────────────────────────
    patterns = []
    try:
        from runtime.memory.pattern_learner import run_all
        patterns = run_all(days=7)
    except ImportError:
        pass

    # ── FASE 12: context efficiency ────────────────────────────────
    efficiency_results = []
    try:
        from runtime.learning.context_efficiency import batch_evaluate
        cognitive = data.get("cognitive_records", [])
        if cognitive:
            efficiency_results = batch_evaluate(cognitive)
    except ImportError:
        pass

    # ── FASE 12: recommendation engine ────────────────────────────
    try:
        from runtime.learning.recommendation_engine import generate_recommendations
        f12_recs = generate_recommendations(
            patterns=patterns,
            efficiency_results=efficiency_results,
            model_performance=data.get("model_performance", {}),
        )
        recs.extend(f12_recs)
    except ImportError:
        pass

    # ── queue all recommendations ──────────────────────────────────
    _queue_recommendations(recs)

    # ── evaluate past outcomes ─────────────────────────────────────
    outcomes = _evaluate_outcomes()

    return {
        "timestamp": int(time.time()),
        "recommendations_count": len(recs),
        "recommendations": recs,
        "patterns_count": len(patterns),
        "patterns": patterns,
        "efficiency_samples": len(efficiency_results),
        "outcomes_count": len(outcomes),
        "outcomes": outcomes,
        "sources": {
            "routing_records": len(data.get("routing_records", [])),
            "cognitive_records": len(data.get("cognitive_records", [])),
            "affinity_sessions": data.get("affinity", {}).get("total_sessions", 0),
        },
    }
