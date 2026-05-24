"""LMSTUDIO-CONTRACT-TESTS-01 burn-in.

Runs a small sequence of real calls against LM Studio to validate:
- /v1/models shape and presence/absence
- non-stream Qwen and Llama
- streaming Llama produces SSE chunks

This is NOT a load test. It is bounded and fast.

Run:
  python3 tests/burnin_lmstudio_contract_01.py
"""

from __future__ import annotations

import os
import time


LMSTUDIO_BASE_URL = os.getenv("AI_LAB_LMSTUDIO_URL", "http://192.168.1.50:1234/v1").rstrip("/")
MODELS_URL = f"{LMSTUDIO_BASE_URL}/models"
CHAT_URL = f"{LMSTUDIO_BASE_URL}/chat/completions"

from runtime.models.model_registry import (
    DEPRECATED_QWEN_14B_ALIAS as MODEL_DEPRECATED,
    MODEL_LLAMA_8B as MODEL_LLAMA,
    MODEL_QWEN_14B as MODEL_QWEN,
)


def _requests():
    import requests  # type: ignore

    return requests


def _chat_payload(model: str, *, stream: bool) -> dict:
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


def main() -> int:
    requests = _requests()

    print(f"LM Studio base: {LMSTUDIO_BASE_URL}")

    # 1) /models
    t0 = time.time()
    r = requests.get(MODELS_URL, timeout=3)
    dt = (time.time() - t0) * 1000.0
    if r.status_code != 200:
        print(f"FAIL /models status={r.status_code} latency_ms={dt:.1f}")
        return 2
    data = r.json() or {}
    ids = [d.get("id") for d in (data.get("data") or []) if isinstance(d, dict) and d.get("id")]
    print(f"OK /models latency_ms={dt:.1f} models={len(ids)}")
    print("models:")
    for mid in ids:
        print(f"- {mid}")
    if MODEL_QWEN not in ids:
        print(f"FAIL missing canonical: {MODEL_QWEN}")
        return 3
    if MODEL_LLAMA not in ids:
        print(f"FAIL missing canonical: {MODEL_LLAMA}")
        return 4
    if MODEL_DEPRECATED in ids:
        print(f"FAIL deprecated alias present: {MODEL_DEPRECATED}")
        return 5

    # 2) non-stream Qwen
    t0 = time.time()
    r = requests.post(CHAT_URL, json=_chat_payload(MODEL_QWEN, stream=False), timeout=15)
    dt = (time.time() - t0) * 1000.0
    r.raise_for_status()
    out = r.json() or {}
    model = out.get("model")
    print(f"OK non-stream qwen latency_ms={dt:.1f} model={model}")
    if model != MODEL_QWEN:
        print("FAIL non-stream qwen returned unexpected model")
        return 6

    # 3) non-stream Llama
    t0 = time.time()
    r = requests.post(CHAT_URL, json=_chat_payload(MODEL_LLAMA, stream=False), timeout=15)
    dt = (time.time() - t0) * 1000.0
    r.raise_for_status()
    out = r.json() or {}
    model = out.get("model")
    print(f"OK non-stream llama latency_ms={dt:.1f} model={model}")
    if model != MODEL_LLAMA:
        print("FAIL non-stream llama returned unexpected model")
        return 7

    # 4) streaming llama
    t0 = time.time()
    seen = 0
    with requests.post(CHAT_URL, json=_chat_payload(MODEL_LLAMA, stream=True), stream=True, timeout=20) as r:
        r.raise_for_status()
        for raw in r.iter_lines(decode_unicode=True):
            if not raw:
                continue
            line = raw.strip()
            if line.startswith("data:"):
                seen += 1
            if seen >= 3:
                break
    dt = (time.time() - t0) * 1000.0
    print(f"OK stream llama latency_ms={dt:.1f} data_chunks={seen}")
    if seen <= 0:
        print("FAIL streaming produced no data chunks")
        return 8

    print("OK burnin lmstudio contract 01")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
