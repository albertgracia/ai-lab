"""Recommendation Engine — convierte patrones en acciones propuestas.

Pipeline:
  pattern_learner.run_all() → patrones detectados
  context_efficiency.batch_evaluate() → scores de eficiencia
  recommendation_engine.generate_recommendations() → acciones propuestas
  optimizer_policy.validate_action() → policy gate
  pending_adjustments.create_pending() → cola de aprobación

Cada recomendación incluye:
  - evidence: fuentes concretas
  - confidence: 0-1 basado en datos observados
  - risk: low/medium/high
  - expected_impact: estimación cualitativa
  - rollback: cómo deshacer
"""

import uuid
import time

from runtime.autonomous.action_types import (
    INCREASE_SPEED_BIAS,
    PENALIZE_MODEL_WEIGHT,
    DECREASE_CONTEXT_BUDGET,
    TUNE_PROFILE_MAX_TOKENS,
    TUNE_RECALL_CHARS,
    TUNE_RECALL_SCORE,
    TUNE_RECALL_MEMORIES,
)


def generate_recommendations(
    patterns: list[dict],
    efficiency_results: list[dict] | None = None,
    model_performance: dict | None = None,
) -> list[dict]:
    """Convert detected patterns + efficiency scores into action proposals.

    Args:
        patterns: output from pattern_learner.run_all()
        efficiency_results: output from context_efficiency.batch_evaluate()
        model_performance: output from model_performance.get_model_performance()

    Returns:
        list of recommendation dicts ready for policy validation + pending queue
    """
    recs: list[dict] = []
    seq = 0

    for p in patterns:
        ptype = p.get("type", "")
        target = p.get("target", "general")
        confidence = p.get("confidence", 0.5)

        if ptype == "high_budget_recurring":
            recs.append(_build_rec(
                seq := seq + 1,
                TUNE_RECALL_CHARS,
                target,
                f"Alto uso de presupuesto recurrente en perfil {target}",
                [p.get("evidence", "")],
                confidence,
                "low",
                "reducir budget_used ~15-20%",
                f"restaurar recall max_chars a valor anterior para {target}",
            ))

        elif ptype == "recall_bloat":
            recs.append(_build_rec(
                seq := seq + 1,
                TUNE_RECALL_CHARS,
                target,
                f"Recall inflado en perfil {target}",
                [p.get("evidence", "")],
                confidence,
                "low",
                "reducir chars inyectados y latency",
                f"restaurar recall max_chars para {target}",
            ))

        elif ptype == "degrading_model":
            recs.append(_build_rec(
                seq := seq + 1,
                PENALIZE_MODEL_WEIGHT,
                target,
                f"Modelo {target} con degradación de rendimiento",
                [p.get("evidence", "")],
                confidence,
                "medium",
                "mejorar success_rate en siguientes requests",
                f"restaurar peso original de {target}",
            ))

        elif ptype == "high_latency_model":
            recs.append(_build_rec(
                seq := seq + 1,
                PENALIZE_MODEL_WEIGHT,
                target,
                f"Latencia alta recurrente en {target}",
                [p.get("evidence", "")],
                confidence,
                "low",
                "reducir latencia media en siguientes requests",
                f"restaurar peso original de {target}",
            ))

        elif ptype == "repeated_node_failure":
            recs.append(_build_rec(
                seq := seq + 1,
                INCREASE_SPEED_BIAS,
                target,
                f"Nodo {target} con fallos repetidos",
                [p.get("evidence", "")],
                confidence,
                "medium",
                "evitar enrutar a nodo problemático",
                "restaurar bias de velocidad original",
            ))

        elif ptype == "high_critical_ratio":
            recs.append(_build_rec(
                seq := seq + 1,
                DECREASE_CONTEXT_BUDGET,
                "incidents",
                "Proporción crítica de incidents elevada",
                [p.get("evidence", "")],
                confidence,
                "medium",
                "reducir carga cognitiva para estabilizar",
                "restaurar context budget anterior",
            ))

        elif ptype in ("recurring_low_recall_quality", "noisy_incidents"):
            recs.append(_build_rec(
                seq := seq + 1,
                TUNE_RECALL_SCORE,
                target,
                "Calidad de recall baja recurrente",
                [p.get("evidence", "")],
                confidence,
                "low",
                "mejorar precisión del recall semántico",
                "restaurar min_score anterior",
            ))

    # ── efficiency-based recommendations ───────────────────────────
    if efficiency_results:
        for label, count in _count_detections(efficiency_results).items():
            if label == "fast_bloat" and count >= 2:
                recs.append(_build_rec(
                    seq := seq + 1,
                    TUNE_PROFILE_MAX_TOKENS,
                    "fast",
                    f"Perfil fast con contexto excesivo ({count} detecciones)",
                    [f"{count} evaluaciones de eficiencia detectaron fast_bloat"],
                    0.65,
                    "low",
                    "reducir latency en perfil fast",
                    "restaurar max_tokens anterior para fast",
                ))
            elif label == "reasoning_starved" and count >= 2:
                recs.append(_build_rec(
                    seq := seq + 1,
                    TUNE_RECALL_MEMORIES,
                    "reasoning",
                    f"Perfil reasoning con contexto insuficiente ({count} detecciones)",
                    [f"{count} evaluaciones detectaron reasoning_starved"],
                    0.65,
                    "low",
                    "mejorar calidad de respuesta en reasoning",
                    "restaurar max_memories anterior para reasoning",
                ))

    # ── model performance trends ──────────────────────────────────
    if model_performance:
        for model, perf in model_performance.items():
            sr = perf.get("success_rate", 1.0)
            pi = perf.get("performance_index", 100)
            if sr < 0.7 and perf.get("total_requests", 0) >= 10:
                recs.append(_build_rec(
                    seq := seq + 1,
                    PENALIZE_MODEL_WEIGHT,
                    model,
                    f"Modelo {model} con success_rate bajo ({sr:.0%})",
                    [f"performance_index={pi}, total_requests={perf.get('total_requests', 0)}"],
                    0.85,
                    "medium",
                    "mejorar fiabilidad del routing",
                    f"restaurar peso original de {model}",
                ))

    return recs


def _build_rec(
    seq: int,
    action: str,
    target: str,
    reason: str,
    evidence: list[str],
    confidence: float,
    risk: str,
    expected_impact: str,
    rollback: str,
) -> dict:
    ts = int(time.time())
    return {
        "id": f"rec-{ts}-{seq:03d}",
        "action": action,
        "target": target,
        "change": reason,
        "reason": reason,
        "evidence": evidence,
        "confidence": round(confidence, 2),
        "risk": risk,
        "expected_impact": expected_impact,
        "rollback": rollback,
        "created_at": ts,
    }


def _count_detections(efficiency_results: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in efficiency_results:
        for d in r.get("detections", []):
            counts[d] = counts.get(d, 0) + 1
    return counts
