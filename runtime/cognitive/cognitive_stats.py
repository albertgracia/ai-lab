"""Cognitive Stats — aggregated queries over cognitive_history.jsonl.

Provides trend analysis: avg context size per task, budget usage over
time, files-used distribution, etc.  Used by Live API /api/cognitive/stats
(future) and Grafana dashboards.
"""

from runtime.cognitive.cognitive_history import read_history


def avg_context_by_task(limit: int = 100) -> dict[str, dict]:
    """Return avg context_size and budget_used per task_type."""
    records = read_history(limit)
    groups: dict[str, list] = {}
    for r in records:
        task = r.get("task_type", "general")
        if task not in groups:
            groups[task] = []
        groups[task].append(r)

    result = {}
    for task, recs in groups.items():
        n = len(recs)
        result[task] = {
            "count": n,
            "avg_context_size": round(sum(r["context_size"] for r in recs) / n, 1),
            "avg_budget_used": round(sum(r["budget_used"] for r in recs) / n, 3),
            "avg_shaping_latency_ms": round(sum(r.get("shaping_latency_ms", 0) for r in recs) / n, 1),
            "avg_files_used": round(sum(r.get("files_used", 0) for r in recs) / n, 1),
        }
    return result
