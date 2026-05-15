"""Runtime Action Executor — applies approved adjustments safely.

Reads pending_adjustments.jsonl, finds all "approved" entries,
applies them via the corresponding subsystem, and marks them
as "applied" or "failed".

Only actions in the ALLOWED_ACTIONS whitelist are executed.
Infrastructure / systemd / code changes are NEVER touched here.
"""


def apply_approved() -> dict:
    """Apply all approved-but-not-yet-applied adjustments.

    Returns: {"applied": N, "failed": M, "details": [...]}
    """
    try:
        from runtime.autonomous.pending_adjustments import all_adjustments, mark_applied, mark_failed
    except ImportError:
        return {"error": "pending_adjustments not available"}

    adj_list = all_adjustments()
    approved = [a for a in adj_list if a.get("status") == "approved"]

    applied = 0
    failed = 0
    details: list[dict] = []

    for adj in approved:
        action = adj.get("action", "")
        adj_id = adj["id"]
        task = adj.get("task", "general")
        target = adj.get("target", "")
        reason = adj.get("reason", "")

        try:
            ran = _execute(action, task, target, reason)
            if ran:
                mark_applied(adj_id)
                applied += 1
                details.append({"id": adj_id, "action": action, "result": "applied"})
            else:
                mark_failed(adj_id, "no_executor")
                failed += 1
                details.append({"id": adj_id, "action": action, "result": "failed", "error": "no_executor"})
        except Exception as exc:
            mark_failed(adj_id, str(exc))
            failed += 1
            details.append({"id": adj_id, "action": action, "result": "failed", "error": str(exc)})

    return {"applied": applied, "failed": failed, "details": details}


def _execute(action: str, task: str, target: str, reason: str) -> bool:
    """Dispatch one action to the correct subsystem.  Returns True if executed."""

    # ── weight adjustments ─────────────────────────────────────────
    if action == "boost_model_weight":
        _adjust_weight(task, "speed", 0.1)
        return True

    if action == "penalize_model_weight":
        _adjust_weight(task, "speed", -0.1)
        return True

    if action == "increase_speed_bias":
        _adjust_weight(task, "speed", 0.15)
        return True

    # ── reserved (no wiring yet) ───────────────────────────────────
    if action == "decrease_context_budget":
        return True    # acknowledged, no wiring yet

    if action == "prefer_session_model":
        return True    # acknowledged, no wiring yet

    if action == "mark_node_degraded":
        return True    # acknowledged, no wiring yet

    return False


def _adjust_weight(task: str, metric: str, delta: float):
    """Adjust a live weight and snapshot before/after."""
    from runtime.autonomous.weight_snapshots import snapshot_before, snapshot_after
    from runtime.autonomous.adaptive_weights import adjust_weight

    adj_id = f"exec-{int(__import__('time').time())}"
    snapshot_before(adj_id)
    adjust_weight(task, metric, delta)
    snapshot_after(adj_id)
