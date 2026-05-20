import json
import time
from datetime import datetime as _dt
from pathlib import Path

_AUDIT_BASE = Path("/opt/ai-lab/runtime/state")
AUDIT_LOG = _AUDIT_BASE / "governance_audit.jsonl"


def _audit_path() -> Path:
    """FASE 24: daily shard rotation — one file per day."""
    today = _dt.now().strftime("%Y-%m-%d")
    return _AUDIT_BASE / f"governance_audit-{today}.jsonl"


def audit_event(event_type: str, payload: dict):
    _AUDIT_BASE.mkdir(parents=True, exist_ok=True)

    event = {
        "timestamp": int(time.time()),
        "event_type": event_type,
        "payload": payload,
    }

    # FASE 24: write to daily shard + legacy file (compat)
    log_path = _audit_path()
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    return event


if __name__ == "__main__":
    audit_event(
        "governance_test",
        {"status": "ok"}
    )

    print(f"WROTE: {AUDIT_LOG}")
