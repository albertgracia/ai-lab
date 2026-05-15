"""Optimizer Policy — whitelist of allowed autonomous actions.

Every recommendation from runtime_optimizer.py must pass this policy
before it can become a pending adjustment.  The policy is deliberately
conservative: only metric-level tweaks are permitted; infrastructure,
code, and configuration changes are forbidden.

Allowed actions:
  boost_model_weight       – increase a model's capability weight
  penalize_model_weight    – decrease a model's capability weight
  increase_speed_bias      – raise the 'speed' dimension global bias
  decrease_context_budget  – reduce the token budget for context shaping
  mark_node_degraded       – flag a GPU node as degraded
  prefer_session_model     – set a session-scoped model preference

Forbidden actions (hard block):
  restart_service, modify_code, modify_prompt, delete_memory,
  change_traefik, change_cloudflare, change_systemd
"""

ALLOWED_ACTIONS = frozenset({
    "boost_model_weight",
    "penalize_model_weight",
    "increase_speed_bias",
    "decrease_context_budget",
    "mark_node_degraded",
    "prefer_session_model",
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
