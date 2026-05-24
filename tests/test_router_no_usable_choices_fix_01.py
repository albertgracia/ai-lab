"""ROUTER-NO-USABLE-CHOICES-FIX-01 tests.

Focus:
- content-only choice is treated as usable
- tool_calls choice is treated as usable
- empty choices is not usable
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_msg_has_usable_output_content_only() -> None:
    from runtime.llm.openai_response_utils import msg_has_usable_output

    assert msg_has_usable_output({"content": "hola", "tool_calls": []}) is True
    assert msg_has_usable_output({"content": "   ", "tool_calls": []}) is False


def test_msg_has_usable_output_tool_calls() -> None:
    from runtime.llm.openai_response_utils import msg_has_usable_output

    assert msg_has_usable_output({"content": None, "tool_calls": [{"id": "1"}]}) is True
    assert msg_has_usable_output({"tool_calls": [{"id": "1"}], "content": ""}) is True


def test_msg_has_usable_output_rejects_non_dict() -> None:
    from runtime.llm.openai_response_utils import msg_has_usable_output

    assert msg_has_usable_output(None) is False
    assert msg_has_usable_output("x") is False  # type: ignore[arg-type]
