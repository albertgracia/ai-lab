"""Session Affinity — observe preferred models per session.

Tracks per-session model affinity WITHOUT forcing routing decisions yet.
The optimiser can later use this data to suggest model preferences,
but for now it is purely observational.

Data structure:
  SESSION_AFFINITY[session_id] = {
      "preferred_model": "qwen2.5-coder-32b-instruct",
      "confidence": 0.82,
      "last_success": 1747400000,
      "success_count": 12,
      "failures": 1,
  }
"""

import time
from collections import defaultdict
from threading import Lock

_lock = Lock()
SESSION_AFFINITY: dict[str, dict] = {}


def record_success(session_id: str, model: str):
    with _lock:
        aff = SESSION_AFFINITY.setdefault(session_id, {"preferred_model": model, "confidence": 0.0, "last_success": 0, "success_count": 0, "failures": 0})
        aff["success_count"] += 1
        aff["last_success"] = int(time.time())
        total = aff["success_count"] + aff["failures"]
        aff["confidence"] = round(aff["success_count"] / max(total, 1), 3)
        # Update preferred model if this one has more successes
        if aff["success_count"] > (aff.get("_best_count", 0) or 0):
            aff["preferred_model"] = model
            aff["_best_count"] = aff["success_count"]


def record_failure(session_id: str, model: str):
    with _lock:
        aff = SESSION_AFFINITY.setdefault(session_id, {"preferred_model": model, "confidence": 0.0, "last_success": 0, "success_count": 0, "failures": 0})
        aff["failures"] += 1
        total = aff["success_count"] + aff["failures"]
        aff["confidence"] = round(aff["success_count"] / max(total, 1), 3)


def get_affinity(session_id: str) -> dict | None:
    with _lock:
        return SESSION_AFFINITY.get(session_id)


def snapshot() -> dict:
    with _lock:
        return {
            "total_sessions": len(SESSION_AFFINITY),
            "affinities": {k: {"preferred": v["preferred_model"], "confidence": v["confidence"], "successes": v["success_count"], "failures": v["failures"]} for k, v in SESSION_AFFINITY.items()},
        }
