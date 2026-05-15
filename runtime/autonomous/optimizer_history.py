"""Optimizer History — persistent journal of every automatic optimisation.

Records what the optimiser decided, why, and with what confidence.
This provides full auditability and allows rollback if an optimisation
proves harmful.

File: /opt/ai-lab/runtime/state/optimizer_history.jsonl
"""

import json, time
from pathlib import Path
from threading import Lock

HISTORY_FILE = Path("/opt/ai-lab/runtime/state/optimizer_history.jsonl")
_lock = Lock()


def record_optimizer_action(
    action: str,
    task: str = "",
    metric: str = "",
    before: float = 0.0,
    after: float = 0.0,
    reason: str = "",
    confidence: float = 0.0,
):
    """Append one optimisation event to the journal."""
    record = {
        "timestamp": int(time.time()),
        "action": action,
        "task": task,
        "metric": metric,
        "before": before,
        "after": after,
        "reason": reason,
        "confidence": round(confidence, 3),
    }
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _lock:
            with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


def read_optimizer_history(limit: int = 100) -> list[dict]:
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
