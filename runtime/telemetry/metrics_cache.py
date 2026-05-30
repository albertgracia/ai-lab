import time
import threading
from typing import Any, Callable

_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, tuple[float, Any]] = {}

def get_cached(key: str, ttl: float, builder: Callable[[], str], fallback: str = "") -> str:
    now = time.time()
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry and (now - entry[0]) < ttl:
            return entry[1]
    try:
        value = builder()
        with _CACHE_LOCK:
            _CACHE[key] = (now, value)
        return value
    except Exception:
        with _CACHE_LOCK:
            entry = _CACHE.get(key)
            if entry is not None:
                return entry[1]
        return fallback

def invalidate(key: str) -> None:
    with _CACHE_LOCK:
        _CACHE.pop(key, None)

def clear() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()
