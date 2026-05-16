"""Optimizer Policy — whitelist of allowed autonomous actions.

Every recommendation from runtime_optimizer.py must pass this policy
before it can become a pending adjustment.  The policy is deliberately
conservative: only metric-level tweaks are permitted; infrastructure,
code, and configuration changes are forbidden.
"""

from runtime.autonomous.action_types import (
    BOOST_MODEL_WEIGHT,
    PENALIZE_MODEL_WEIGHT,
    INCREASE_SPEED_BIAS,
    DECREASE_CONTEXT_BUDGET,
    MARK_NODE_DEGRADED,
    PREFER_SESSION_MODEL,
    TUNE_PROFILE_MAX_TOKENS,
    TUNE_RECALL_CHARS,
    TUNE_RECALL_SCORE,
    TUNE_RECALL_MEMORIES,
)

ALLOWED_ACTIONS = frozenset({
    BOOST_MODEL_WEIGHT,
    PENALIZE_MODEL_WEIGHT,
    INCREASE_SPEED_BIAS,
    DECREASE_CONTEXT_BUDGET,
    MARK_NODE_DEGRADED,
    PREFER_SESSION_MODEL,
    TUNE_PROFILE_MAX_TOKENS,
    TUNE_RECALL_CHARS,
    TUNE_RECALL_SCORE,
    TUNE_RECALL_MEMORIES,
})

FORBIDDEN_ACTIONS = frozenset({
    "restart_service",
    "modify_code",
    "modify_prompt",
    "delete_memory",
    "change_traefik",
    "change_cloudflare",
    "change_systemd",
})

MIN_CONFIDENCE = 0.70


def validate_action(action: str, confidence: float = 0.0) -> tuple[bool, str]:
    """Check whether *action* is safe to queue as a pending adjustment.

    Returns (allowed: bool, reason: str).
    """
    if action in FORBIDDEN_ACTIONS:
        return False, f"action '{action}' is permanently forbidden"
    if action not in ALLOWED_ACTIONS:
        return False, f"action '{action}' is not in the allowed whitelist"
    if confidence < MIN_CONFIDENCE:
        return False, f"confidence {confidence:.2f} is below minimum {MIN_CONFIDENCE}"
    return True, "ok"
