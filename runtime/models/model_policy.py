"""
ROUTER-HF-MODEL-POLICY-01: Canonical router model policy.

Single source of truth for model routing decisions.

DEFINES:
- CANONICAL_MODELS: deterministic route -> model mapping
- Helper functions for each route type
- PROHIBITED_MODELS: models that must never be routed to

RULES:
- llama-3.1-8b-instruct is PROHIBITED (broken Jinja template)
- fast/observe/minimal/fallback/degraded/greeting/lightweight -> qwen3-vl-8b-instruct
- coding/reasoning/tool-use/auto/architecture/report -> qwen/qwen2.5-coder-14b-instruct

Architecture:
    model_policy.py  (canonical)
        imported by gateway, router, profiles, registry, precision, observability
"""

CANONICAL_MODELS = {
    "fast": "qwen2.5-14b-instruct",
    "observe": "qwen2.5-14b-instruct",
    "minimal": "qwen2.5-14b-instruct",
    "fallback": "qwen2.5-14b-instruct",
    "degraded": "qwen2.5-14b-instruct",
    "greeting": "qwen2.5-14b-instruct",
    "lightweight": "qwen2.5-14b-instruct",
    "auto": "qwen/qwen2.5-coder-14b-instruct",
    "coding": "qwen/qwen2.5-coder-14b-instruct",
    "reasoning": "qwen/qwen2.5-coder-14b-instruct",
    "tool-use": "qwen/qwen2.5-coder-14b-instruct",
    "architecture": "qwen/qwen2.5-coder-14b-instruct",
    "report": "qwen/qwen2.5-coder-14b-instruct",
}

PROHIBITED_MODELS = frozenset({
    "llama-3.1-8b-instruct",
})

FAST_MODEL = "qwen2.5-14b-instruct"
STRONG_MODEL = "qwen/qwen2.5-coder-14b-instruct"


def get_model_for_route(route: str) -> str:
    """Return the canonical model_id for a given route name.
    Falls back to FAST_MODEL for unknown routes.
    """
    return CANONICAL_MODELS.get(route, FAST_MODEL)


def get_fast_model() -> str:
    """Return model for fast/lightweight/observe routes."""
    return FAST_MODEL


def get_fallback_model() -> str:
    """Return model for fallback/default routing."""
    return FAST_MODEL


def get_degraded_model() -> str:
    """Return model for degraded/emergency routing."""
    return FAST_MODEL


def get_coding_model() -> str:
    """Return model for coding/reasoning/tool-use routes."""
    return STRONG_MODEL


def get_reasoning_model() -> str:
    """Return model for deep reasoning routes."""
    return STRONG_MODEL


def get_tool_use_model() -> str:
    """Return model for tool-use routes."""
    return STRONG_MODEL


def is_prohibited_model(model_id: str | None) -> bool:
    """Return True if the model_id is prohibited from routing."""
    if not model_id:
        return False
    return model_id.strip() in PROHIBITED_MODELS


def validate_route_model_selection(
    model_id: str,
    route: str = "fast",
    task_type: str = "general",
) -> str:
    """Validate a model selection against canonical policy.
    Returns the canonical model for the route if the selected model is
    prohibited, otherwise returns the selected model unchanged.
    """
    if is_prohibited_model(model_id):
        return get_model_for_route(route)
    return model_id
