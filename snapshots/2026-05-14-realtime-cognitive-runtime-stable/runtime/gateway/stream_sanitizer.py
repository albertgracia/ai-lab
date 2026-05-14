"""
AI-LAB STREAM SANITIZER
Removes reasoning traces and empty chunks from LM Studio streams.
"""

import json


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

            # eliminar reasoning_content si existe
            delta.pop("reasoning_content", None)

            # si no hay contenido real → ignorar chunk
            has_content = bool(delta.get("content"))
            has_role = bool(delta.get("role"))

            finish_reason = choices[0].get("finish_reason")

            if not has_content and not has_role and not finish_reason:
                continue

            cleaned = json.dumps(obj, ensure_ascii=False)

            handler.wfile.write(
                f"data: {cleaned}\n\n".encode("utf-8")
            )
            handler.wfile.flush()

        except Exception:
            continue
