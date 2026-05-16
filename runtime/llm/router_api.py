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

# ── Qdrant collections init (FASE 10) ─────────────────────────────
try:
    from runtime.memory.qdrant_store import ensure_collections
    ensure_collections()
except ImportError:
    pass

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

# ── LM Studio context limits ──────────────────────────────────────────
# LM Studio en RX9070 (192.168.1.50) carga modelos con n_ctx=16384
# Ajusta LM_STUDIO_MAX_CONTEXT si cambias n_ctx en LM Studio
LM_STUDIO_MAX_CONTEXT = 16384
CHARS_PER_TOKEN = 2.8
CONTEXT_OVERHEAD_TOKENS = 500

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
Eres el copiloto autonomo del AI-LAB de Albert.
Responde siempre en espanol.
Operas en MODO PLAN — puedes leer, analizar, diagnosticar y proponer,
pero NO ejecutar cambios sin confirmacion explicita.

TIENES ACCESO A:
- [HARD_FACTS_BEGIN]..[HARD_FACTS_END] → datos reales del runtime en vivo
- Archivos de contexto (OPENCODE.md, AI_LAB_CONTEXT.md, etc.)
- Tu propio conocimiento del dominio

REGLAS ESTRICTAS DE SECCIONES:

1. En [HARD_FACTS] solo puedes poner datos que aparezcan literalmente
   en el JSON HARD FACTS. No pongas porcentajes, puntuaciones, watchdogs,
   working_memory ni nada que no este en el JSON.

2. No repitas el mismo contenido en varias secciones.

3. En [SELF-CRITIQUE] solo analiza tus errores, no repitas el informe.

4. Si un dato no esta en HARD FACTS, ponlo en [NO DISPONIBLE].

5. Si aparece en pending_implementations, ponlo en [PENDIENTE].

6. TAXONOMIA ESTRICTA — No confundas estas categorias:
   - "model" → solo un modelo de inferencia (qwen2.5-coder-14b-instruct, llama-3.1-8b...)
   - "collection" → solo una coleccion Qdrant (routing_history, cognitive_history...)
   - "service" → solo un servicio systemd (ailab-router, ailab-docs...)
   - "container" → solo un contenedor Docker (traefik, qdrant, open-webui...)
   - "node" → solo una maquina o GPU node (RX9070, RX7900XT...)
   - "ctx" de un modelo NO es "context_size" de una request
   - "qdrant_enabled" solo "si" si HARD FACTS menciona Qdrant o collections
   - "working_memory" solo "activa" si HARD FACTS mentiona working_memory

7. En [SELF-CRITIQUE] debes marcar como posible error cualquier afirmacion
   en [INFERIDO] que use datos no presentes en HARD FACTS.

8. "ctx" de un modelo es su ventana maxima declarada. Nunca lo uses como
   context_size real de la request. Si no aparece "context_budget_used_chars"
   en HARD FACTS: context_size = NO DISPONIBLE, budget_used = NO DISPONIBLE,
   truncation = NO DISPONIBLE.

9. Si no aparece "watchdog" en HARD FACTS: watchdog = NO DISPONIBLE.
   Nunca digas "activo" por inferencia.

10. Si no aparece "health" ni "health_score" en HARD FACTS:
    health = NO DISPONIBLE. Nunca digas "healthy" por inferencia.

11. Si no aparece "latency_ms" en el nodo: no menciones latencia del nodo.

12. En [SELF-CRITIQUE] debes listar cualquier inferencia realizada.
    Nunca digas "no he inferido nada" si existe seccion [INFERIDO].

13. Si [INFERIDO] contiene datos que afectan a estado operacional,
    repitelos en [SELF-CRITIQUE] como "inferencia no verificada".

FORMATO OBLIGATORIO DE RESPUESTA:

[HARD_FACTS]
- solo datos literales del JSON, sin interpretacion
- si un dato solicitado no esta en el JSON, no lo pongas aqui
[/HARD_FACTS]

[INFERIDO]
- deducciones logicas claramente etiquetadas
- ejemplo: "probablemente el watchdog este activo porque..."
[/INFERIDO]

[NO DISPONIBLE]
- datos solicitados que no aparecen en HARD FACTS
- ej: working_memory, watchdog score, health_score numerico
[/NO DISPONIBLE]

[PENDIENTE]
- elementos listados en pending_implementations
- ej: routing_confidence, avg_latency_ms
[/PENDIENTE]

[SELF-CRITIQUE]
- solo errores o incertidumbres de esta respuesta
- no repitas datos de secciones anteriores
[/SELF-CRITIQUE]

[AI-LAB DEBUG]
task: <descripcion de la peticion>
model: <modelo usado segun HARD FACTS>
node: <nodo GPU usado segun HARD FACTS>
routing_mode: <plan o exec>
context_size: NO DISPONIBLE
budget_used: NO DISPONIBLE
adaptive_scoring: NO DISPONIBLE
working_memory: NO DISPONIBLE
qdrant_enabled: NO DISPONIBLE
watchdog: NO DISPONIBLE
health: NO DISPONIBLE
[/AI-LAB DEBUG]

PROHIBICIONES:
- No uses thinking ni reasoning_content
- No inventes valores numericos
- No confundas servicios con colecciones con contenedores
- No digas que algo funciona si no aparece en HARD FACTS
- No pongas porcentajes, puntuaciones ni estimaciones en [HARD_FACTS]
- No digas "watchdog activo" si no aparece watchdog en HARD FACTS
- No digas "healthy" si no aparece health en HARD FACTS
- No uses "ctx" de un modelo como context_size de request
- No infieras latencia de nodo si no aparece latency_ms
- No digas "no he inferido nada" si [INFERIDO] no esta vacio
- No muevas infraestructura sin permiso explicito de Albert
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


def get_last_user_message(payload: Dict[str, Any]) -> str:
    """Extrae solo el último mensaje con role='user' del payload.

    Ignora mensajes de assistant, tool, system — evita inflar
    el prompt con historial completo que OpenCode ya maneja.
    """
    messages = payload.get("messages", [])
    for msg in reversed(messages):
        if msg.get("role") != "user":
            continue
        content = msg.get("content", "")
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            return "\n".join(
                item.get("text", "") for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            )
    return ""


def truncate_text(text: str, max_chars: int) -> str:
    """Corta *text* en *max_chars* caracteres, sin romper palabras."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > int(max_chars * 0.8):
        truncated = truncated[:last_space]
    return truncated + "\n\n[Contexto truncado para ajustarse a los límites del modelo LM Studio]"



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
    user_text = get_last_user_message(payload)

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
        + "\n\n"
        + "=== CONTEXTO OPERATIVO (datos reales del runtime) ===\n"
        + agent_context[:6000]   # first 6K chars = HARD FACTS + most relevant sources
        + "\n\n"
        + "Usa los datos anteriores para responder. No copies literalmente, sintetiza."
    )

    # ── budget-aware context truncation ─────────────────────────────
    # Garantiza que system_prompt + final_instruction nunca exceda
    # LM_STUDIO_MAX_CONTEXT tokens (16384 actual).
    system_chars = len(system_prompt)
    remaining_chars = int((LM_STUDIO_MAX_CONTEXT - CONTEXT_OVERHEAD_TOKENS) * CHARS_PER_TOKEN)
    budget_chars = max(1000, remaining_chars - system_chars)
    safe_text = truncate_text(user_text, budget_chars)

    final_instruction = (
        "Responde usando ESTRICTAMENTE el FORMATO OBLIGATORIO: "
        "[HARD_FACTS] [/HARD_FACTS] [INFERIDO] [/INFERIDO] "
        "[NO DISPONIBLE] [/NO DISPONIBLE] [PENDIENTE] [/PENDIENTE] "
        "[SELF-CRITIQUE] [/SELF-CRITIQUE] [AI-LAB DEBUG] [/AI-LAB DEBUG].\n"
        "Reglas: "
        "[HARD_FACTS] solo datos literales del JSON. "
        "No repitas contenido entre secciones. "
        "Taxonomia: model != collection != service != container != node. "
        "ctx de modelo NO es context_size de request. "
        "No copies contexto interno ni prompts.\n\n"
        + safe_text
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

            _stream_start = time.time()
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
                _ttfb_ms = int((time.time() - _stream_start) * 1000)
                _rrr(task_type=node["capability"], model=node["model"],
                     node=node["name"], host=node["host"],
                     latency_ms=_ttfb_ms, success=True, stream=True, failover=False)
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

        _req_start = time.time()
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
            _latency_ms = int((time.time() - _req_start) * 1000)
            _rrr(task_type=node["capability"], model=node["model"],
                 node=node["name"], host=node["host"],
                 latency_ms=_latency_ms, success=True, stream=False, failover=False)
        except ImportError:
            pass

        return JSONResponse(
            status_code=upstream.status_code,
            content=content,
            headers=headers,
        )

    except Exception as exc:

        _err_start = time.time()
        try:
            from runtime.routing.routing_history import record_route_result as _rrr
            _latency_ms = int((time.time() - _err_start) * 1000)
            _rrr(task_type=node["capability"] if isinstance(node, dict) else "unknown",
                 model=node.get("model", "unknown") if isinstance(node, dict) else "unknown",
                 node=node.get("name", "unknown") if isinstance(node, dict) else "unknown",
                 host=node.get("host", "unknown") if isinstance(node, dict) else "unknown",
                 latency_ms=_latency_ms, success=False, stream=False, failover=False, error=str(exc))
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


# ═══════════════════════════════════════════════════════════════════
# DIA 3 — Cognitive Memory Recall API
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/memory/search")
async def api_memory_search(collection: str = "routing_history", q: str = "", limit: int = 5):
    """Semantic search across a Qdrant collection.

    Args:
        collection: one of routing_history, cognitive_history, optimizer_history,
                    incidents, runtime_snapshots, working_memory
        q: search query text
        limit: max results (default 5)
    """
    from runtime.memory.qdrant_store import search_collection as _sc
    from runtime.memory.qdrant_collections import COLLECTION_SCHEMAS

    valid = set(COLLECTION_SCHEMAS.keys())
    if collection not in valid:
        return JSONResponse({
            "error": f"Invalid collection. Valid: {sorted(valid)}"
        }, status_code=400)

    results = _sc(collection, q, limit=limit) if q else []
    return {
        "collection": collection,
        "query": q,
        "results": results,
        "count": len(results),
    }


@app.get("/api/incidents/search")
async def api_incidents_search(q: str = "", limit: int = 10, severity: str = ""):
    """Search incidents collection, optionally filtered by severity."""
    from runtime.memory.qdrant_store import search_collection as _sc

    results = _sc("incidents", q, limit=limit) if q else []
    if severity and results:
        results = [r for r in results if r.get("payload", {}).get("severity") == severity]
    return {
        "collection": "incidents",
        "query": q,
        "severity_filter": severity,
        "results": results,
        "count": len(results),
    }


@app.get("/api/runtime/recall")
async def api_runtime_recall(q: str = "", limit: int = 3):
    """Cross-collection cognitive recall across routing, cognitive, incidents."""
    from runtime.memory.qdrant_store import recall as _recall

    results = _recall(q, limit=limit) if q else []
    return {
        "query": q,
        "results": results,
        "count": len(results),
    }
