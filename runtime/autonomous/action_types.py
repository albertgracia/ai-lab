"""Action type constants — única fuente de verdad para acciones del optimizador.

Todas las recommendations, policies, y pending adjustments usan estas
constantes.  Si aparece un string hardcodeado en otro sitio, es un bug.
"""

# ── Acciones permitidas (policy ALLOWED) ────────────────────────────────
BOOST_MODEL_WEIGHT = "boost_model_weight"
PENALIZE_MODEL_WEIGHT = "penalize_model_weight"
INCREASE_SPEED_BIAS = "increase_speed_bias"
DECREASE_CONTEXT_BUDGET = "decrease_context_budget"
MARK_NODE_DEGRADED = "mark_node_degraded"
PREFER_SESSION_MODEL = "prefer_session_model"

# ── Acciones de tuning de perfiles (FASE 12.5) ─────────────────────────
TUNE_PROFILE_MAX_TOKENS = "tune_profile_max_tokens"
TUNE_RECALL_CHARS = "tune_recall_chars"
TUNE_RECALL_SCORE = "tune_recall_score"
TUNE_RECALL_MEMORIES = "tune_recall_memories"

# ── Agrupaciones útiles ─────────────────────────────────────────────────
ALL_ALLOWED = frozenset({
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

TUNE_ACTIONS = frozenset({
    TUNE_PROFILE_MAX_TOKENS,
    TUNE_RECALL_CHARS,
    TUNE_RECALL_SCORE,
    TUNE_RECALL_MEMORIES,
})
