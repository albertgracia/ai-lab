"""Semantic Search Quality Assessment — precision, noise, contamination.

Provides:
  - Single-query quality scoring (precision, noise, contamination risk)
  - Batch quality assessment across multiple test queries
  - Threshold suggestion based on score distribution
  - Hallucination contamination detection (low-score but returned results)

Usage:
    from runtime.memory.quality_assessment import assess_query, batch_assessment
"""

from typing import Any


def assess_query(
    query: str,
    results: list[dict],
    precision_threshold: float = 0.5,
    noise_threshold: float = 0.3,
    contamination_threshold: float = 0.15,
) -> dict:
    """Assess quality of a single semantic search result set.

    Args:
        query: the search query text
        results: list of {score, payload} from search_collection
        precision_threshold: score above which is "relevant"
        noise_threshold: score below which is "noise"
        contamination_threshold: score below which is "contamination risk"

    Returns:
        dict with quality metrics
    """
    scores = [r["score"] for r in results]
    total = len(scores)

    precision = sum(1 for s in scores if s >= precision_threshold) / total if total else 0.0
    noise = sum(1 for s in scores if s < noise_threshold) / total if total else 0.0
    contamination = sum(1 for s in scores if s < contamination_threshold) / total if total else 0.0

    score_stats = {}
    if scores:
        sorted_s = sorted(scores)
        score_stats = {
            "min": round(min(scores), 4),
            "max": round(max(scores), 4),
            "mean": round(sum(scores) / len(scores), 4),
            "median": round(sorted_s[len(sorted_s) // 2], 4),
            "p25": round(sorted_s[len(sorted_s) // 4], 4),
            "p75": round(sorted_s[len(sorted_s) * 3 // 4], 4),
        }

    return {
        "query": query,
        "total": total,
        "precision": round(precision, 4),
        "noise": round(noise, 4),
        "contamination_risk": round(contamination, 4),
        "score_stats": score_stats,
        "scores": [round(s, 4) for s in scores],
        "thresholds_used": {
            "precision": precision_threshold,
            "noise": noise_threshold,
            "contamination": contamination_threshold,
        },
    }


def suggest_thresholds(results: list[dict]) -> dict:
    """Suggest optimal score thresholds based on result distribution.

    Analyzes score gaps and clustering to find natural cutoff points.

    Args:
        results: list of {score, payload} from search_collection

    Returns:
        dict with suggested thresholds
    """
    scores = sorted([r["score"] for r in results], reverse=True)
    if not scores:
        return {
            "suggested_precision": 0.5,
            "suggested_noise": 0.3,
            "suggested_contamination": 0.15,
            "score_gaps": [],
        }

    gaps = []
    for i in range(len(scores) - 1):
        gap = scores[i] - scores[i + 1]
        if gap > 0.05:
            gaps.append({"between": f"{scores[i+1]:.3f}–{scores[i]:.3f}", "gap": round(gap, 4)})

    return {
        "suggested_precision": round(max(scores) * 0.6, 4) if scores else 0.5,
        "suggested_noise": round(max(scores) * 0.3, 4) if scores else 0.3,
        "suggested_contamination": round(max(scores) * 0.15, 4) if scores else 0.15,
        "score_gaps": gaps[:5],
        "max_score": round(max(scores), 4),
        "min_score": round(min(scores), 4),
    }


TEST_QUERIES = {
    "incidents": [
        "node failure",
        "high latency",
        "service down",
        "GPU offline",
        "routing error",
        "LM Studio crash",
        "out of memory",
        "connection timeout",
        "failover event",
        "degraded performance",
    ],
    "routing_history": [
        "coding request",
        "fast inference",
        "reasoning task",
        "streaming response",
        "model qwen",
        "high latency",
        "successful inference",
    ],
    "cognitive_history": [
        "context shaping",
        "budget usage",
        "working memory",
        "file selection",
        "digest size",
    ],
}


def run_batch(collection: str, search_fn: callable, limit: int = 5) -> dict:
    """Run quality assessment across predefined test queries.

    Args:
        collection: Qdrant collection name
        search_fn: function(collection, query, limit) -> list[dict]
        limit: results per query

    Returns:
        aggregated batch assessment
    """
    queries = TEST_QUERIES.get(collection, [])
    if not queries:
        return {"collection": collection, "error": f"No test queries for {collection}"}

    results = []
    all_scores = []
    for q in queries:
        hits = search_fn(collection, q, limit=limit)
        assessment = assess_query(q, hits)
        results.append(assessment)
        all_scores.extend(assessment.get("scores", []))

    avg_precision = sum(r["precision"] for r in results) / len(results) if results else 0
    avg_noise = sum(r["noise"] for r in results) / len(results) if results else 0
    avg_contamination = sum(r["contamination_risk"] for r in results) / len(results) if results else 0

    return {
        "collection": collection,
        "queries_tested": len(queries),
        "aggregate": {
            "avg_precision": round(avg_precision, 4),
            "avg_noise": round(avg_noise, 4),
            "avg_contamination_risk": round(avg_contamination, 4),
        },
        "threshold_suggestion": suggest_thresholds([{"score": s} for s in all_scores]),
        "per_query": results,
    }
