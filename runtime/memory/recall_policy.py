"""Recall Policy Engine — controlled, scored, budgeted semantic recall.

Architecture:
  query → classify → should_recall? → search sources(ordered) → quality gate → inject advisory block

Rules:
  • Strict source ordering: incidents > routing_history > cognitive_history > working_memory
  • Budget per profile: max memories, max chars, min score
  • Quality gate: skip recall if contamination_risk > 0.2
  • Advisory tone — recall is "experiencias pasadas relevantes", NOT "esto es verdad"
  • Never dump raw embeddings. Never exceed budget.
"""

import time
from typing import Optional

CONTAMINATION_GATE = 0.2

# ── recall budget per profile ─────────────────────────────────────────
RECALL_BUDGET: dict[str, dict] = {
    "fast": {
        "max_memories": 1,
        "max_chars": 500,
        "min_score": 0.65,
        "sources": ["incidents"],
    },
    "coding": {
        "max_memories": 3,
        "max_chars": 1500,
        "min_score": 0.55,
        "sources": ["incidents", "routing_history"],
    },
    "reasoning": {
        "max_memories": 5,
        "max_chars": 3000,
        "min_score": 0.45,
        "sources": ["incidents", "routing_history", "cognitive_history"],
    },
    "general": {
        "max_memories": 2,
        "max_chars": 1000,
        "min_score": 0.5,
        "sources": ["incidents", "routing_history"],
    },
}

DEFAULT_PROFILE = "general"


def should_recall(task_type: str, query_text: str) -> bool:
    """Decide whether recall is worth doing for this query+profile.

    Returns False if:
      - query is empty/too short (< 10 chars)
      - query is a greeting or trivial
      - profile has no sources configured
    """
    if not query_text or len(query_text.strip()) < 10:
        return False

    cfg = RECALL_BUDGET.get(task_type, RECALL_BUDGET[DEFAULT_PROFILE])
    if not cfg["sources"]:
        return False

    trivial = ("hola", "hello", "hi", "ok", "gracias", "thanks", "si", "no", "yes",
               "adelante", "continue", "/help", "buf")
    ql = query_text.lower().strip()
    if ql in trivial or len(ql.split()) <= 2:
        return False

    return True


def max_memories(task_type: str) -> int:
    return RECALL_BUDGET.get(task_type, RECALL_BUDGET[DEFAULT_PROFILE])["max_memories"]


def max_memory_chars(task_type: str) -> int:
    return RECALL_BUDGET.get(task_type, RECALL_BUDGET[DEFAULT_PROFILE])["max_chars"]


def minimum_score(task_type: str) -> float:
    return RECALL_BUDGET.get(task_type, RECALL_BUDGET[DEFAULT_PROFILE])["min_score"]


def recall_sources(task_type: str) -> list[str]:
    return RECALL_BUDGET.get(task_type, RECALL_BUDGET[DEFAULT_PROFILE])["sources"]


def _summarize(payload: dict, collection: str) -> str:
    """One-line summary from a payload."""
    event = payload.get("event_type", "")
    node = payload.get("node", "") or payload.get("host", "")
    message = payload.get("message", "")
    model = payload.get("model", "")
    task = payload.get("task_type", "")
    severity = payload.get("severity", "")
    latency = payload.get("latency_ms", 0)
    error = payload.get("error", "")

    parts = []
    if event:
        parts.append(event.replace("_", " "))
    if node:
        parts.append(node)
    if severity:
        parts.append(f"({severity})")
    if task:
        parts.append(task)
    if model:
        parts.append(model)
    if latency:
        parts.append(f"{latency}ms")
    if message and len(message) < 120:
        parts.append(message)
    elif error and len(error) < 100:
        parts.append(error)

    return " | ".join(parts)


def execute_recall(query_text: str, task_type: str = "") -> dict:
    """Run the full recall pipeline: classify → search → filter → format.

    Returns:
        {
            "enabled": True/False,
            "collections_used": [...],
            "matches": N,
            "avg_score": 0.0,
            "chars_injected": N,
            "block": "...",         # [SEMANTIC_RECALL_BEGIN]...[/SEMANTIC_RECALL_END] or ""
        }
    """
    result = {
        "enabled": False,
        "collections_used": [],
        "matches": 0,
        "avg_score": 0.0,
        "chars_injected": 0,
        "block": "",
    }

    if not should_recall(task_type, query_text):
        return result

    cfg = RECALL_BUDGET.get(task_type, RECALL_BUDGET[DEFAULT_PROFILE])
    sources = cfg["sources"]
    min_score = cfg["min_score"]
    budget = cfg["max_memories"]
    char_budget = cfg["max_chars"]

    try:
        from runtime.memory.qdrant_store import search_collection as _sc
    except ImportError:
        return result

    all_hits = []
    used_collections = []
    remaining = budget

    for coll in sources:
        if remaining <= 0:
            break
        hits = _sc(coll, query_text, limit=remaining)
        qualified = [h for h in hits if h["score"] >= min_score]
        if qualified:
            for h in qualified:
                h["collection"] = coll
                all_hits.append(h)
            used_collections.append(coll)
            remaining -= len(qualified)

    if not all_hits:
        return result

    # ── quality gate: skip recall if contamination risk is too high ──
    try:
        from runtime.memory.quality_assessment import assess_query
        qa = assess_query(query_text, all_hits)
        if qa.get("contamination_risk", 0) > CONTAMINATION_GATE:
            result["block"] = ""
            try:
                from runtime.audit.audit_logger import audit_event
                audit_event("recall_contaminated", {"query": query_text[:100], "risk": qa.get("contamination_risk", 0)})
            except ImportError:
                pass
            return result
    except ImportError:
        pass

    all_hits.sort(key=lambda x: x["score"], reverse=True)
    all_hits = all_hits[:budget]

    avg_score = sum(h["score"] for h in all_hits) / len(all_hits)

    lines = []
    used_chars = 0
    for h in all_hits:
        coll = h.get("collection", "?")
        score = h["score"]
        summary = _summarize(h.get("payload", {}), coll)
        entry = f"  • ({coll}) {summary}"
        if used_chars + len(entry) + 2 > char_budget:
            break
        lines.append(entry)
        used_chars += len(entry)

    block = ("[SEMANTIC_RECALL_BEGIN]\n"
             "Experiencias pasadas relevantes (advisory, no verificadas):\n"
             + "\n".join(lines) +
             "\n[/SEMANTIC_RECALL_END]")

    result["enabled"] = True
    result["collections_used"] = used_collections
    result["matches"] = len(all_hits)
    result["avg_score"] = round(avg_score, 2)
    result["chars_injected"] = len(block)
    result["block"] = block

    return result
