#!/usr/bin/env python3
"""FASE 39A.2 — OpenCode Gateway contract tests.

Contract-only validation (no functional runtime changes).
"""

from __future__ import annotations

import json
import urllib.request

import runtime.gateway.openai_gateway as gateway
from runtime.gateway.tool_call_parser import (
    filter_dangerous_tool_calls,
    repair_tool_call_arguments,
)


BASE_URL = "http://127.0.0.1:8008"
ALLOWED_FINISH = {"stop", "length", "tool_calls", "content_filter"}


def _http_json(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        method=method,
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8")
        return resp.status, json.loads(raw)


def test_chatcompletion_contract_live_gateway() -> None:
    status, data = _http_json(
        "POST",
        "/v1/chat/completions",
        {
            "model": "ailab-router/coding",
            "messages": [{"role": "user", "content": "Responde solo OK"}],
            "temperature": 0,
            "stream": False,
        },
    )
    assert status == 200
    assert isinstance(data.get("id"), str)
    assert data.get("object") == "chat.completion"
    assert isinstance(data.get("created"), int)
    assert isinstance(data.get("model"), str)
    assert isinstance(data.get("choices"), list) and data["choices"]

    c0 = data["choices"][0]
    assert isinstance(c0.get("index"), int)
    assert isinstance(c0.get("message"), dict)
    assert c0["message"].get("role") == "assistant"
    assert isinstance(c0["message"].get("content", ""), str)
    assert c0.get("finish_reason") in ALLOWED_FINISH

    usage = data.get("usage")
    assert isinstance(usage, dict)
    assert isinstance(usage.get("prompt_tokens"), int)
    assert isinstance(usage.get("completion_tokens"), int)
    assert isinstance(usage.get("total_tokens"), int)


def test_models_contract_live_gateway() -> None:
    status, data = _http_json("GET", "/v1/models")
    assert status == 200
    assert data.get("object") == "list"
    assert isinstance(data.get("data"), list)
    assert len(data["data"]) >= 1
    for item in data["data"]:
        assert isinstance(item, dict)
        assert isinstance(item.get("id"), str) and item["id"].strip()
        # Gateway currently proxies OpenAI model items with object="model"
        assert item.get("object") == "model"


def test_tool_calls_not_invented_from_plain_content() -> None:
    # If upstream content has no tool syntax, parser must not invent tool calls.
    message = {"role": "assistant", "content": "OK"}
    calls = gateway.extract_tool_calls_from_message(message)
    assert calls == []


def test_tool_call_repair_and_dangerous_filter() -> None:
    malformed = {
        "id": "toolcall-1",
        "type": "function",
        "function": {
            "name": "bash",
            "arguments": {"command": "sudo systemctl restart ailab-gateway"},
        },
    }
    repaired = repair_tool_call_arguments(malformed)
    assert isinstance(repaired["function"]["arguments"], str)

    filtered, blocked = filter_dangerous_tool_calls([repaired])
    assert filtered == []
    assert isinstance(blocked, str) and blocked


def test_shutdown_reject_helper_returns_503_shape() -> None:
    class DummyHandler:
        def __init__(self) -> None:
            self.code = None
            self.payload = None

        def _send_json(self, code: int, payload: dict) -> None:
            self.code = code
            self.payload = payload

    old_flag = gateway._shutting_down
    try:
        gateway._shutting_down = True
        dummy = DummyHandler()
        rejected = gateway.GatewayHandler._reject_if_shutting_down(dummy)
        assert rejected is True
        assert dummy.code == 503
        assert isinstance(dummy.payload, dict)
        assert dummy.payload.get("error") == "shutting_down"
    finally:
        gateway._shutting_down = old_flag
