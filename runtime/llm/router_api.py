import sys
sys.path.insert(0, "/opt/ai-lab")

import time
from typing import Any, Dict

import requests

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import json as json_mod

from runtime.llm.model_router import select_node
from runtime.state.system_state import build_system_state

from runtime.agent.selective_context import (
    build_selective_context
)

# ── cognitive telemetry (FASE 8.9) ─────────────────────────────────
try:
    from runtime.cognitive.cognitive_metrics import increment as _cog_inc, set_metric as _cog_set
    _HAVE_COGNITIVE = True
except ImportError:
    _cog_inc = _cog_set = None
    _HAVE_COGNITIVE = False

# ── optional: working memory + context shaper (FASE 8.7) ────────────
try:
    from runtime.memory.working_memory import get_session
    _HAVE_WORKING_MEMORY = True
except ImportError:
    get_session = None  # type: ignore[assignment]
    _HAVE_WORKING_MEMORY = False

try:
    from runtime.agent.context_shaper import shape_context
    _HAVE_CONTEXT_SHAPER = True
except ImportError:
    shape_context = None  # type: ignore[assignment]
    _HAVE_CONTEXT_SHAPER = False

app = FastAPI(title="AI-LAB Router API", servers=[{"url": "http://192.168.1.30:8083", "description": "AI-LAB Router API"}], version="1.0.0", description="Router cognitivo del AI-LAB. Proporciona enrutamiento capability-aware a nodos de inferencia GPU.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "object": "list",
        "data": [
            {"id": "ailab-router/auto", "object": "model"},
            {"id": "ailab-router/fast", "object": "model"},
            {"id": "ailab-router/reasoning", "object": "model"},
            {"id": "ailab-router/coding", "object": "model"},
        ],
    }


BASE_SYSTEM_CONTEXT = """
Eres el AI-LAB runtime assistant de Albert.
Responde siempre en espanol.

USA EL CONTEXTO PROPORCIONADO como tu fuente de verdad.
Especialmente el bloque 'CURRENT AI-LAB RUNTIME (HARD FACTS)' contiene datos reales de infraestructura.

NORMAS:
- Basa tus respuestas en el contexto adjunto.
- Si un dato concreto no aparece en el contexto, puedes decir que no esta disponible, PERO primero revisa bien el bloque HARD FACTS.
- NO inventes nombres de servicios, modelos, GPUs ni arquitecturas que no esten en el contexto.
- NO uses ejemplos genericos de IA (NVIDIA, BERT, RoBERTa) salvo peticion explicita.
- Distingue entre lo que SABES (por el contexto) y lo que SUPONES.
- Responde directamente. No uses thinking ni reasoning_content.
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

                if (
                    isinstance(item, dict)
                    and item.get("type") == "text"
                ):
                    parts.append(item.get("text", ""))

    return "\n".join(parts)




@app.get("/api/v1/tools")
@app.get("/api/tools")
@app.get("/api/v1/functions")
def list_tools():
    return {"data": []}


@app.get("/api/v1/tools/")
@app.get("/api/tools/")
@app.get("/api/v1/functions/")
def list_tools_slash():
    return {"data": []}


@app.get("/models")
@app.get("/api/models")
def api_models():
    import time
    return {
        "object": "list",
        "data": [
            {"id": "ailab-router/auto", "object": "model", "created": int(time.time()), "owned_by": "ai-lab"},
            {"id": "ailab-router/fast", "object": "model", "created": int(time.time()), "owned_by": "ai-lab"},
            {"id": "ailab-router/reasoning", "object": "model", "created": int(time.time()), "owned_by": "ai-lab"},
            {"id": "ailab-router/coding", "object": "model", "created": int(time.time()), "owned_by": "ai-lab"},
        ],
    }


@app.get("/api/config")
def api_config():
    return {"status": "ok"}


@app.get("/api/version")
def api_version():
    return {"version": "1.0.0", "ai-lab": "cognitive-runtime"}


@app.get("/api/v1/configs/banners")
def api_banners():
    return {"banners": []}


@app.get("/api/usage")
def api_usage():
    return {"usage": {"completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0}}


@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat_completions(request: Request):

    payload = await request.json()

    build_system_state()

    requested_model = payload.get(
        "model",
        "ailab-router/auto"
    )

    request_text = extract_request_text(payload)

    capability = capability_from_model(
        requested_model
    )

    node = select_node(
        request_text,
        capability=capability
    )

    upstream_url = (
        f"http://{node['host']}:{node['port']}"
        "/v1/chat/completions"
    )

    messages = payload.get("messages", [])

    # ── working memory + context shaper (FASE 8.7) ──────────────────
    wm = None
    if _HAVE_WORKING_MEMORY and _HAVE_CONTEXT_SHAPER:
        session_id = request.headers.get("X-AI-LAB-Session", request.client.host if request.client else "default")
        wm = get_session(session_id)
        wm.add_turn("user", request_text)
        task = node.get("capability", "general")
        wm.set_task(task)

        agent_context = shape_context(task, node.get("model", ""), wm)
    else:
        agent_context = build_selective_context(request_text)

    context_summary = "\\n".join(
        line for line in agent_context.splitlines()
        if line.startswith("Agent:")
        or line.startswith("Reasoning:")
        or line.startswith("Complexity:")
        or line.startswith("Workflow:")
        or line.startswith("Domains:")
        or line.startswith("Multi Agent:")
    )

    system_prompt = (
        BASE_SYSTEM_CONTEXT
        + "\\n\\n"
        + "Resumen operativo interno del router AI-LAB. "
        + "No copies este resumen; úsalo solo para orientar la respuesta.\\n"
        + context_summary
    )

    final_instruction = (
        "Responde únicamente a esta petición del usuario, en español, "
        "sin copiar contexto interno ni prompts.\\n\\n"
        + request_text
    )

    payload["messages"] = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": final_instruction
        }
    ]

    upstream_payload = dict(payload)

    upstream_payload["model"] = node["model"]

    upstream_payload.setdefault(
        "max_tokens",
        2500 if capability == "reasoning" or node.get("capability") == "reasoning" else (600 if capability == "fast" or node.get("capability") == "fast" else 1200)
    )

    upstream_payload.setdefault(
        "temperature",
        0.1 if capability == "fast" or node.get("capability") == "fast" else 0.2
    )

    # Only set reasoning effort for non-reasoning models
    if "reasoning" not in upstream_payload.get("model", "") and "reasoning" not in upstream_payload.get("model", ""):
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

            async def sanitize_stream():
                for raw_line in upstream.iter_lines():
                    if not raw_line:
                        continue
                    line = raw_line.decode("utf-8", errors="replace")
                    if not line.startswith("data: "):
                        yield line + "\n"
                        continue
                    payload = line[6:].strip()
                    if payload == "[DONE]":
                        yield "data: [DONE]\n\n"
                        break
                    try:
                        obj = json_mod.loads(payload)
                        choices = obj.get("choices", [])
                        for choice in choices:
                            delta = choice.get("delta", {})
                            if "reasoning_content" in delta:
                                rc = delta.pop("reasoning_content")
                                if not delta.get("content"):
                                    delta["content"] = rc
                                else:
                                    delta["content"] = rc + "\n" + delta["content"]
                        yield f"data: {json_mod.dumps(obj, ensure_ascii=False)}\n\n"
                    except Exception:
                        yield line + "\n"

            try:
                from runtime.routing.routing_history import record_route_result as _rrr
                _rrr(task_type=node["capability"], model=node["model"],
                     node=node["name"], host=node["host"],
                     latency_ms=0, success=True, stream=True, failover=False)
            except ImportError:
                pass

            return StreamingResponse(
                sanitize_stream(),
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

        content = upstream.json()
        choices = content.get("choices", [])
        for choice in choices:
            msg = choice.get("message", {})
            if "reasoning_content" in msg:
                rc = msg.pop("reasoning_content")
                if not msg.get("content"):
                    msg["content"] = rc

        try:
            from runtime.routing.routing_history import record_route_result as _rrr
            _rrr(task_type=node["capability"], model=node["model"],
                 node=node["name"], host=node["host"],
                 latency_ms=0, success=True, stream=False, failover=False)
        except ImportError:
            pass

        return JSONResponse(
            status_code=upstream.status_code,
            content=content,
            headers=headers,
        )

    except Exception as exc:

        try:
            from runtime.routing.routing_history import record_route_result as _rrr
            _rrr(task_type=node["capability"] if isinstance(node, dict) else "unknown",
                 model=node.get("model", "unknown") if isinstance(node, dict) else "unknown",
                 node=node.get("name", "unknown") if isinstance(node, dict) else "unknown",
                 host=node.get("host", "unknown") if isinstance(node, dict) else "unknown",
                 latency_ms=0, success=False, stream=False, failover=False, error=str(exc))
        except ImportError:
            pass

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
