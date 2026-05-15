"""Model Performance — high-level aggregation layer over routing_history.

Separates streaming vs non-streaming performance, computes weighted
scores, and provides queryable stats for /api/model-performance and docs.
"""

import time, math
from runtime.routing.routing_history import stats_by_model


def get_model_performance(task_type=None, window_minutes=60):
    """Return dictionary of per-model performance stats.

    Each model entry contains:
        - capability_score (from registry, if available)
        - total_requests
        - streaming / non_streaming breakdown
        - success_rate
        - avg_gpu_load
        - performance_index (0‑100 compound score)
    """
    raw = stats_by_model(task_type=task_type, window_minutes=window_minutes)

    # ── optionally enrich with capability scores from the registry ────
    try:
        from runtime.models.model_registry import model_registry as registry  # type: ignore[no-any-unimported]
        from runtime.models.model_registry import score_model
        _have_registry = True
    except ImportError:
        registry = {}
        score_model = lambda t, m: 0  # noqa: E731
        _have_registry = False

    result = {}
    for model, stats in raw.items():
        entry = dict(stats)

        # capability score
        c = task_type or "general"
        entry["capability_score"] = score_model(c, model) if _have_registry else 0

        # display name
        entry["display_name"] = (
            registry.get(model, {}).get("display_name", model)
            if _have_registry
            else model
        )

        # gpu name
        entry["gpu"] = (
            registry.get(model, {}).get("gpu", "—")
            if _have_registry
            else "—"
        )

        # performance index (0‑100)
        s = stats.get("streaming", {})
        ns = stats.get("non_streaming", {})
        combined_lat = (
            (s.get("avg_latency_ms", 0) * s.get("count", 0) +
             ns.get("avg_latency_ms", 0) * ns.get("count", 0)) /
            max(s.get("count", 0) + ns.get("count", 0), 1)
        )
        lat_norm = max(0, 1 - combined_lat / 30000)
        succ = stats.get("success_rate", 0)
        entry["performance_index"] = round((succ * 0.5 + lat_norm * 0.5) * 100, 1)

        result[model] = entry

    return result
