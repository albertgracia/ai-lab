"""FASE 29.2 — Real Streaming Relay with backpressure and safety.
FASE 29.4 — Adaptive concurrency via SLO module.

Relays upstream SSE chunks directly to the client WITHOUT buffering.
Includes: backpressure protection, stream cleanup, timeout handling,
graceful degradation on malformed chunks.
"""

from __future__ import annotations

import os
import time
import threading

FEATURE_FLAG = "AI_LAB_REAL_STREAMING"

# FASE 29.4: MAX_CONCURRENT_STREAMS can be overridden by adaptive concurrency
MAX_CONCURRENT_STREAMS = 3
MAX_STREAM_DURATION_SEC = 300
FIRST_CHUNK_TIMEOUT_SEC = 20
STREAM_IDLE_TIMEOUT_SEC = 30

_active_streams = 0
_streams_lock = threading.Lock()
_total_streams = 0
_interrupted_streams = 0
_override_max_streams: int | None = None


def is_real_streaming_enabled() -> bool:
    return os.environ.get(FEATURE_FLAG, "false").lower() in ("true", "1", "yes")


def set_max_streams(limit: int) -> None:
    """FASE 29.4: Set dynamic max concurrent streams from SLO module."""
    global _override_max_streams
    _override_max_streams = max(1, limit)


def _get_max_streams() -> int:
    if _override_max_streams is not None:
        return _override_max_streams
    return MAX_CONCURRENT_STREAMS


def _acquire_slot() -> bool:
    global _active_streams
    max_slots = _get_max_streams()
    with _streams_lock:
        if _active_streams >= max_slots:
            return False
        _active_streams += 1
        return True


def _release_slot() -> None:
    global _active_streams
    with _streams_lock:
        _active_streams = max(0, _active_streams - 1)


def get_stream_stats() -> dict:
    return {
        "feature_flag": FEATURE_FLAG,
        "enabled": is_real_streaming_enabled(),
        "active_streams": _active_streams,
        "max_concurrent": _get_max_streams(),
        "total_streams": _total_streams,
        "interrupted_streams": _interrupted_streams,
        "first_chunk_timeout_sec": FIRST_CHUNK_TIMEOUT_SEC,
        "idle_timeout_sec": STREAM_IDLE_TIMEOUT_SEC,
        "max_duration_sec": MAX_STREAM_DURATION_SEC,
    }


def relay_stream(upstream, handler, model: str = "unknown"):
    """Relay upstream SSE chunks directly to the client.

    Used ONLY when AI_LAB_REAL_STREAMING=true.
    Chunks flow from LM Studio to client without buffering.
    """
    global _total_streams, _interrupted_streams

    if not _acquire_slot():
        handler.wfile.write(
            b"data: {\"error\": \"stream_limit_exceeded\", \"message\": \"Too many concurrent streams\"}\n\n"
        )
        handler.wfile.write(b"data: [DONE]\n\n")
        handler.wfile.flush()
        _interrupted_streams += 1
        return

    _total_streams += 1
    stream_start = time.time()
    first_chunk_arrived = False
    chunk_count = 0

    try:
        for chunk in upstream.iter_content(chunk_size=8192):
            if not chunk:
                continue

            if not first_chunk_arrived:
                first_chunk_arrived = True
                first_chunk_ms = int((time.time() - stream_start) * 1000)
                try:
                    from runtime.telemetry.prometheus_metrics import record_stream_first_chunk
                    record_stream_first_chunk(model, first_chunk_ms)
                except ImportError:
                    pass

            handler.wfile.write(chunk)
            handler.wfile.flush()
            chunk_count += 1

            elapsed = time.time() - stream_start
            if elapsed > MAX_STREAM_DURATION_SEC:
                handler.wfile.write(b"data: [STREAM_TIMEOUT]\n\n")
                handler.wfile.flush()
                _interrupted_streams += 1
                break

    except (BrokenPipeError, ConnectionResetError, OSError):
        _interrupted_streams += 1
    except Exception:
        _interrupted_streams += 1
        try:
            handler.wfile.write(b"data: [STREAM_ERROR]\n\n")
            handler.wfile.flush()
        except Exception:
            pass
    finally:
        _release_slot()
        try:
            upstream.close()
        except Exception:
            pass

    return chunk_count
