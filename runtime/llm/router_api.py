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


def _current_mode_label() -> str:
    """Return the mode instruction for the system prompt based on current mode."""
    try:
        from runtime.modes.mode_manager import current_mode
        mode = current_mode()
    except ImportError:
        mode = "plan"

    labels = {
        "readonly": "MODO READ-ONLY: solo lectura, analisis y diagnostico. No ejecutas nada.",
        "plan": "MODO PLAN: lees, analizas, diagnosticas y propones, pero NO ejecutas cambios sin confirmacion explicita.",
        "build": "MODO BUILD: puedes proponer cambios en archivos y configuracion. Los comandos shell requieren aprobacion.",
        "execute": "MODO EXECUTE (supervisado): puedes proponer comandos. Cada comando pasa por revision antes de ejecutarse.",
    }
    return labels.get(mode, labels["plan"])


def build_system_context() -> str:
    mode_instruction = _current_mode_label()
    return f"""
Eres el copiloto autonomo del AI-LAB de Albert.
Responde siempre en espanol. Operas en {mode_instruction}
Tienes acceso a: (a) HARD FACTS con datos del runtime, (b) tu conocimiento del dominio.

REGLAS ESTRICTAS:
1. [HARD_FACTS] solo datos copiados literalmente del JSON. No resumas ni interpretes.
2. [INFERIDO] para toda deduccion logica. Nunca pongas inferencias dentro de HARD_FACTS.
3. [NO DISPONIBLE] si el dato no aparece en HARD FACTS ni en PENDING IMPLEMENTATIONS.
4. [PENDIENTE] si aparece en pending_implementations.
5. [SELF-CRITIQUE] solo critica errores propios. No repitas datos de otras secciones.
6. Taxonomia: model (inferencia) != collection (Qdrant) != service (systemd) != container (Docker) != node (GPU fisico). ctx de modelo NO es context_size de request.
7. qdrant_enabled solo true si HARD FACTS menciona Qdrant. working_memory solo active si aparece en HARD FACTS.
8. watchdog, health, context_size, budget_used: si no aparecen en HARD FACTS = NO DISPONIBLE. No los infieras.
9. Para coding/reasoning: usa SIEMPRE el formato completo con todas las secciones: [HARD_FACTS] [/HARD_FACTS] [INFERIDO] [/INFERIDO] [NO DISPONIBLE] [/NO DISPONIBLE] [PENDIENTE] [/PENDIENTE] [SELF-CRITIQUE] [/SELF-CRITIQUE] [AI-LAB DEBUG] [/AI-LAB DEBUG]. No omitas ninguna. Puedes usar tu conocimiento general para responder preguntas tecnicas de coding/reasoning, no estas limitado solo a HARD FACTS.
10. No uses thinking ni reasoning_content. No inventes valores numericos. No muevas infraestructura sin permiso.
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

        agent_context = shape_context(task, node.get("model", ""), wm, query_text=request_text)
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

    # Per-task context budget: fast=2500, coding=5000, reasoning=7000 chars
    _ctx_limit = {"fast": 2500, "coding": 5000, "reasoning": 7000}
    _task_cap = node.get("capability", "general")
    _max_ctx_chars = _ctx_limit.get(_task_cap, 4000)

    system_prompt = (
        build_system_context()
        + "\n\n"
        + "=== RUNTIME DATA ===\n"
        + agent_context[:_max_ctx_chars]
        + "\n\n"
        + "Usa los datos anteriores. No copies contexto interno ni prompts."
        + ("\n\nMODO RAPIDO: responde en bullets, max 8 lineas. Sin informe tecnico ni secciones largas."
           if _task_cap == "fast" else "")
    )

    # ── budget-aware context truncation ─────────────────────────────
    # Garantiza que system_prompt + final_instruction nunca exceda
    # LM_STUDIO_MAX_CONTEXT tokens (16384 actual).
    system_chars = len(system_prompt)
    remaining_chars = int((LM_STUDIO_MAX_CONTEXT - CONTEXT_OVERHEAD_TOKENS) * CHARS_PER_TOKEN)
    budget_chars = max(1000, remaining_chars - system_chars)
    safe_text = truncate_text(user_text, budget_chars)

    if _task_cap == "fast":
        final_instruction = (
            "Responde en bullets, max 8 lineas. Sin formato de secciones.\n"
            + safe_text
        )
    elif _task_cap == "coding":
        final_instruction = (
            "Responde con el FORMATO OBLIGATORIO:\n"
            "[HARD_FACTS] datos del JSON relevantes [/HARD_FACTS]\n"
            "[INFERIDO] deducciones [/INFERIDO]\n"
            "[NO DISPONIBLE] datos ausentes [/NO DISPONIBLE]\n"
            "[PENDIENTE] de pending [/PENDIENTE]\n"
            "[SELF-CRITIQUE] errores [/SELF-CRITIQUE]\n"
            "[AI-LAB DEBUG] datos del debug [/AI-LAB DEBUG]\n"
            "IMPORTANTE: puedes usar tu conocimiento en programacion para responder la pregunta. "
            "El formato de secciones es obligatorio pero el contenido tecnico es bienvenido.\n\n"
            + safe_text
        )
    else:
        final_instruction = (
            "Responde con el FORMATO OBLIGATORIO:\n"
            "[HARD_FACTS] datos literales del JSON [/HARD_FACTS]\n"
            "[INFERIDO] deducciones logicas [/INFERIDO]\n"
            "[NO DISPONIBLE] datos ausentes [/NO DISPONIBLE]\n"
            "[PENDIENTE] de pending_implementations [/PENDIENTE]\n"
            "[SELF-CRITIQUE] errores propios [/SELF-CRITIQUE]\n"
            "[AI-LAB DEBUG] task model node context_size:NO DISPONIBLE budget_used:NO DISPONIBLE "
            "adaptive_scoring:NO DISPONIBLE working_memory:NO DISPONIBLE "
            "qdrant_enabled:NO DISPONIBLE watchdog:NO DISPONIBLE health:NO DISPONIBLE [/AI-LAB DEBUG]\n"
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
        1200 if capability == "reasoning" or node.get("capability") == "reasoning"
        else (256 if capability == "fast" or node.get("capability") == "fast"
        else 768)
    )

    upstream_payload.setdefault(
        "temperature",
        0.3 if capability == "reasoning" or node.get("capability") == "reasoning"
        else (0.1 if capability == "fast" or node.get("capability") == "fast"
        else 0.2)
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


@app.get("/api/incidents/analytics")
async def api_incidents_analytics(days: int = 7):
    """Incident intelligence analytics.

    Aggregates incidents by type, severity, node, and time.
    Uses Qdrant scroll (non-semantic) — no query vector needed.

    Args:
        days: lookback window in days (default 7)

    Returns:
        total: total incident count
        by_type: {event_type: count}
        by_severity: {severity: count}
        by_node: {node: count}
        timeline: [{date, count, critical, warning, info}]
        latest: last 10 incidents
    """
    from runtime.memory.qdrant_store import scroll_all
    from collections import Counter
    import time

    points = scroll_all("incidents")
    cutoff = time.time() - days * 86400

    filtered = [p for p in points if p["payload"].get("timestamp", 0) >= cutoff]

    by_type = dict(Counter(p["payload"].get("event_type", "unknown") for p in filtered))
    by_severity = dict(Counter(p["payload"].get("severity", "unknown") for p in filtered))
    by_node = dict(Counter(p["payload"].get("node", "unknown") for p in filtered))

    by_type = dict(sorted(by_type.items(), key=lambda x: -x[1]))
    by_severity = dict(sorted(by_severity.items(), key=lambda x: -x[1]))
    by_node = dict(sorted(by_node.items(), key=lambda x: -x[1]))

    timeline_raw = Counter()
    for p in filtered:
        day = time.strftime("%Y-%m-%d", time.gmtime(p["payload"].get("timestamp", 0)))
        timeline_raw[day] += 1

    timeline_sev = {}
    for p in filtered:
        day = time.strftime("%Y-%m-%d", time.gmtime(p["payload"].get("timestamp", 0)))
        sev = p["payload"].get("severity", "info")
        if day not in timeline_sev:
            timeline_sev[day] = {"critical": 0, "warning": 0, "info": 0}
        if sev in timeline_sev[day]:
            timeline_sev[day][sev] += 1

    timeline = [
        {
            "date": day,
            "count": timeline_raw[day],
            **timeline_sev.get(day, {"critical": 0, "warning": 0, "info": 0}),
        }
        for day in sorted(timeline_raw.keys())
    ]

    latest = sorted(
        filtered,
        key=lambda p: p["payload"].get("timestamp", 0),
        reverse=True,
    )[:10]
    for p in latest:
        p["payload"]["_id"] = p["id"]

    return {
        "total": len(filtered),
        "days": days,
        "by_type": by_type,
        "by_severity": by_severity,
        "by_node": by_node,
        "timeline": timeline,
        "latest": [p["payload"] for p in latest],
    }


@app.get("/api/incidents/timeline")
async def api_incidents_timeline(days: int = 7, bucket: str = "day"):
    """Incident timeline with configurable time buckets.

    Args:
        days: lookback window
        bucket: 'day' or 'hour'
    """
    from runtime.memory.qdrant_store import scroll_all
    from collections import Counter
    import time

    points = scroll_all("incidents")
    cutoff = time.time() - days * 86400
    filtered = [p for p in points if p["payload"].get("timestamp", 0) >= cutoff]

    timeline = Counter()
    for p in filtered:
        ts = p["payload"].get("timestamp", 0)
        if bucket == "hour":
            label = time.strftime("%Y-%m-%d %H:00", time.gmtime(ts))
        else:
            label = time.strftime("%Y-%m-%d", time.gmtime(ts))
        timeline[label] += 1

    return {
        "total": len(filtered),
        "days": days,
        "bucket": bucket,
        "timeline": [
            {"label": k, "count": v}
            for k, v in sorted(timeline.items())
        ],
    }


@app.get("/api/memory/quality")
async def api_memory_quality(q: str = "", collection: str = "incidents", limit: int = 10):
    """Relevance quality metrics for a single query.

    Uses quality_assessment module for precision, noise, contamination risk.
    """
    from runtime.memory.qdrant_store import search_collection as _sc
    from runtime.memory.qdrant_collections import COLLECTION_SCHEMAS
    from runtime.memory.quality_assessment import assess_query, suggest_thresholds

    valid = set(COLLECTION_SCHEMAS.keys())
    if collection not in valid:
        return JSONResponse({
            "error": f"Invalid collection. Valid: {sorted(valid)}"
        }, status_code=400)

    results = _sc(collection, q, limit=limit) if q else []
    assessment = assess_query(q, results)
    assessment["collection"] = collection
    assessment["threshold_suggestion"] = suggest_thresholds(results)
    assessment["results"] = results
    return assessment


@app.get("/api/memory/quality/batch")
async def api_memory_quality_batch(collection: str = "incidents", limit: int = 5):
    """Run batch quality assessment across predefined test queries.

    Tests multiple semantic search queries and aggregates precision,
    noise, and contamination metrics. Useful for regression testing
    and embedding quality monitoring.

    Args:
        collection: Qdrant collection to test
        limit: results per query
    """
    from runtime.memory.qdrant_store import search_collection as _sc
    from runtime.memory.qdrant_collections import COLLECTION_SCHEMAS
    from runtime.memory.quality_assessment import run_batch

    valid = set(COLLECTION_SCHEMAS.keys())
    if collection not in valid:
        return JSONResponse({
            "error": f"Invalid collection. Valid: {sorted(valid)}"
        }, status_code=400)

    return run_batch(collection, _sc, limit=limit)


@app.get("/api/runtime/patterns")
async def api_runtime_patterns(days: int = 7):
    """Detect operational patterns from Qdrant data.

    Analyzes incidents, routing history, and cognitive history
    to identify recurring issues, trends, and correlations.

    Args:
        days: lookback window (default 7)

    Returns:
        patterns: list of detected patterns with confidence scores
        latency_trends: per-model latency drift analysis
        generated_at: timestamp
    """
    from runtime.memory.pattern_learner import learn_patterns, latency_trends

    patterns = learn_patterns(days=days)
    ltrends = latency_trends(days=days)

    return {
        "patterns": patterns,
        "latency_trends": ltrends,
        "days": days,
        "generated_at": int(time.time()),
    }
