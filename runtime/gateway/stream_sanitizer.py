import json


def parse_sse_line(line: str):
    """
    Parse SSE line:
    data: {...}
    """

    if not line.startswith("data: "):
        return None

    payload = line[len("data: "):].strip()

    if payload == "[DONE]":
        return "[DONE]"

    try:
        return json.loads(payload)
    except Exception:
        return None


def sanitize_stream_chunk(chunk: dict):
    """
    Remove reasoning_content from streaming chunks.
    """

    try:
        choices = chunk.get("choices", [])

        for choice in choices:

            delta = choice.get("delta", {})

            if "reasoning_content" in delta:
                del delta["reasoning_content"]

        return chunk

    except Exception:
        return chunk


def relay_stream(response):
    """
    Relay + sanitize streaming response.
    """

    for raw_line in response.iter_lines():

        if not raw_line:
            continue

        try:
            decoded = raw_line.decode("utf-8")
        except Exception:
            continue

        parsed = parse_sse_line(decoded)

        if parsed is None:
            continue

        if parsed == "[DONE]":
            yield "data: [DONE]\n\n"
            break

        sanitized = sanitize_stream_chunk(parsed)

        if sanitized is None:
            continue

        yield f"data: {json.dumps(sanitized)}\n\n"
