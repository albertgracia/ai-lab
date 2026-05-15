"""Runtime Confidence — assign confidence scores to model decisions.

For a given (task, model) pair, returns a 0‑1 confidence score
based on historical performance, session affinity, latency profile
and failover history.

Used by the autonomous optimiser to decide whether to propose changes.
"""

import time


def compute_confidence(
    task_type: str,
    model_id: str,
    session_id: str = "",
) -> tuple[float, list[str]]:
    """Return (confidence 0‑1, list of reasons).

    Formula:
        confidence = success_rate * 0.5
                   + latency_score  * 0.2
                   + affinity_score * 0.2
                   + failover_penalty * 0.1
    """
    reasons: list[str] = []

    # ── 1. success rate (from routing history) ─────────────────────
    success_rate = 0.5
    try:
        from runtime.routing.routing_history import stats_by_model
        stats = stats_by_model(task_type, window_minutes=1440)
        model_stats = stats.get(model_id, {})
        success_rate = model_stats.get("success_rate", success_rate)
        if success_rate >= 0.9:
            reasons.append("high_success_rate")
        elif success_rate >= 0.7:
            reasons.append("moderate_success_rate")
        else:
            reasons.append("low_success_rate")
    except ImportError:
        pass

    # ── 2. latency score ───────────────────────────────────────────
    latency_score = 0.5
    try:
        from runtime.routing.routing_history import stats_by_model
        stats = stats_by_model(task_type, window_minutes=1440)
        ms = stats.get(model_id, {})
        s = ms.get("streaming", {})
        ns = ms.get("non_streaming", {})
        combo_lat = (
            s.get("avg_latency_ms", 0) * s.get("count", 0) +
            ns.get("avg_latency_ms", 0) * ns.get("count", 0)
        ) / max(s.get("count", 0) + ns.get("count", 0), 1)
        latency_score = max(0, 1 - combo_lat / 30_000)
        if latency_score >= 0.8:
            reasons.append("low_latency")
        elif latency_score >= 0.5:
            reasons.append("moderate_latency")
    except ImportError:
        pass

    # ── 3. session affinity ────────────────────────────────────────
    affinity_score = 0.0
    if session_id:
        try:
            from runtime.autonomous.session_affinity import get_affinity
            aff = get_affinity(session_id)
            if aff and aff.get("preferred_model") == model_id:
                affinity_score = aff.get("confidence", 0.0)
                reasons.append("session_affinity")
        except ImportError:
            pass

    # ── 4. failover penalty ────────────────────────────────────────
    failover_penalty = 0.0
    try:
        from runtime.routing.routing_history import stats_by_model
        stats = stats_by_model(task_type, window_minutes=1440)
        ms = stats.get(model_id, {})
        fr = ms.get("failover_rate", 0.0)
        failover_penalty = max(0, 1 - fr * 5)  # 0% failover → 1.0, 20% → 0.0
        if fr > 0.1:
            reasons.append("failover_risk")
        elif fr == 0:
            reasons.append("low_failover_rate")
    except ImportError:
        pass

    # ── composite ───────────────────────────────────────────────────
    confidence = (
        success_rate * 0.5 +
        latency_score * 0.2 +
        affinity_score * 0.2 +
        failover_penalty * 0.1
    )
    return round(min(confidence, 1.0), 3), reasons
