"""Memory Usefulness — post-recall feedback tracking.

Measures whether semantic recall helped or added noise,
without modifying the recall pipeline itself.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_FEEDBACK_FILE = Path("/opt/ai-lab/runtime/state/recall_feedback.jsonl")


def record_recall_outcome(
    query_text: str,
    helpful: bool,
    noise_score: float = 0.0,
    latency_cost_ms: float = 0.0,
    context_ratio: float = 0.0,
) -> None:
    """Record post-recall feedback. Called externally after a response is evaluated."""
    entry = {
        "timestamp": int(time.time()),
        "query": query_text[:200],
        "helpful": helpful,
        "noise_score": round(noise_score, 3),
        "latency_cost_ms": round(latency_cost_ms, 1),
        "context_ratio": round(context_ratio, 3),
    }
    try:
        _FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_FEEDBACK_FILE, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def get_usefulness_stats(days: int = 7) -> dict[str, Any]:
    """Aggregate recall usefulness statistics."""
    if not _FEEDBACK_FILE.exists():
        return {"total": 0, "helpful_rate": 0, "noise_avg": 0, "latency_avg": 0}

    cutoff = time.time() - days * 86400
    entries: list[dict] = []
    try:
        for line in _FEEDBACK_FILE.read_text().strip().split("\n"):
            if not line:
                continue
            entry = json.loads(line)
            if entry.get("timestamp", 0) >= cutoff:
                entries.append(entry)
    except Exception:
        pass

    if not entries:
        return {"total": 0, "helpful_rate": 0, "noise_avg": 0, "latency_avg": 0}

    helpful_count = sum(1 for e in entries if e.get("helpful"))
    return {
        "total": len(entries),
        "helpful_rate": round(helpful_count / len(entries), 3),
        "noise_avg": round(sum(e.get("noise_score", 0) for e in entries) / len(entries), 3),
        "latency_avg": round(sum(e.get("latency_cost_ms", 0) for e in entries) / len(entries), 1),
    }
