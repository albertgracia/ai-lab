"""Pending Adjustments — queue of safe, proposed actions awaiting approval.

Every recommendation that passes the optimizer policy is stored here
as a "pending" entry.  Adjustments remain pending until explicitly
approved or rejected (future phase).

File: /opt/ai-lab/runtime/state/pending_adjustments.jsonl
"""

import json, time, uuid
from pathlib import Path
from threading import Lock

HISTORY_FILE = Path("/opt/ai-lab/runtime/state/pending_adjustments.jsonl")
_lock = Lock()

_ADJUSTMENT_PREFIX = "adj"


def _next_id() -> str:
    return f"{_ADJUSTMENT_PREFIX}-{int(time.time())}-{uuid.uuid4().hex[:6]}"


def create_pending(
    action: str,
    target: str = "",
    task: str = "",
    reason: str = "",
    confidence: float = 0.0,
) -> dict:
    """Queue a new pending adjustment.

    Returns the adjustment dict (already persisted).
    """
    record = {
        "id": _next_id(),
        "timestamp": int(time.time()),
        "action": action,
        "target": target,
        "task": task,
        "reason": reason,
        "confidence": round(confidence, 3),
        "status": "pending",
    }
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _lock:
            with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return record


def get_pending(limit: int = 20) -> list[dict]:
    """Return the most recent pending adjustments (newest first)."""
    if not HISTORY_FILE.exists():
        return []
    lines = HISTORY_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
    records = []
    for line in reversed(lines):
        try:
            r = json.loads(line)
            if r.get("status") == "pending":
                records.append(r)
                if len(records) >= limit:
                    break
        except json.JSONDecodeError:
            continue
    return records


def all_pending() -> list[dict]:
    """Return ALL pending adjustments."""
    if not HISTORY_FILE.exists():
        return []
    lines = HISTORY_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
    records = []
    for line in lines:
        try:
            r = json.loads(line)
            if r.get("status") == "pending":
                records.append(r)
        except json.JSONDecodeError:
            continue
    return records
