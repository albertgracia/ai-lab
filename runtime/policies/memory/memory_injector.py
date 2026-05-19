"""Memory injector for AI-LAB FASE 23A.

Single point of memory injection. Reads the memory policy for the active profile,
decides whether to execute recall, applies budgets, and returns structured items.

Returns items (not formatted blocks) so that text formatting, compression,
and truncation happen in the caller (context_shaper).
"""

from __future__ import annotations

from pathlib import Path

try:
    from runtime.policies.memory.memory_loader import get_policy_for_profile as _get_memory_policy
    _HAVE_MEMORY_LOADER = True
except ImportError:
    _get_memory_policy = None  # type: ignore[assignment]
    _HAVE_MEMORY_LOADER = False


def _should_skip(policy: dict, query_text: str) -> tuple[bool, str]:
    if not policy.get("semantic_recall"):
        return True, "semantic_recall_disabled"
    words = len(query_text.split())
    min_words = policy.get("min_query_words", 4)
    if words < min_words:
        return True, f"query_too_short ({words} < {min_words})"
    if not policy.get("sources"):
        return True, "no_sources_configured"
    return False, ""


def build_memory_context(policy: dict, query_text: str, task_type: str = "general") -> dict:
    """Execute memory recall governed by *policy*.

    Returns:
        {
            "items": [{"text":str, "score":float, "source":str, "timestamp":int}, ...],
            "memories": int,
            "chars": int,
            "top_score": float,
            "avg_score": float,
            "hit_ratio": float,
            "sources": list[str],
            "skipped": bool,
            "skip_reason": str,
        }
    """
    skipped, reason = _should_skip(policy, query_text)
    if skipped:
        return {
            "items": [],
            "memories": 0,
            "chars": 0,
            "top_score": 0.0,
            "avg_score": 0.0,
            "hit_ratio": 0.0,
            "sources": [],
            "skipped": True,
            "skip_reason": reason,
        }

    sources = policy.get("sources", [])
    max_memories = policy.get("max_memories", 1)
    min_score = policy.get("min_score", 0.6)
    max_chars = policy.get("max_chars", 800)

    items: list[dict] = []

    try:
        from runtime.memory.qdrant_store import search_collection as _search

        for collection in sources:
            try:
                results = _search(collection, query_text, limit=max_memories)
            except Exception:
                results = []

            for r in results:
                if not isinstance(r, dict):
                    continue
                score = float(r.get("score", 0) or 0)
                if score < min_score:
                    continue
                payload = r.get("payload", {}) if isinstance(r.get("payload"), dict) else {}
                text = payload.get("summary") or payload.get("content") or payload.get("text") or ""
                if not text:
                    continue
                ts = int(payload.get("timestamp", r.get("timestamp", 0)) or 0)
                items.append({
                    "text": str(text)[:400],
                    "score": score,
                    "source": collection,
                    "timestamp": ts,
                })
    except ImportError:
        pass

    if policy.get("episodic_recall"):
        try:
            from runtime.memory.episodic_memory import read_episodes
            episodes = read_episodes(limit=max_memories)
            for ep in episodes:
                if not isinstance(ep, dict):
                    continue
                text = ep.get("summary", "")
                ts = int(ep.get("timestamp", 0) or 0)
                items.append({
                    "text": str(text)[:400],
                    "score": 0.65,
                    "source": "episodic",
                    "timestamp": ts,
                })
        except ImportError:
            pass

    items.sort(key=lambda i: i["score"], reverse=True)

    if len(items) > max_memories:
        items = items[:max_memories]

    total_chars = sum(len(i["text"]) for i in items)
    if total_chars > max_chars:
        budget = max_chars
        for i in items:
            if budget <= 0:
                i["text"] = ""
            elif len(i["text"]) > budget:
                i["text"] = i["text"][:budget] + "..."
                budget = 0
            else:
                budget -= len(i["text"])
        items = [i for i in items if i["text"]]

    scores = [i["score"] for i in items]
    top_score = max(scores) if scores else 0.0
    avg_score = sum(scores) / len(scores) if scores else 0.0
    hit_ratio = len(items) / max(max_memories, 1)
    total_chars = sum(len(i["text"]) for i in items)

    return {
        "items": items,
        "memories": len(items),
        "chars": total_chars,
        "top_score": top_score,
        "avg_score": avg_score,
        "hit_ratio": hit_ratio,
        "sources": list(dict.fromkeys(i["source"] for i in items)),
        "skipped": False,
        "skip_reason": "",
    }
