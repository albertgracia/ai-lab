import time
from typing import Any, Dict

import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from runtime.llm.model_router import select_node
from runtime.state.system_state import build_system_state

app = FastAPI(title="AI-LAB Router API")


SYSTEM_CONTEXT = """
Eres el router cognitivo del AI-LAB de Albert.

Responde siempre en español.

Cuando el usuario mencione AI-LAB, se refiere a este entorno local:

- nodo Linux principal:
  - hostname: ubuntu-ialab
  - IP: 192.168.1.30

- nodos GPU LM Studio:
  - 192.168.1.50 (RX9070XT)
  - 192.168.1.60 (RX7900XT)

- stack docker:
  - traefik
  - qdrant
  - open-webui
  - ollama
  - portainer

- runtime:
  - /opt/ai-lab/runtime

- estado real:
  - /opt/ai-lab/runtime/state/system_snapshot.json

Normas:
- NO inventes métricas
- NO inventes servicios
- NO inventes estados
- NO inventes módulos
- NO inventes latencias
- usa solo datos reales presentes en contexto
- distingue HECHOS de HIPÓTESIS
- No muestres razonamiento interno.
- No uses thinking.
- Responde directamente en content.
- La respuesta visible es obligatoria.
"""


def openai_model_id(node: Dict[str, Any]) -> str:
    return f"ailab-router/{node['capability']}/{node['model']}"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "ai-lab-router-api"
    }


@app.get("/v1/models")
def models():
    return {
        "object": "list",
        "data": [
            {
                "id": "ailab-router/auto",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "ai-lab",
            },
            {
                "id": "ailab-router/fast",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "ai-lab",
            },
            {
                "id": "ailab-router/reasoning",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "ai-lab",
            },
            {
                "id": "ailab-router/coding",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "ai-lab",
            },
        ],
    }


def capability_from_model(model: str | None):
    if not model:
        return None

    if model.endswith("/fast"):
        return "fast"

    if model.endswith("/reasoning"):
        return "reasoning"

    if model.endswith("/coding"):
        return "coding"

    return None


def extract_request_text(payload: Dict[str, Any]) -> str:
    messages = payload.get("messages", [])
    parts = []

    for msg in messages:
        content = msg.get("content", "")

        if isinstance(content, str):
            parts.append(content)

        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))

    return "\n".join(parts)


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):

    payload = await request.json()

    build_system_state()

    requested_model = payload.get("model", "ailab-router/auto")

    request_text = extract_request_text(payload)

    capability = capability_from_model(requested_model)

    node = select_node(
        request_text,
        capability=capability
    )

    upstream_url = (
        f"http://{node['host']}:{node['port']}/v1/chat/completions"
    )

    messages = payload.get("messages", [])

    payload["messages"] = [
        {
            "role": "system",
            "content": SYSTEM_CONTEXT
        }
    ] + messages

    upstream_payload = dict(payload)

    upstream_payload["model"] = node["model"]

    upstream_payload.setdefault("max_tokens", 1200)
    upstream_payload.setdefault("temperature", 0.2)

    upstream_payload.setdefault(
    "reasoning",
    {"effort": "none"}
)
    headers = {
        "X-AI-LAB-Selected-Node": node["name"],
        "X-AI-LAB-Selected-Host": node["host"],
        "X-AI-LAB-Selected-Model": node["model"],
        "X-AI-LAB-Capability": node["capability"],
    }

    try:

        if upstream_payload.get("stream"):

            upstream = requests.post(
                upstream_url,
                json=upstream_payload,
                stream=True,
                timeout=300,
            )

            return StreamingResponse(
                upstream.iter_content(chunk_size=8192),
                status_code=upstream.status_code,
                media_type=upstream.headers.get(
                    "content-type",
                    "text/event-stream"
                ),
                headers=headers,
            )

        upstream = requests.post(
            upstream_url,
            json=upstream_payload,
            timeout=300
        )

        return JSONResponse(
            status_code=upstream.status_code,
            content=upstream.json(),
            headers=headers,
        )

    except Exception as exc:

        return JSONResponse(
            status_code=502,
            content={
                "error": {
                    "message": str(exc),
                    "type": "ai_lab_router_upstream_error",
                    "selected_node": node,
                }
            },
            headers=headers,
        )
