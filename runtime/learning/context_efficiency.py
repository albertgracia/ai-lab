"""Context Efficiency Scoring — mide si el contexto inyectado aporta valor.

Métricas:
  prompt_tokens      — tokens enviados al modelo
  completion_tokens  — tokens generados
  latency_ms         — tiempo de respuesta
  budget_used        — fracción del presupuesto de contexto usado
  recall_chars       — caracteres de recall inyectados
  quality_score      — calidad de la respuesta (0-1)
  success            — si la request fue exitosa

Score compuesto:
  efficiency = utility / cost

Casos detectables:
  - overcontext: mucho contexto + mala calidad → reducir recall
  - undercontext: poco contexto + fallo → ampliar recall
  - fast_bloat: perfil fast con demasiado contexto → compactar
  - reasoning_starved: reasoning con baja calidad → subir budget
"""

from typing import Optional


def score_context_efficiency(
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    latency_ms: int = 0,
    budget_used: float = 0.0,
    recall_chars: int = 0,
    quality_score: float = 0.0,
    success: bool = True,
    task_type: str = "general",
) -> dict:
    """Compute context efficiency score and detect issues.

    Returns:
        dict with efficiency, label, cost, utility, detections, recommendation
    """
    # ── cost: weighted combination of resource usage ───────────────
    token_cost = (prompt_tokens + completion_tokens * 0.5) / 1000  # per 1K
    latency_cost = latency_ms / 1000  # seconds
    budget_cost = budget_used * 2
    recall_cost = recall_chars / 500  # per 500 chars
    cost = max(0.1, token_cost * 0.3 + latency_cost * 0.3 + budget_cost * 0.2 + recall_cost * 0.2)

    # ── utility: based on quality and success ─────────────────────
    utility = quality_score * (1.0 if success else 0.2)

    efficiency = round(utility / cost, 4) if cost > 0 else 0.0

    # ── label ─────────────────────────────────────────────────────
    if not success:
        label = "failed"
    elif efficiency >= 0.5:
        label = "good"
    elif efficiency >= 0.2:
        label = "fair"
    else:
        label = "poor"

    # ── detections ────────────────────────────────────────────────
    detections = []
    recommendation = None

    # overcontext: much context + poor quality
    if recall_chars > 1500 and quality_score < 0.5:
        detections.append("overcontext")
        recommendation = "reduce recall chars or increase min_score threshold"
    # undercontext: little context + failure
    elif recall_chars < 200 and not success:
        detections.append("undercontext")
        recommendation = "increase recall limit to provide more context"
    # fast_bloat: fast profile with too much context
    elif task_type == "fast" and recall_chars > 800:
        detections.append("fast_bloat")
        recommendation = "compact recall for fast profile (reduce max_chars or memories)"
    # reasoning_starved: reasoning profile with low quality
    elif task_type == "reasoning" and quality_score < 0.4 and recall_chars < 1000:
        detections.append("reasoning_starved")
        recommendation = "increase recall budget for reasoning profile"
    # high budget but low quality
    elif budget_used > 0.8 and quality_score < 0.4:
        detections.append("wasted_context")
        recommendation = "reduce overall context budget or improve source relevance"

    return {
        "efficiency": efficiency,
        "label": label,
        "cost": round(cost, 4),
        "utility": round(utility, 4),
        "detections": detections,
        "recommendation": recommendation,
        "task_type": task_type,
        "inputs": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "latency_ms": latency_ms,
            "budget_used": budget_used,
            "recall_chars": recall_chars,
            "quality_score": quality_score,
            "success": success,
        },
    }


def batch_evaluate(records: list[dict]) -> list[dict]:
    """Evaluate context efficiency for a list of cognitive/routing records.

    Each record should have:
        prompt_tokens, completion_tokens, latency_ms, budget_used,
        recall_chars, quality_score, success, task_type
    """
    results = []
    for rec in records:
        results.append(score_context_efficiency(
            prompt_tokens=rec.get("prompt_tokens", 0),
            completion_tokens=rec.get("completion_tokens", 0),
            latency_ms=rec.get("latency_ms", 0),
            budget_used=rec.get("budget_used", 0),
            recall_chars=rec.get("recall_chars", 0),
            quality_score=rec.get("quality_score", 0.5),
            success=rec.get("success", True),
            task_type=rec.get("task_type", "general"),
        ))
    return results


def summarize_efficiency(results: list[dict]) -> dict:
    """Aggregate efficiency scores across multiple evaluations."""
    if not results:
        return {"samples": 0, "avg_efficiency": 0, "labels": {}}

    labels = {}
    detections = {}
    for r in results:
        labels[r["label"]] = labels.get(r["label"], 0) + 1
        for d in r.get("detections", []):
            detections[d] = detections.get(d, 0) + 1

    return {
        "samples": len(results),
        "avg_efficiency": round(sum(r["efficiency"] for r in results) / len(results), 4),
        "avg_cost": round(sum(r["cost"] for r in results) / len(results), 4),
        "avg_utility": round(sum(r["utility"] for r in results) / len(results), 4),
        "labels": labels,
        "detections": detections,
        "pct_good": round(labels.get("good", 0) / len(results) * 100, 1),
        "pct_poor": round(labels.get("poor", 0) / len(results) * 100, 1),
    }
