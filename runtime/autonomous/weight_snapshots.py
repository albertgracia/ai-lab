"""Weight Snapshots — audit trail of every weight change.

Snapshots are taken before and after each adjustment so that
any change can be rolled back.  The snapshot references the
adjustment ID from pending_adjustments.jsonl for traceability.

File: /opt/ai-lab/runtime/state/runtime_weight_snapshots.jsonl
"""

import json, time, copy
from pathlib import Path
from threading import Lock

SNAPSHOT_FILE = Path("/opt/ai-lab/runtime/state/runtime_weight_snapshots.jsonl")
_lock = Lock()


def snapshot_before(adj_id: str) -> dict:
    """Take a snapshot of current LIVE_TASK_WEIGHTS before an adjustment."""
    try:
        from runtime.autonomous.adaptive_weights import snapshot as _weights
        before = _weights()
    except ImportError:
        before = {}

    record = {"type": "before", "adj_id": adj_id, "timestamp": int(time.time()), "weights": before}
    _write(record)
    return copy.deepcopy(before)


def snapshot_after(adj_id: str):
    """Take a snapshot of LIVE_TASK_WEIGHTS after an adjustment."""
    try:
        from runtime.autonomous.adaptive_weights import snapshot as _weights
        after = _weights()
    except ImportError:
        after = {}
    record = {"type": "after", "adj_id": adj_id, "timestamp": int(time.time()), "weights": after}
    _write(record)


def _write(record: dict):
    try:
        SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _lock:
            with open(SNAPSHOT_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass
