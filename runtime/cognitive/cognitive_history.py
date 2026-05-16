"""Cognitive History — persistent JSONL snapshots of each context-shaping event.

Writes one JSON line per ``shape_context()`` call to enable trend analysis:
  • Are budgets growing over time?
  • Is the shaper using too many / too few files?
  • Is the working memory digest ballooning?

File: /opt/ai-lab/runtime/state/cognitive_history.jsonl
"""

import json, time
from pathlib import Path
from threading import Lock

HISTORY_FILE = Path("/opt/ai-lab/runtime/state/cognitive_history.jsonl")
_lock = Lock()
_MAX_LINES = 5000   # auto-truncate if it grows too large


def record_snapshot(
    task_type: str = "general",
    model: str = "",
    context_size: int = 0,
    budget_used: float = 0.0,
    shaping_latency_ms: int = 0,
    files_used: int = 0,
    files_used_names: list | None = None,
    digest_size: int = 0,
    working_memory_used: bool = False,
):
    record = {
        "timestamp": int(time.time()),
        "task_type": task_type,
        "model": model,
        "context_size": context_size,
        "budget_used": round(budget_used, 3),
        "shaping_latency_ms": shaping_latency_ms,
        "files_used": files_used,
        "files_used_names": files_used_names or [],
        "digest_size": digest_size,
        "working_memory_used": working_memory_used,
    }
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _lock:
            with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass
    # ── Qdrant cognitive hook (FASE 10) ─────────────────────────
    try:
        from runtime.memory.qdrant_routing_hook import on_cognitive_event
        on_cognitive_event({
            "task_type": task_type,
            "model": model,
            "context_size": context_size,
            "budget_used": budget_used,
            "shaping_latency_ms": shaping_latency_ms,
            "files_used": files_used,
            "files_used_names": files_used_names or [],
            "working_memory_used": working_memory_used,
        })
    except ImportError:
        pass

    # ── Incident hook for context overflows (FASE 10.2) ──────────
    if budget_used > 0.9:
        try:
            from runtime.memory.watchdog_incident_hook import record_node_incident
            record_node_incident(
                node="", host="",
                event="context_overflow",
                message=f"Context budget at {budget_used:.0%} ({task_type}/{model})",
                severity="warning",
            )
        except ImportError:
            pass


def read_history(limit: int = 20) -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    lines = HISTORY_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
    records = []
    for line in reversed(lines[-limit * 3:]):
        try:
            r = json.loads(line)
            records.append(r)
            if len(records) >= limit:
                break
        except json.JSONDecodeError:
            continue
    records.reverse()
    return records
