"""AI-LAB Event Bus - Structured runtime events for SSE streaming."""
import time
import json
import threading
from collections import deque

EVENT_TYPES = [
    "node_online", "node_offline", "model_selected",
    "request_started", "request_finished", "agent_invoked",
    "session_created", "routing_decision", "gpu_overheat",
]

_event_history = deque(maxlen=200)
_event_listeners = []
_lock = threading.Lock()


def emit(event_type: str, data: dict):
    if event_type not in EVENT_TYPES:
        event_type = "custom"
    event = {
        "event": event_type,
        "data": data,
        "timestamp": int(time.time() * 1000),
        "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with _lock:
        _event_history.append(event)
        for listener in _event_listeners:
            try:
                listener(event)
            except:
                pass
    return event


def subscribe(callback):
    with _lock:
        _event_listeners.append(callback)
    return lambda: unsubscribe(callback)


def unsubscribe(callback):
    with _lock:
        if callback in _event_listeners:
            _event_listeners.remove(callback)


def get_history(limit: int = 50):
    with _lock:
        return list(_event_history)[-limit:]


def get_stats():
    with _lock:
        return {
            "total_events": len(_event_history),
            "active_listeners": len(_event_listeners),
            "event_types": {t: sum(1 for e in _event_history if e["event"] == t) for t in EVENT_TYPES},
        }
