import sys
sys.path.insert(0, "/opt/ai-lab")

import time
from typing import Any, Dict

import requests

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
import json as json_mod

from runtime.llm.model_router import select_node
from runtime.agent.intent_router import detect_intent
from runtime.modes.mode_manager import current_mode
from runtime.state.system_state import build_system_state
from runtime.gateway.tool_call_parser import parse_tool_calls_from_text, repair_tool_call_arguments, tool_call_is_dangerous
from runtime.gateway.tool_request_classifier import (
    build_observe_context,
    classify_chat_route,
    build_minimal_greeting_messages,
    build_minimal_report_messages,
    build_minimal_tool_messages,
    is_report_request,
    strip_question_tool,
    sanitize_payload_messages,
    sanitize_prompt_text,
    sanitize_observe_output,
    should_use_greeting_fastpath,
    should_use_tool_fastpath,
)

from runtime.telemetry.prometheus_metrics import HARD_FACTS_HITS, GOVERNANCE_BLOCKED, GOVERNANCE_BLOCKED_BY_REASON, ROUTER_REQUESTS, prime_route_family_metrics, record_route_family_metrics

from runtime.agent.selective_context import (
    build_selective_context
)

try:
    from runtime.prompts.prompt_loader import get_prompt_for_route as _load_route_prompt
    _HAVE_PROMPT_LOADER = True
except ImportError:
    _load_route_prompt = None  # type: ignore[assignment]
    _HAVE_PROMPT_LOADER = False

try:
    from runtime.profiles.profile_loader import apply_profile as _apply_profile
    _HAVE_PROFILE_LOADER = True
except ImportError:
    _apply_profile = None  # type: ignore[assignment]
    _HAVE_PROFILE_LOADER = False

try:
    from runtime.telemetry.prometheus_metrics import record_profile_metrics
    _HAVE_PROFILE_METRICS = True
except ImportError:
    record_profile_metrics = None  # type: ignore[assignment]
    _HAVE_PROFILE_METRICS = False

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

prime_route_family_metrics()

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
        "observe": "MODO OBSERVE: inspeccion tecnica/operativa segura. Puedes leer, analizar y usar shell readonly. No ejecutas cambios.",
        "build": "MODO BUILD: puedes proponer cambios en archivos y configuracion. Los comandos shell requieren aprobacion.",
        "execute": "MODO EXECUTE (supervisado): puedes proponer comandos. Cada comando pasa por revision antes de ejecutarse.",
    }
    return labels.get(mode, labels["plan"])


def build_system_context() -> str:
    mode_instruction = _current_mode_label()
    mode_name = current_mode()
    if mode_name == "observe":
        return f"""
Eres el copiloto observador del AI-LAB de Albert.
Responde siempre en espanol. Operas en {mode_instruction}

REGLAS:
1. Prioriza inspeccion, diagnostico y analisis tecnico.
2. Usa comandos readonly solo si aportan informacion.
3. No ejecutes acciones que alteren estado.
4. No uses formato HARD_FACTS obligatorio; responde natural y conciso.
5. Si faltan datos, di que faltan.
6. No inventes metricas ni estado interno.
"""
    HARD_FACTS_HITS.inc()
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
11. Si usas palabras como 'due to', 'based on', 'probablemente', 'optimizacion', 'disponibilidad', 'rendimiento', 'selected because' → esa afirmacion debe ir SIEMPRE en [INFERIDO] y [SELF-CRITIQUE] debe marcarla como 'inferencia no verificada'.
12. routing_mode SOLO puede ser 'adaptive' si HARD FACTS contiene adaptive_scoring=true o routing_mode=adaptive explicitamente. Valores reales validos: 'primary' o 'fallback'. No lo infieras.
13. 'latency_ms' en GPU nodes = latencia de red/ping del nodo. NO es latencia de inferencia del modelo. 'inference_latency_ms' solo si aparece explicitamente en HARD FACTS.
14. Cualquier afirmacion con 'motivo REAL' o sufijo 'REAL' debe tener fuente explicita en HARD FACTS. Si no la tiene, debe ir en [INFERIDO] con nota 'inferencia no verificada'. semantic_recall (qdrant) debe aparecer SIEMPRE en [HARD_FACTS] si el dato esta disponible en el JSON.
15. La palabra 'REAL' solo puede usarse si el campo existe literalmente en HARD FACTS o viene de routing.reason_codes. Si es inferido, no puede llamarse REAL.
16. Si el usuario pide un resumen, informe, estado o reporte, responde directamente: no generes preguntas estructuradas ni uses herramientas de tipo `question`.
"""



def openai_model_id(node: Dict[str, Any]) -> str:
    return f"ailab-router/{node['capability']}/{node['model']}"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "ai-lab-router-api"
    }


@app.get("/metrics")
def metrics():
    from prometheus_client import generate_latest, REGISTRY

    return PlainTextResponse(
        content=generate_latest(REGISTRY).decode("utf-8"),
        media_type="text/plain; charset=utf-8",
    )


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
    return get_last_user_messages(payload, limit=MAX_EMBED_QUERY_MESSAGES)


MAX_EMBED_QUERY_MESSAGES = 3


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


def get_last_user_messages(payload: Dict[str, Any], limit: int = MAX_EMBED_QUERY_MESSAGES) -> str:
    """Return the last *limit* user messages, oldest first."""
    messages = payload.get("messages", [])
    collected: list[str] = []

    for msg in reversed(messages):
        if msg.get("role") != "user":
            continue
        content = msg.get("content", "")
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = "\n".join(
                item.get("text", "") for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            )
        else:
            text = ""

        text = text.strip()
        if text:
            collected.append(text)
        if len(collected) >= limit:
            break

    return "\n\n".join(reversed(collected))


def truncate_text(text: str, max_chars: int) -> str:
    """Corta *text* en *max_chars* caracteres, sin romper palabras."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > int(max_chars * 0.8):
        truncated = truncated[:last_space]
    return truncated + "\n\n[Contexto truncado para ajustarse a los límites del modelo LM Studio]"


def _response_error_message(response: requests.Response) -> str:
    try:
        data = response.json()
        return str(data.get("error", {}).get("message", data.get("message", "")))
    except Exception:
        try:
            return response.text or ""
        except Exception:
            return ""


def _passthrough_stream(response: requests.Response):
    try:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                yield chunk
    finally:
        try:
            response.close()
        except Exception:
            pass



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

    request_start = time.time()
    payload = await request.json()
    payload = sanitize_payload_messages(payload)
    ROUTER_REQUESTS.inc()

    request_text = extract_request_text(payload)
    user_text = get_last_user_message(payload)
    payload = strip_question_tool(payload, user_text or request_text)
    mode_name = current_mode()
    prompt_route = detect_intent(user_text or request_text)
    greeting_fastpath = should_use_greeting_fastpath(payload)
    tool_fastpath = should_use_tool_fastpath(payload)
    observe_fastpath = prompt_route.mode == "observe" and not greeting_fastpath and not tool_fastpath
    route = classify_chat_route(
        payload,
        mode_name=mode_name,
        user_text=user_text,
        request_text=request_text,
        is_report_request=is_report_request(user_text or request_text),
        greeting_fastpath=greeting_fastpath,
        tool_fastpath=tool_fastpath,
        intent_mode=prompt_route.mode,
    )
    record_route_family_metrics(route.family)
    try:
        if _HAVE_PROFILE_LOADER:
            payload = _apply_profile(payload, route.family)
            payload["_profile_source"] = "profile_loader"
            profile = payload.get("_profile", "unknown")
            print(
                f"profile={profile} v={payload.get('_profile_version','?')} "
                f"route={route.family} model={payload.get('model','?')} "
                f"tokens={payload.get('max_tokens','?')} temp={payload.get('temperature','?')} "
                f"tools={'tools' in payload} source=profile_loader",
                flush=True,
            )
            if _HAVE_PROFILE_METRICS:
                record_profile_metrics(profile, route.family, payload.get("model", "?"))
    except Exception:
        pass
    try:
        from runtime.audit.audit_logger import audit_event
        audit_event(
            "route_family_selected",
            {
                "family": route.family,
                "variant": route.variant,
                "reason": route.reason,
                "model": payload.get("model", "ailab-router/auto"),
                "mode": mode_name,
            },
        )
    except ImportError:
        pass

    if payload.get("_profile_source") == "profile_loader":
        try:
            from runtime.audit.audit_logger import audit_event
            audit_event("profile_applied", {
                "profile": payload.get("_profile", "unknown"),
                "version": payload.get("_profile_version", "0"),
                "source": "profile_loader",
                "route": route.family,
                "model": payload.get("model", "unknown"),
                "max_tokens": payload.get("max_tokens", 0),
                "temperature": payload.get("temperature", 0),
                "tools_allowed": "tools" in payload,
            })
        except ImportError:
            pass

    if route.family == "cognitive":
        build_system_state()

    requested_model = payload.get(
        "model",
        "ailab-router/auto"
    )

    capability = capability_from_model(
        requested_model
    )
    if not capability and (payload.get("tools") or payload.get("tool_choice")):
        capability = "tool_use"
    effective_capability = capability
    if route.family in ("minimal", "observe"):
        effective_capability = "fast"
    if route.family == "observe":
        capability = "fast"

    node = select_node(
        request_text,
        capability=effective_capability
    )
    if greeting_fastpath:
        node = dict(node)
        node["model"] = "llama-3.1-8b-instruct"
        node["capability"] = "fast"
    selected_model = node.get("model")
    selected_node = node.get("name")
    routing_mode = node.get("mode", "primary")
    reason_codes = node.get("reason_codes", [])
    discovery_source = node.get("discovery_source", "static")

    upstream_url = (
        f"http://{node['host']}:{node['port']}"
        "/v1/chat/completions"
    )

    if route.family == "minimal" and route.variant == "report":
        proxy_payload = dict(payload)
        proxy_payload.pop("stream", None)
        proxy_payload.pop("_ai_lab_route_family", None)
        proxy_payload.pop("_ai_lab_route_variant", None)
        proxy_payload.pop("_ai_lab_route_reason", None)
        proxy_payload["model"] = "auto"
        proxy_payload["max_tokens"] = min(int(proxy_payload.get("max_tokens", 64) or 64), 64)
        proxy_payload["temperature"] = 0
        proxy_response = requests.post(
            "http://127.0.0.1:8008/v1/chat/completions",
            json=proxy_payload,
            headers={"Connection": "close"},
            timeout=300,
        )
        proxy_content = proxy_response.json() if proxy_response.content else {}
        latency_ms = int((time.time() - request_start) * 1000)
        record_route_family_metrics(route.family, count=False, latency_ms=latency_ms, blocked=False, error=proxy_response.status_code >= 400)
        return JSONResponse(
            status_code=proxy_response.status_code,
            content=proxy_content,
            headers={
                "X-AI-LAB-Selected-Node": "gateway-proxy",
                "X-AI-LAB-Selected-Host": "127.0.0.1",
                "X-AI-LAB-Selected-Model": "llama-3.1-8b-instruct",
                "X-AI-LAB-Capability": "fast",
            },
        )
    elif route.family == "minimal" and route.variant == "casual":
        proxy_payload = dict(payload)
        proxy_payload.pop("stream", None)
        proxy_payload.pop("_ai_lab_route_family", None)
        proxy_payload.pop("_ai_lab_route_variant", None)
        proxy_payload.pop("_ai_lab_route_reason", None)
        proxy_payload["model"] = "auto"
        proxy_payload["max_tokens"] = min(int(proxy_payload.get("max_tokens", 64) or 64), 64)
        proxy_payload["temperature"] = 0
        proxy_response = requests.post(
            "http://127.0.0.1:8008/v1/chat/completions",
            json=proxy_payload,
            headers={"Connection": "close"},
            timeout=300,
        )
        proxy_content = proxy_response.json() if proxy_response.content else {}
        latency_ms = int((time.time() - request_start) * 1000)
        record_route_family_metrics(route.family, count=False, latency_ms=latency_ms, blocked=False, error=proxy_response.status_code >= 400)
        return JSONResponse(
            status_code=proxy_response.status_code,
            content=proxy_content,
            headers={
                "X-AI-LAB-Selected-Node": "gateway-proxy",
                "X-AI-LAB-Selected-Host": "127.0.0.1",
                "X-AI-LAB-Selected-Model": "llama-3.1-8b-instruct",
                "X-AI-LAB-Capability": "fast",
            },
        )
    elif route.family == "minimal" and route.variant == "greeting":
        capability = "fast"
        payload["messages"] = build_minimal_greeting_messages(user_text or request_text)
    elif route.family == "observe":
        payload["max_tokens"] = min(int(payload.get("max_tokens", 180) or 180), 180)
        payload["messages"] = [
            {
                "role": "system",
                "content": (
                    "Eres el observador del AI-LAB de Albert. Usa solo informacion observable. "
                    "No uses HARD_FACTS, no uses secciones y no inventes datos. "
                    "Si el usuario pide detalle, resume en 3-5 lineas. "
                    f"OBSERVED_RUNTIME: {build_observe_context()}"
                ),
            },
            {"role": "user", "content": user_text or request_text},
        ]
    elif route.family == "tool_fastpath":
        payload["messages"] = build_minimal_tool_messages(
            payload,
            selected_model=selected_model or "",
            selected_node=selected_node or "",
            routing_mode=routing_mode,
            reason_codes=reason_codes,
            discovery_source=discovery_source,
            user_text=user_text or request_text,
        )
    else:
        messages = payload.get("messages", [])

        # ── working memory + context shaper (FASE 8.7) ──────────────────
        wm = None
        if _HAVE_WORKING_MEMORY and _HAVE_CONTEXT_SHAPER:
            session_id = request.headers.get("X-AI-LAB-Session", request.client.host if request.client else "default")
            wm = get_session(session_id)
            wm.add_turn("user", request_text)
            task = node.get("capability", "general")
            wm.set_task(task)

            agent_context = shape_context(
                task,
                selected_model or "",
                wm,
                query_text=request_text,
                routing_mode=routing_mode,
                selected_model=selected_model,
                selected_node=selected_node,
                routing_reason_codes=reason_codes,
                discovery_source=discovery_source,
            )
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

        if _task_cap in ("fast", "general"):
            try:
                prompt_text, _warnings = _load_route_prompt("fast", "fast") if _HAVE_PROMPT_LOADER else ("", [])
                if prompt_text:
                    system_prompt = prompt_text
                    if agent_context.strip():
                        system_prompt += "\n\n=== RUNTIME DATA ===\n" + agent_context[:2500] + "\n"
                    system_prompt += "\nPrioriza respuestas visibles, coherentes y utiles."
                else:
                    raise ValueError("empty prompt")
            except Exception:
                system_prompt = (
                    "Eres el asistente tecnico del AI-LAB.\n"
                    "Responde en espanol de forma clara, util y natural.\n"
                    "No uses HARD_FACTS, no uses secciones formateadas y no inventes datos.\n"
                    + ("=== RUNTIME DATA ===\n" + agent_context[:2500] + "\n\n" if agent_context.strip() else "")
                    + "Prioriza respuestas visibles, coherentes y utiles."
                )

        # ── budget-aware context truncation ─────────────────────────────
        # Garantiza que system_prompt + final_instruction nunca exceda
        # LM_STUDIO_MAX_CONTEXT tokens (16384 actual).
        system_chars = len(system_prompt)
        remaining_chars = int((LM_STUDIO_MAX_CONTEXT - CONTEXT_OVERHEAD_TOKENS) * CHARS_PER_TOKEN)
        budget_chars = max(1000, remaining_chars - system_chars)
        safe_text = truncate_text(user_text, budget_chars)

        if _task_cap in ("fast", "general"):
            final_instruction = safe_text
        elif _task_cap == "coding":
            final_instruction = (
                "Responde con el FORMATO OBLIGATORIO:\n"
                "[HARD_FACTS] datos del JSON relevantes [/HARD_FACTS]\n"
                "[INFERIDO] deducciones [/INFERIDO]\n"
                "[NO DISPONIBLE] datos ausentes [/NO DISPONIBLE]\n"
                "[PENDIENTE] de pending [/PENDIENTE]\n"
                "[SELF-CRITIQUE] errores [/SELF-CRITIQUE]\n"
                "[AI-LAB DEBUG] Pobla con valores reales de HARD FACTS: profile, task, model, node, budget_used, "
                "adaptive_scoring, working_memory, "
                "qdrant_recall (matches, collections, chars del JSON), watchdog, health. "
                "NO DISPONIBLE solo si el dato no existe en HARD FACTS. "
                "semantic_recall debe ir en [HARD_FACTS], no aqui. [/AI-LAB DEBUG]\n"
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
                "[AI-LAB DEBUG] Pobla este bloque con valores reales de HARD FACTS: "
                "profile=<profile del JSON>, task=<inferido de la solicitud>, "
                "model=<model_id>, node=<node_name>, "
                "budget_used=<del sistema>, adaptive_scoring=<si en HARD FACTS>, "
                "working_memory=<si en HARD FACTS>, "
                "qdrant_recall=<matches, collections, chars del semantic_recall en JSON>, "
                "watchdog=<health.watchdog>, health=<health.score>. "
                "NO DISPONIBLE solo si el dato no existe en HARD FACTS. "
                "semantic_recall NO debe ir aqui, debe ir en [HARD_FACTS]. [/AI-LAB DEBUG]\n"
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
    upstream_payload.pop("stream", None)
    upstream_payload.pop("_ai_lab_route_family", None)
    upstream_payload.pop("_ai_lab_route_variant", None)
    upstream_payload.pop("_ai_lab_route_reason", None)

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

    if route.family in ("minimal", "observe"):
        upstream_payload.pop("reasoning", None)
    elif capability in ("reasoning",) or node.get("capability") in ("reasoning",):
        if "reasoning" not in upstream_payload.get("model", ""):
            upstream_payload.setdefault(
                "reasoning",
                {"effort": "none"}
            )
    else:
        upstream_payload.pop("reasoning", None)

    if "qwen2.5-coder-14b" in str(upstream_payload.get("model", "")):
        upstream_payload.pop("reasoning", None)
        upstream_payload.pop("tool_choice", None)
        upstream_payload.pop("tools", None)

    headers = {
        "X-AI-LAB-Selected-Node": node["name"],
        "X-AI-LAB-Selected-Host": node["host"],
        "X-AI-LAB-Selected-Model": node["model"],
        "X-AI-LAB-Capability": node["capability"],
    }

    try:

        client_wants_stream = bool(payload.get("stream"))

        if client_wants_stream:
            _stream_start = time.time()

            upstream = requests.post(
                upstream_url,
                json=upstream_payload,
                timeout=300,
            )

            if upstream.status_code >= 400:
                error_msg = _response_error_message(upstream)
                if "unloaded" in error_msg.lower() or "invalid model identifier" in error_msg.lower():
                    upstream.close()
                    fallback_node = {
                        **node,
                        "host": "192.168.1.50",
                        "port": 1234,
                        "model": "qwen2.5-coder-14b-instruct",
                        "name": node.get("name", "rx9070"),
                    }
                    upstream_url = f"http://{fallback_node['host']}:{fallback_node['port']}/v1/chat/completions"
                    upstream_payload = dict(upstream_payload)
                    upstream_payload["model"] = fallback_node["model"]
                    upstream = requests.post(
                        upstream_url,
                        json=upstream_payload,
                        timeout=300,
                    )
                    node = fallback_node
                    selected_model = node["model"]
                    selected_node = node["name"]
                    headers = {
                        "X-AI-LAB-Selected-Node": node["name"],
                        "X-AI-LAB-Selected-Host": node["host"],
                        "X-AI-LAB-Selected-Model": node["model"],
                        "X-AI-LAB-Capability": node["capability"],
                    }

            if upstream.status_code >= 400:
                content = {"error": {"message": _response_error_message(upstream) or "upstream_error"}}
                upstream.close()
                return JSONResponse(
                    status_code=upstream.status_code,
                    content=content,
                    headers=headers,
                )

            content = upstream.json()

            choices = content.get("choices", [])
            first_choice = choices[0] if choices else {}
            message = first_choice.get("message", {}) if isinstance(first_choice, dict) else {}

            async def wrap_as_sse():
                chunk_id = content.get("id", "chatcmpl-" + str(int(time.time())))
                model_name = content.get("model", node.get("model", "unknown"))
                base = {"id": chunk_id, "object": "chat.completion.chunk", "model": model_name}

                delta = {"role": "assistant"}
                if isinstance(message.get("content"), str) and message.get("content"):
                    delta["content"] = message.get("content")
                if message.get("tool_calls"):
                    delta["tool_calls"] = [repair_tool_call_arguments(tc) for tc in message.get("tool_calls") if isinstance(tc, dict)]

                yield f"data: {json_mod.dumps({**base, 'choices': [{'index': 0, 'delta': delta, 'finish_reason': None}]}, ensure_ascii=False)}\n\n"

                finish_reason = first_choice.get("finish_reason", "stop") if isinstance(first_choice, dict) else "stop"
                yield f"data: {json_mod.dumps({**base, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': finish_reason}]}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"

            try:
                from runtime.routing.routing_history import record_route_result as _rrr
                _ttfb_ms = int((time.time() - _stream_start) * 1000)
                _rrr(task_type=node["capability"], model=node["model"],
                     node=node["name"], host=node["host"],
                     latency_ms=_ttfb_ms, success=True, stream=True, failover=False)
            except ImportError:
                pass

            usage = content.get("usage", {}) if isinstance(content, dict) else {}
            record_route_family_metrics(
                route.family,
                count=False,
                latency_ms=_ttfb_ms,
                prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
                completion_tokens=int(usage.get("completion_tokens", 0) or 0),
            )

            return StreamingResponse(
                wrap_as_sse(),
                status_code=200,
                media_type="text/event-stream",
                headers=headers,
            )

        _req_start = time.time()
        upstream = requests.post(
            upstream_url,
            json=upstream_payload,
            headers={"Connection": "close"},
            timeout=300
        )

        content = upstream.json()

        if upstream.status_code >= 400:
            error_msg = str(content.get("error", {}).get("message", content.get("message", "")))
            if "unloaded" in error_msg.lower() or "invalid model identifier" in error_msg.lower():
                fallback_url = f"http://192.168.1.50:1234/v1/chat/completions"
                fallback_payload = dict(upstream_payload)
                fallback_payload["model"] = "qwen2.5-coder-14b-instruct"
                upstream = requests.post(fallback_url, json=fallback_payload, headers={"Connection": "close"}, timeout=300)
                content = upstream.json()

        if not isinstance(content, dict):
            latency_ms = int((time.time() - request_start) * 1000)
            record_route_family_metrics(route.family, count=False, latency_ms=latency_ms, error=True)
            return JSONResponse(
                status_code=502,
                content={
                    "error": {
                        "message": "upstream returned a non-object response",
                        "type": "ai_lab_router_upstream_error",
                        "selected_node": node,
                    }
                },
                headers=headers,
            )

        choices = content.get("choices", [])
        if not choices:
            latency_ms = int((time.time() - request_start) * 1000)
            record_route_family_metrics(route.family, count=False, latency_ms=latency_ms, error=True)
            return JSONResponse(
                status_code=502,
                content={
                    "error": {
                        "message": "upstream returned no choices",
                        "type": "ai_lab_router_upstream_error",
                        "selected_node": node,
                        "upstream_status": upstream.status_code,
                    }
                },
                headers=headers,
            )

        for choice in choices:
            msg = choice.get("message", {})
            if "reasoning_content" in msg:
                rc = msg.pop("reasoning_content")
                tool_calls = parse_tool_calls_from_text(rc if isinstance(rc, str) else None)
                if tool_calls:
                    msg["tool_calls"] = tool_calls
                elif not msg.get("content"):
                    msg["content"] = rc
            elif isinstance(msg.get("content"), str):
                tool_calls = parse_tool_calls_from_text(msg.get("content"))
                if tool_calls:
                    msg["tool_calls"] = tool_calls
            if msg.get("tool_calls"):
                msg["content"] = None

            if msg.get("tool_calls"):
                msg["tool_calls"] = [repair_tool_call_arguments(tc) for tc in msg.get("tool_calls") if isinstance(tc, dict)]

            if isinstance(msg.get("content"), str):
                msg["content"] = sanitize_prompt_text(msg.get("content"))

            if mode_name == "observe" and isinstance(msg.get("content"), str):
                msg["content"] = sanitize_observe_output(msg.get("content"))

        blocked_any = False
        for choice in choices:
            msg = choice.get("message", {})
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                continue
            blocked = False
            blocked_reason = ""
            for tc in tool_calls:
                dangerous, marker = tool_call_is_dangerous(tc)
                if dangerous:
                    blocked = True
                    blocked_reason = marker or "dangerous command"
                    break
            if blocked:
                blocked_any = True
                msg.pop("tool_calls", None)
                msg["content"] = f"Solicitud bloqueada por policy: {blocked_reason}"
                choice["finish_reason"] = "stop"
                GOVERNANCE_BLOCKED.inc()
                GOVERNANCE_BLOCKED_BY_REASON.labels(reason=blocked_reason).inc()
                try:
                    from runtime.audit.audit_logger import audit_event
                    audit_event("tool_call_blocked", {"reason": blocked_reason, "node": selected_node, "model": selected_model})
                except ImportError:
                    pass

            try:
                from runtime.routing.routing_history import record_route_result as _rrr
                _latency_ms = int((time.time() - _req_start) * 1000)
                _rrr(task_type=node["capability"], model=node["model"],
                     node=node["name"], host=node["host"],
                     latency_ms=_latency_ms, success=True, stream=False, failover=False)
            except ImportError:
                pass

            usage = content.get("usage", {}) if isinstance(content, dict) else {}
            record_route_family_metrics(
                route.family,
                count=False,
                latency_ms=_latency_ms,
                prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
                completion_tokens=int(usage.get("completion_tokens", 0) or 0),
                blocked=blocked_any,
            )

            return JSONResponse(
                status_code=upstream.status_code,
                content=content,
                headers=headers,
            )

        latency_ms = int((time.time() - request_start) * 1000)
        record_route_family_metrics(route.family, count=False, latency_ms=latency_ms, error=True)
        return JSONResponse(
            status_code=502,
            content={
                "error": {
                    "message": "upstream returned no usable choices",
                    "type": "ai_lab_router_upstream_error",
                    "selected_node": node,
                    "upstream_status": upstream.status_code,
                }
            },
            headers=headers,
        )

    except Exception as exc:

        record_route_family_metrics(route.family, count=False, error=True)
        try:
            from runtime.routing.routing_history import record_route_result as _rrr
            _latency_ms = int((time.time() - request_start) * 1000)
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
