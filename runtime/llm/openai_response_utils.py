"""OpenAI-compatible response helpers.

Small, dependency-free utilities used by router/gateway layers.
"""

from __future__ import annotations

from typing import Any


def msg_has_usable_output(msg: dict[str, Any] | None) -> bool:
    """Return True if a choice message contains usable output.

    Usable means:
    - non-empty string content, OR
    - tool_calls present (even if content is empty/None).
    """
    if not isinstance(msg, dict):
        return False
    tc = msg.get("tool_calls")
    if isinstance(tc, list) and len(tc) > 0:
        return True
    c = msg.get("content")
    return isinstance(c, str) and bool(c.strip())
