"""LMSTUDIO-CONTRACT-TESTS-01.

Real contract tests against LM Studio (192.168.1.50).

Hard rules:
- If LM Studio is unavailable, tests SKIP (not fail).
- Tight timeouts; never hang pytest.
- Validate canonical models only; deprecated alias must be absent.
"""

from __future__ import annotations

import os
import time
from typing import Any

import pytest


LMSTUDIO_BASE_URL = os.getenv("AI_LAB_LMSTUDIO_URL", "http://192.168.1.50:1234/v1").rstrip("/")
MODELS_URL = f"{LMSTUDIO_BASE_URL}/models"
CHAT_URL = f"{LMSTUDIO_BASE_URL}/chat/completions"

from runtime.models.model_registry import (
    DEPRECATED_QWEN_14B_ALIAS as MODEL_DEPRECATED,
    MODEL_LLAMA_8B as MODEL_LLAMA,
    MODEL_QWEN_14B as MODEL_QWEN,
)


def _requests():
    try:
        import requests  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"requests_not_available:{exc}")
    return requests


def _lmstudio_available(timeout_s: float = 2.0) -> bool:
    requests = _requests()
    try:
        r = requests.get(MODELS_URL, timeout=timeout_s)
        return r.status_code == 200
    except Exception:
        return False


def _skip_if_unavailable():
    if not _lmstudio_available():
        pytest.skip(f"LM Studio unavailable at {LMSTUDIO_BASE_URL}")


def _list_model_ids(timeout_s: float = 3.0) -> list[str]:
    requests = _requests()
    r = requests.get(MODELS_URL, timeout=timeout_s)
    r.raise_for_status()
    data = r.json() or {}
    items = data.get("data") or []
    ids: list[str] = []
    for it in items:
        if isinstance(it, dict) and it.get("id"):
            ids.append(str(it.get("id")))
    return ids


def _chat_payload(model: str, *, stream: bool) -> dict[str, Any]:
    return {
        "model": model,
        "stream": bool(stream),
        "messages": [
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": "Reply with OK."},
        ],
        "max_tokens": 16,
        "temperature": 0.0,
    }


def test_models_endpoint_responds():
    _skip_if_unavailable()
    ids = _list_model_ids()
    assert isinstance(ids, list)
    assert len(ids) > 0


def test_canonical_models_present_and_deprecated_absent():
    _skip_if_unavailable()
    ids = _list_model_ids()
    assert MODEL_QWEN in ids
    assert MODEL_LLAMA in ids
    assert MODEL_DEPRECATED not in ids


def test_chat_completion_non_stream_qwen_works_and_returns_canonical_model():
    _skip_if_unavailable()
    requests = _requests()
    t0 = time.time()
    r = requests.post(CHAT_URL, json=_chat_payload(MODEL_QWEN, stream=False), timeout=15)
    dt = time.time() - t0
    r.raise_for_status()
    data = r.json() or {}
    assert (data.get("model") or "") == MODEL_QWEN
    assert (data.get("model") or "") != MODEL_DEPRECATED
    # Minimal sanity: we got a completion
    choices = data.get("choices") or []
    assert isinstance(choices, list) and len(choices) >= 1
    assert dt < 15.0


def test_chat_completion_non_stream_llama_works_and_returns_canonical_model():
    _skip_if_unavailable()
    requests = _requests()
    t0 = time.time()
    r = requests.post(CHAT_URL, json=_chat_payload(MODEL_LLAMA, stream=False), timeout=15)
    dt = time.time() - t0
    r.raise_for_status()
    data = r.json() or {}
    assert (data.get("model") or "") == MODEL_LLAMA
    assert (data.get("model") or "") != MODEL_DEPRECATED
    choices = data.get("choices") or []
    assert isinstance(choices, list) and len(choices) >= 1
    assert dt < 15.0


def test_streaming_llama_produces_sse_chunks():
    _skip_if_unavailable()
    requests = _requests()

    # Read a small number of SSE lines and assert we see at least one "data:" chunk.
    payload = _chat_payload(MODEL_LLAMA, stream=True)
    t0 = time.time()
    seen_data = 0
    with requests.post(CHAT_URL, json=payload, stream=True, timeout=20) as r:
        r.raise_for_status()
        for raw in r.iter_lines(decode_unicode=True):
            if not raw:
                continue
            line = raw.strip()
            if line.startswith("data:"):
                seen_data += 1
            if seen_data >= 3:
                break
    dt = time.time() - t0
    assert seen_data > 0
    assert dt < 20.0
