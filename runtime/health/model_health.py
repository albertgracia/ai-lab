"""Model Health Score — per-model, per-node operational reliability.

Scores are 0.0-1.0 based on recent routing history data:
  success_rate, avg_latency, failover_rate, context_efficiency.

Does NOT replace capability routing. Feeds into model_router
as an additional 0.10 weighting factor for tie-breaking.
"""

from __future__ import annotations

import time
from typing import Any


def model_health_score(model_id: str, node_name: str, *, window_minutes: int = 60) -> float:
    """Return 0.0-1.0 health score for a specific model on a specific node.

    Components:
      success_rate      × 0.40
      latency_score     × 0.25  (lower latency = higher score)
      failover_penalty  × 0.25  (lower failover rate = higher score)
      freshness_bonus   × 0.10  (recent data = higher confidence)

    Returns 0.50 (neutral) if insufficient data.
    """
    try:
        from runtime.routing.routing_history import stats_by_model

        stats = stats_by_model(task_type=None, window_minutes=window_minutes)
        entry = _find_entry(stats, model_id, node_name)
        if not entry:
            return 0.50

        total = entry.get("total", 0)
        if total < 3:
            return 0.50

        success_rate = entry.get("success_rate", 0.5)
        avg_latency = entry.get("avg_latency_ms", 5000)
        failover_rate = entry.get("failover_rate", 0.0)
        last_seen = entry.get("last_seen", 0)

        latency_score = _score_latency(avg_latency)
        failover_score = 1.0 - min(1.0, failover_rate * 2)
        freshness = min(1.0, max(0.0, (time.time() - last_seen) / 3600 * -1 + 1))

        return (
            success_rate * 0.40
            + latency_score * 0.25
            + failover_score * 0.25
            + freshness * 0.10
        )
    except Exception:
        return 0.50


def get_all_health_scores(window_minutes: int = 60) -> dict[str, dict[str, Any]]:
    """Return health scores for all model+node pairs."""
    try:
        from runtime.routing.routing_history import stats_by_model

        stats = stats_by_model(task_type=None, window_minutes=window_minutes)
        scores: dict[str, dict[str, Any]] = {}
        for key, entry in stats.items():
            model_id = entry.get("model", key)
            node = entry.get("node", "")
            total = entry.get("total", 0)
            if total < 3:
                continue
            scores[key] = {
                "model": model_id,
                "node": node,
                "health": round(model_health_score(model_id, node, window_minutes=window_minutes), 3),
                "success_rate": entry.get("success_rate", 0),
                "avg_latency_ms": entry.get("avg_latency_ms", 0),
                "failover_rate": entry.get("failover_rate", 0),
                "total_requests": total,
            }
        return scores
    except Exception:
        return {}


def _find_entry(stats: dict, model_id: str, node_name: str) -> dict | None:
    for key, entry in stats.items():
        if entry.get("model") == model_id and entry.get("node") == node_name:
            return entry
    for key, entry in stats.items():
        if model_id in key and node_name in key:
            return entry
    return None


def _score_latency(avg_latency_ms: float) -> float:
    if avg_latency_ms <= 1000:
        return 1.0
    if avg_latency_ms <= 5000:
        return 0.85
    if avg_latency_ms <= 15000:
        return 0.60
    if avg_latency_ms <= 30000:
        return 0.35
    return 0.10
