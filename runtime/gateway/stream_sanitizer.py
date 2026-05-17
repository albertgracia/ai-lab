"""
AI-LAB STREAM SANITIZER
Removes reasoning traces and empty chunks from LM Studio streams.
"""

import json

from runtime.gateway.tool_call_parser import parse_tool_calls_from_text


def relay_stream(upstream, handler):
    """
    Relay OpenAI-compatible SSE stream while:
    - removing reasoning_content
    - dropping empty chunks
    - preserving delta.content
    """

    for raw_line in upstream.iter_lines():

        if not raw_line:
            continue

        line = raw_line.decode("utf-8")

        if not line.startswith("data: "):
            continue

        payload = line[6:].strip()

        if payload == "[DONE]":
            handler.wfile.write(b"data: [DONE]\n\n")
            handler.wfile.flush()
            break

        try:
            obj = json.loads(payload)

            choices = obj.get("choices", [])

            if not choices:
                continue

            delta = choices[0].get("delta", {})

            reasoning = delta.get("reasoning_content")
            tool_calls = parse_tool_calls_from_text(reasoning if isinstance(reasoning, str) else None)
            if not tool_calls and isinstance(delta.get("content"), str):
                tool_calls = parse_tool_calls_from_text(delta.get("content"))
            if tool_calls:
                delta["tool_calls"] = tool_calls
                delta["content"] = None

            # eliminar reasoning_content si existe
            delta.pop("reasoning_content", None)

            # si no hay contenido real → ignorar chunk
            has_content = bool(delta.get("content"))
            has_role = bool(delta.get("role"))
            has_tool_calls = bool(delta.get("tool_calls"))

            finish_reason = choices[0].get("finish_reason")

            if not has_content and not has_role and not has_tool_calls and not finish_reason:
                continue

            cleaned = json.dumps(obj, ensure_ascii=False)

            handler.wfile.write(
                f"data: {cleaned}\n\n".encode("utf-8")
            )
            handler.wfile.flush()

        except Exception:
            continue
