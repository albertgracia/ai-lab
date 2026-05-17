"""Helpers to adapt LM Studio reasoning traces into OpenAI tool calls."""

from __future__ import annotations

import json
import re
from typing import Any

try:
    from runtime.tools.tool_metrics import TOOL_MALFORMED
except ImportError:
    TOOL_MALFORMED = None

_TOOL_CALL_RE = re.compile(
    r"<tool_call>\s*<function=(?P<name>[^>\s]+)>(?P<body>.*?)</function>\s*</tool_call>",
    re.IGNORECASE | re.DOTALL,
)

_PARAMETER_RE = re.compile(
    r"<parameter=(?P<name>[^>\s]+)>\s*(?P<value>.*?)\s*</parameter>",
    re.IGNORECASE | re.DOTALL,
)

_DANGEROUS_COMMAND_MARKERS = (
    "rm -rf",
    "shutdown",
    "reboot",
    "poweroff",
    "mkfs",
    "dd ",
    "sudo",
    "chmod 777",
    "systemctl restart",
    "systemctl stop",
    "systemctl disable",
    "curl -x post",
    "wget ",
    "| sh",
    "| bash",
    "; rm -rf",
    "rm -rf /",
    "rm -rf ~",
    "rm -rf .",
)


def _extract_argument_text(arguments: Any) -> str:
    if isinstance(arguments, str):
        return arguments
    try:
        return json.dumps(arguments, ensure_ascii=False, default=str)
    except Exception:
        return str(arguments)


def tool_call_is_dangerous(tool_call: dict[str, Any]) -> tuple[bool, str]:
    fn = tool_call.get("function") if isinstance(tool_call.get("function"), dict) else {}
    name = str(fn.get("name", "")).strip().lower()
    arguments = _extract_argument_text(fn.get("arguments", "")).lower()

    combined = f"{name} {arguments}".strip()
    if not combined:
        return False, ""

    for marker in _DANGEROUS_COMMAND_MARKERS:
        if marker in combined:
            return True, marker

    return False, ""


def filter_dangerous_tool_calls(tool_calls: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str | None]:
    for tool_call in tool_calls:
        dangerous, marker = tool_call_is_dangerous(tool_call)
        if dangerous:
            return [], marker or "dangerous tool call"
    return tool_calls, None


def parse_tool_calls_from_text(text: str | None) -> list[dict[str, Any]]:
    if not text:
        return []

    tool_calls: list[dict[str, Any]] = []
    for index, match in enumerate(_TOOL_CALL_RE.finditer(text)):
        name = (match.group("name") or "").strip()
        body = (match.group("body") or "").strip()
        arguments: dict[str, Any] = {}
        if body:
            try:
                parsed = json.loads(body)
                if isinstance(parsed, dict):
                    arguments = parsed
                else:
                    raise ValueError("tool call body is not an object")
            except Exception:
                param_matches = list(_PARAMETER_RE.finditer(body))
                if param_matches:
                    for param_match in param_matches:
                        param_name = (param_match.group("name") or "").strip()
                        param_value = (param_match.group("value") or "").strip()
                        if param_name:
                            arguments[param_name] = param_value
                else:
                    arguments = {"text": body}
                    if TOOL_MALFORMED:
                        TOOL_MALFORMED.inc()

        tool_calls.append(
            {
                "id": f"toolcall-{index+1}",
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": json.dumps(arguments, ensure_ascii=False),
                },
            }
        )

    return tool_calls


def parse_tool_calls(reasoning_content: str | None) -> list[dict[str, Any]]:
    return parse_tool_calls_from_text(reasoning_content)


def extract_tool_calls_from_message(message: dict[str, Any]) -> list[dict[str, Any]]:
    reasoning = message.get("reasoning_content")
    if isinstance(reasoning, str):
        tool_calls = parse_tool_calls_from_text(reasoning)
        if tool_calls:
            return tool_calls
    content = message.get("content")
    if isinstance(content, str):
        return parse_tool_calls_from_text(content)
    return []
