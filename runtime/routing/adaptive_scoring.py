"""Adaptive Scoring — hybrid scoring with temporal decay.

Fuses the static capability score from the model registry with
historical performance data.  If less than 10 samples exist for a
model, falls back to capability-only scoring.

Key feature: exponential time decay — bad performance older than
24 hours is progressively forgiven.
"""

import time, math


def hybrid_score(task_type, model_id, node_state=None, window_minutes=60):
    """Return a 0‑100 hybrid score for *model_id* on *task_type*.

    The hybrid score combines:
      - capability_score  (static, from model_registry)  × 0.7
      - performance_score (empirical, from history)       × 0.3 × decay_factor

    If fewer than 10 historical samples exist, returns capability_score only.
    """
    # ── capability score (static) ────────────────────────────────────
    cap_score = 0
    try:
        from runtime.models.model_registry import score_model
        cap_score = score_model(task_type, model_id)
    except ImportError:
        return 50  # neutral fallback

    # ── performance score (historical) ───────────────────────────────
    try:
        from runtime.routing.model_performance import get_model_performance
    except ImportError:
        return cap_score

    perf = get_model_performance(task_type, window_minutes).get(model_id, {})
    total = perf.get("total_requests", 0)

    if total < 10:
        _inc_fallback()
        return cap_score  # not enough data — trust static only

    # streaming + non-streaming combined
    s = perf.get("streaming", {})
    ns = perf.get("non_streaming", {})
    s_n = s.get("count", 0)
    ns_n = ns.get("count", 0)
    combined_n = s_n + ns_n or 1

    # weighted average latency (normalised 0‑1, lower is better)
    combo_lat = (
        s.get("avg_latency_ms", 0) * s_n +
        ns.get("avg_latency_ms", 0) * ns_n
    ) / combined_n
    lat_norm = max(0, 1 - combo_lat / 30_000)  # 0ms → 1.0, 30s → 0.0

    # weighted average success rate
    combo_succ = (
        s.get("success_rate", 0) * s_n +
        ns.get("success_rate", 0) * ns_n
    ) / combined_n

    perf_score = (combo_succ * 0.5 + lat_norm * 0.5) * 100

    # ── temporal decay ───────────────────────────────────────────────
    last_ts = perf.get("last_updated", time.time())
    hours_since = (time.time() - last_ts) / 3600.0
    decay = math.exp(-hours_since / 24.0)  # half-life: ~17 hours

     # ── final hybrid ──────────────────────────────────────────────────
    final = cap_score * 0.7 + perf_score * 0.3 * decay
    _inc_routing()
    return round(min(final, 100), 1)


# ── cognitive telemetry hooks (FASE 8.9) ──────────────────────────────

def _inc_routing():
    try:
        from runtime.cognitive.cognitive_metrics import increment
        increment("adaptive_routing_total")
    except ImportError:
        pass

def _inc_fallback():
    try:
        from runtime.cognitive.cognitive_metrics import increment
        increment("adaptive_routing_fallbacks")
    except ImportError:
        pass
