import json
import time
from pathlib import Path

AUDIT_LOG = Path("/opt/ai-lab/runtime/state/governance_audit.jsonl")


def audit_event(event_type: str, payload: dict):
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)

    event = {
        "timestamp": int(time.time()),
        "event_type": event_type,
        "payload": payload,
    }

    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    return event


if __name__ == "__main__":
    audit_event(
        "governance_test",
        {"status": "ok"}
    )

    print(f"WROTE: {AUDIT_LOG}")
