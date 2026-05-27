"""Incident deduplication helper for watchdog events.

Deterministic dedup_key generation and Qdrant lookup.
Fail-safe: all public functions catch exceptions and return safe defaults.
"""

import hashlib
import time

DEDUP_WINDOWS = {
    "cluster_degraded": 86400,
    "service_degraded": 3600,
}


def _has_requests():
    try:
        import requests
        return requests
    except ImportError:
        return None


def normalize_message(message: str) -> str:
    if not message:
        return ""
    return " ".join(str(message).lower().split()).strip()


def build_dedup_key(
    event_type: str,
    source: str,
    severity: str,
    message: str,
    service: str = "",
) -> str:
    raw = f"{event_type}|{source}|{severity}|{service}|{normalize_message(message)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _check_dedup_qdrant(dedup_key: str, event_type: str) -> dict:
    """Query Qdrant for existing non-archived incident with same dedup_key."""
    req = _has_requests()
    if not req:
        return {"deduped": False}

    window = DEDUP_WINDOWS.get(event_type)
    if window is None:
        return {"deduped": False}

    cutoff = time.time() - window
    try:
        from runtime.memory.qdrant_store import QDRANT_HOST
        body = {
            "filter": {
                "must": [
                    {"key": "dedup_key", "match": {"value": dedup_key}},
                    {"key": "timestamp", "range": {"gte": cutoff}},
                ],
                "must_not": [
                    {"key": "archived", "match": {"value": True}},
                ],
            },
            "limit": 1,
            "with_payload": True,
            "with_vector": False,
        }
        resp = req.post(f"{QDRANT_HOST}/collections/incidents/points/scroll", json=body, timeout=3)
        if resp.status_code == 200:
            points = resp.json().get("result", {}).get("points", [])
            if points:
                return {"deduped": True, "id": points[0]["id"], "ts": points[0]["payload"].get("timestamp")}
    except Exception:
        pass
    return {"deduped": False}


def check_and_tag(
    event_type: str,
    source: str,
    severity: str,
    message: str,
    service: str = "",
) -> dict:
    """Check if a duplicate exists within the dedup window.

    Returns a dict with:
      - deduped: bool
      - dedup_key: str
      - action: "skipped" | "new"
      - existing_id: str | None

    Fail-safe: if Qdrant is unavailable, returns deduped=False, action="new".
    """
    dedup_key = build_dedup_key(event_type, source, severity, message, service)
    result = {
        "deduped": False,
        "dedup_key": dedup_key,
        "action": "new",
        "existing_id": None,
    }

    if event_type not in DEDUP_WINDOWS:
        return result

    qr = _check_dedup_qdrant(dedup_key, event_type)
    if qr.get("deduped"):
        result["deduped"] = True
        result["action"] = "skipped"
        result["existing_id"] = qr.get("id")

    return result
