"""Memory injector for AI-LAB FASE 23A.

Single point of memory injection. Reads the memory policy for the active profile,
decides whether to execute recall, applies budgets, and returns structured items.

Returns items (not formatted blocks) so that text formatting, compression,
and truncation happen in the caller (context_shaper).
"""

from __future__ import annotations

import time

from pathlib import Path

try:
    from runtime.policies.memory.memory_loader import get_policy_for_profile as _get_memory_policy
    _HAVE_MEMORY_LOADER = True
except ImportError:
    _get_memory_policy = None  # type: ignore[assignment]
    _HAVE_MEMORY_LOADER = False

# ── FASE 23B.1: normalized skip reasons ────────────────────────────
SKIP_CONTAMINATION = "contamination_gate"
SKIP_MINIMAL_GUARD = "hard_guard_minimal"
SKIP_BUDGET_EXCEEDED = "budget_exceeded"
SKIP_LOW_SCORE = "low_score"
SKIP_FAMILY_MISMATCH = "family_mismatch"
SKIP_QUERY_SHORT = "query_too_short"
SKIP_NO_SOURCES = "no_sources"
SKIP_DISABLED = "semantic_recall_disabled"


def _load_family_config() -> dict:
    try:
        import json
        manifest = json.loads((_POLICIES_DIR / "manifest_memory.json").read_text(encoding="utf-8"))
        return manifest.get("families", {})
    except Exception:
        return {}


def _effective_score(semantic_score: float, source: str, timestamp: int, usefulness: float = 1.0) -> float:
    """FASE 23B.6: effective score with freshness decay."""
    families = _load_family_config()
    family = families.get(source, {})
    retention = family.get("retention_days", 30)
    age_days = (time.time() - timestamp) / 86400 if timestamp else 0
    freshness = max(0.1, 1.0 - age_days / max(retention, 1))
    return semantic_score * freshness * usefulness


def _should_skip(policy: dict, query_text: str) -> tuple[bool, str]:
    if not policy.get("semantic_recall"):
        return True, SKIP_DISABLED
    if policy.get("policy") == "minimal":
        return True, SKIP_MINIMAL_GUARD
    words = len(query_text.split())
    min_words = policy.get("min_query_words", 4)
    if words < min_words:
        return True, SKIP_QUERY_SHORT
    if not policy.get("sources"):
        return True, SKIP_NO_SOURCES
    return False, ""


def build_memory_context(policy: dict, query_text: str, task_type: str = "general") -> dict:
    """Execute memory recall governed by *policy*.
    Returns dict with items, memories, chars, scores, sources, retrieval_ms."""
    t_start = time.time()

    skipped, reason = _should_skip(policy, query_text)
    if skipped:
        try:
            from runtime.telemetry.prometheus_metrics import record_memory_metrics
            record_memory_metrics({"memories": 0, "chars": 0, "skipped": True, "sources": []}, policy.get("policy", "unknown"))
        except ImportError:
            pass
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
            "retrieval_ms": int((time.time() - t_start) * 1000),
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
                raw_score = float(r.get("score", 0) or 0)
                payload = r.get("payload", {}) if isinstance(r.get("payload"), dict) else {}
                ts = int(payload.get("timestamp", r.get("timestamp", 0)) or 0)
                score = _effective_score(raw_score, collection, ts)
                if score < min_score:
                    continue
                text = payload.get("summary") or payload.get("content") or payload.get("text") or ""
                if not text:
                    continue
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
                    "score": _effective_score(0.65, "episodic", ts),
                    "source": "episodic",
                    "timestamp": ts,
                })
        except ImportError:
            pass

    items.sort(key=lambda i: i["score"], reverse=True)

    # FASE 23B.1: contamination gate — skip if too many low-quality hits
    if items:
        contamination = sum(1 for i in items if i["score"] < 0.15) / len(items)
        if contamination > 0.2:
            try:
                from runtime.telemetry.prometheus_metrics import MEMORY_CONTAMINATION
                MEMORY_CONTAMINATION.labels(policy=policy.get("policy", "unknown")).observe(contamination)
            except ImportError:
                pass
            return {
                "items": [],
                "memories": 0, "chars": 0,
                "top_score": 0.0, "avg_score": 0.0, "hit_ratio": 0.0,
                "sources": [],
                "skipped": True, "skip_reason": SKIP_CONTAMINATION,
                "retrieval_ms": int((time.time() - t_start) * 1000),
            }

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

    retrieval_ms = int((time.time() - t_start) * 1000)
    try:
        from runtime.telemetry.prometheus_metrics import record_memory_metrics
        ctx = {
            "memories": len(items), "chars": total_chars, "top_score": top_score,
            "avg_score": avg_score, "hit_ratio": hit_ratio,
            "sources": list(dict.fromkeys(i["source"] for i in items)),
            "skipped": False,
        }
        record_memory_metrics(ctx, policy.get("policy", "unknown"))
        try:
            from runtime.telemetry.prometheus_metrics import MEMORY_QUALITY_SCORE
            MEMORY_QUALITY_SCORE.labels(policy=policy.get("policy", "unknown")).observe(float(avg_score))
        except ImportError:
            pass
    except ImportError:
        pass

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
        "retrieval_ms": retrieval_ms,
    }
