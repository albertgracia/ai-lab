"""Session Metrics."""
import time
from threading import Lock

_lock = Lock()
_session_durations = []
_orphan_count = 0
_total_sessions = 0
_active_sessions = 0


def record_session(duration_ms: float = 0):
    global _total_sessions, _active_sessions
    with _lock:
        _total_sessions += 1
        _active_sessions += 1


def end_session(duration_ms: float):
    global _active_sessions
    with _lock:
        _active_sessions -= 1
        if _active_sessions < 0: _active_sessions = 0
        _session_durations.append(duration_ms)
        if len(_session_durations) > 200: _session_durations.pop(0)


def get_session_metrics():
    with _lock:
        avg_d = sum(_session_durations) / len(_session_durations) if _session_durations else 0
        return {"total_sessions": _total_sessions, "active_sessions": _active_sessions, "average_duration_ms": round(avg_d, 1)}
