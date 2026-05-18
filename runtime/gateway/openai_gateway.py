import json
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests
import time

from runtime.router.capability_router import choose_model
from runtime.llm.model_router import infer_task
from runtime.agent.intent_router import detect_intent
from runtime.modes.mode_manager import current_mode

from runtime.telemetry.gateway_metrics import (
    register_request,
    register_stream,
    register_error,
    register_latency,
    get_metrics,
)

from runtime.distributed.execution_coordinator import (
    register_execution,
)

from runtime.telemetry.runtime_api import (
    runtime_snapshot,
)

from runtime.distributed.runtime_topology import (
    get_topology,
)

from runtime.telemetry.runtime_api import (
    runtime_snapshot,
)

from runtime.distributed.execution_coordinator import (
    register_execution,
)


from runtime.gateway.stream_sanitizer import relay_stream
from runtime.gateway.tool_call_parser import extract_tool_calls_from_message, filter_dangerous_tool_calls, repair_tool_call_arguments, parse_tool_calls
from runtime.gateway.tool_request_classifier import build_minimal_report_messages, build_observe_context, classify_chat_route, is_report_request, sanitize_observe_output, sanitize_payload_messages, sanitize_prompt_text, should_use_greeting_fastpath, should_use_tool_fastpath, strip_question_tool
from runtime.gateway.gateway_metrics import (
    load_metrics,
    record_request,
    record_error,
)
from runtime.telemetry.prometheus_metrics import GOVERNANCE_BLOCKED, GOVERNANCE_BLOCKED_BY_REASON, prime_route_family_metrics, record_route_family_metrics
from prometheus_client import generate_latest as prom_generate_latest, REGISTRY as prom_REGISTRY
from collections import defaultdict
import threading

prime_route_family_metrics()

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

RATE_LIMIT_REQUESTS = 30
RATE_LIMIT_WINDOW = 60
_rate_limit_data: dict = defaultdict(list)
_rate_limit_lock = threading.Lock()


def check_rate_limit(client_ip: str) -> bool:
    now = time.time()
    with _rate_limit_lock:
        timestamps = _rate_limit_data[client_ip]
        timestamps = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
        _rate_limit_data[client_ip] = timestamps
        if len(timestamps) >= RATE_LIMIT_REQUESTS:
            return False
        timestamps.append(now)
        return True

# Enhanced runtime metrics
MODEL_SELECTIONS = []
ACTIVE_STREAMS = 0
ROUTING_DECISIONS = 0
FAILOVERS = 0
MEMORY_WRITES = 0

# Session tracking
import uuid
SESSION_STORE = {}
SESSION_COUNTER = 0
ORPHAN_SESSIONS = 0
EPISODIC_RECALLS = 0
ACCUMULATED_MEMORY = 0
EPISODIC_TOTAL = 0
EPISODIC_EMBEDDINGS = 0
EPISODIC_DOMAINS = {}
BLOCKED_PROMPTS = 0
SANITIZATIONS = 0
RATE_LIMIT_HITS = 0
CONTEXT_OVERFLOWS = 0
HALLUCINATION_GUARDS = 0
PARSER_FAILURES = 0


def create_session(task_type, model, node):
    global SESSION_COUNTER
    sid = str(uuid.uuid4())[:8]
    with _metrics_lock:
        SESSION_COUNTER += 1
        SESSION_STORE[sid] = {
            "session_id": sid,
            "start_time": time.time(),
            "duration": 0,
            "model": model,
            "node": node,
            "task": task_type,
            "tokens": 0,
            "status": "active",
        }
    return sid


def complete_session(sid, tokens=0):
    global EPISODIC_RECALLS, ACCUMULATED_MEMORY
    with _metrics_lock:
        if sid in SESSION_STORE:
            s = SESSION_STORE[sid]
            s["duration"] = int((time.time() - s["start_time"]) * 1000)
            s["tokens"] = tokens
            s["status"] = "completed"
            EPISODIC_RECALLS += 1
            ACCUMULATED_MEMORY += tokens


def mark_orphan_session(sid):
    global ORPHAN_SESSIONS
    with _metrics_lock:
        if sid in SESSION_STORE:
            SESSION_STORE[sid]["status"] = "orphan"
            ORPHAN_SESSIONS += 1


def get_sessions(limit=50):
    with _metrics_lock:
        all_sessions = list(SESSION_STORE.values())
        all_sessions.sort(key=lambda x: x["start_time"], reverse=True)
        return all_sessions[:limit]


def cleanup_old_sessions():
    with _metrics_lock:
        now = time.time()
        expired = [sid for sid, s in SESSION_STORE.items() if s["status"] == "active" and now - s["start_time"] > 3600]
        for sid in expired:
            SESSION_STORE[sid]["status"] = "orphan"
        if expired:
            global ORPHAN_SESSIONS
            ORPHAN_SESSIONS += len(expired)
        if len(SESSION_STORE) > 2000:
            old = sorted(SESSION_STORE.keys(), key=lambda sid: SESSION_STORE[sid]["start_time"])[:1000]
            for sid in old:
                del SESSION_STORE[sid]


import threading
_metrics_lock = threading.Lock()


def record_model_selection(task_type, model, node, latency_ms):
    with _metrics_lock:
        MODEL_SELECTIONS.append({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "task": task_type,
            "model": model,
            "node": node,
            "latency_ms": latency_ms,
        })
        if len(MODEL_SELECTIONS) > 1000:
            MODEL_SELECTIONS[:] = MODEL_SELECTIONS[-500:]


def record_routing_decision():
    global ROUTING_DECISIONS
    with _metrics_lock:
        ROUTING_DECISIONS += 1


def record_blocked_prompt():
    global BLOCKED_PROMPTS
    with _metrics_lock:
        BLOCKED_PROMPTS += 1


def record_sanitization():
    global SANITIZATIONS
    with _metrics_lock:
        SANITIZATIONS += 1


def record_rate_limit_hit():
    global RATE_LIMIT_HITS
    with _metrics_lock:
        RATE_LIMIT_HITS += 1


def record_context_overflow():
    global CONTEXT_OVERFLOWS
    with _metrics_lock:
        CONTEXT_OVERFLOWS += 1


def record_hallucination_guard():
    global HALLUCINATION_GUARDS
    with _metrics_lock:
        HALLUCINATION_GUARDS += 1


def record_parser_failure():
    global PARSER_FAILURES
    with _metrics_lock:
        PARSER_FAILURES += 1


def record_episode(domain='general'):
    global EPISODIC_TOTAL
    with _metrics_lock:
        EPISODIC_TOTAL += 1
        EPISODIC_DOMAINS[domain] = EPISODIC_DOMAINS.get(domain, 0) + 1


def record_embedding():
    global EPISODIC_EMBEDDINGS
    with _metrics_lock:
        EPISODIC_EMBEDDINGS += 1


def get_top_domains(limit=10):
    with _metrics_lock:
        sorted_domains = sorted(EPISODIC_DOMAINS.items(), key=lambda x: x[1], reverse=True)
        return [{'domain': d, 'count': c} for d, c in sorted_domains[:limit]]


def get_memory_size_mb():
    import os
    mem_file = "/opt/ai-lab/runtime/state/episodic_memory.jsonl"
    try:
        size = os.path.getsize(mem_file)
        return round(size / (1024 * 1024), 2)
    except:
        return 0


def record_memory_write():
    global MEMORY_WRITES
    with _metrics_lock:
        MEMORY_WRITES += 1


def record_failover():
    global FAILOVERS
    with _metrics_lock:
        FAILOVERS += 1


def get_model_selections(limit=50):
    with _metrics_lock:
        return list(MODEL_SELECTIONS[-limit:])




HOST = "0.0.0.0"
PORT = 8008

BACKENDS = [
    {"name": "rx9070", "url": "http://192.168.1.50:1234/v1", "enabled": True},
    {"name": "nas-n5", "url": "http://192.168.1.200:12345/v1", "enabled": False},
    {"name": "rx7900xt", "url": "http://192.168.1.60:1234/v1", "enabled": False},
]

PRIMARY_BACKEND = "rx9070"


def get_active_backend():
    for backend in BACKENDS:
        if backend["enabled"]:
            return backend

    return BACKENDS[0]

AGENT_PROMPT_FILE = Path("/opt/ai-lab/.agent/OPENCODE_PROMPT.md")


def load_agent_prompt():
    if not AGENT_PROMPT_FILE.exists():
        return (
            "Eres AI-LAB, un runtime cognitivo privado. "
            "Responde siempre en español, de forma clara, segura y operativa."
        )

    return AGENT_PROMPT_FILE.read_text(
        encoding="utf-8",
        errors="ignore",
    )


def sanitize_text(value):
    if not isinstance(value, str):
        return value

    return (
        value
        .replace("\ufffd", "")
        .replace("\x00", "")
        .strip()
    )


def inject_agent_context(payload):
    payload = sanitize_payload_messages(payload)
    messages = payload.get("messages", [])
    mode_name = current_mode()
    user_text = ""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user" and isinstance(msg.get("content"), str):
            user_text = msg.get("content", "")
            break

    payload = strip_question_tool(payload, user_text)
    prompt_route = detect_intent(user_text)
    observe_fastpath = prompt_route.mode == "observe" and not should_use_tool_fastpath(payload)
    route = classify_chat_route(
        payload,
        mode_name=mode_name,
        user_text=user_text,
        request_text=user_text,
        is_report_request=is_report_request(user_text),
        greeting_fastpath=should_use_greeting_fastpath(payload),
        tool_fastpath=should_use_tool_fastpath(payload),
        intent_mode=prompt_route.mode,
    )
    payload["_ai_lab_route_family"] = route.family
    payload["_ai_lab_route_variant"] = route.variant
    payload["_ai_lab_route_reason"] = route.reason
    record_route_family_metrics(route.family)
    try:
        if _HAVE_PROFILE_LOADER:
            payload = _apply_profile(payload, route.family)
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
                "model": payload.get("model", "default"),
                "mode": mode_name,
            },
        )
    except ImportError:
        pass

    if route.family == "minimal" and route.variant == "report":
        payload.pop("tools", None)
        payload.pop("tool_choice", None)
        payload["messages"] = build_minimal_report_messages(user_text)
        payload["model"] = "llama-3.1-8b-instruct"
        payload["max_tokens"] = min(int(payload.get("max_tokens", 180) or 180), 180)
        payload["temperature"] = min(float(payload.get("temperature", 0.1) or 0.1), 0.2)
        system_prompt = None
    elif route.family == "minimal" and route.variant == "casual":
        payload.pop("tools", None)
        payload.pop("tool_choice", None)
        payload["model"] = "llama-3.1-8b-instruct"
        payload["max_tokens"] = min(int(payload.get("max_tokens", 96) or 96), 96)
        payload["temperature"] = min(float(payload.get("temperature", 0.2) or 0.2), 0.2)
        system_prompt = (
            "Responde en espanol, breve y natural. "
            "No uses HARD_FACTS, no uses secciones y no inventes datos."
        )
    elif route.family == "observe":
        payload.pop("tools", None)
        payload.pop("tool_choice", None)
        payload["model"] = "llama-3.1-8b-instruct"
        system_prompt = (
            "Responde en espanol, natural y breve. Usa solo informacion observable. "
            "No uses HARD_FACTS, no uses secciones y no inventes datos. "
            "Si el usuario pide detalle, resume en 3-5 lineas. "
            f"OBSERVED_RUNTIME: {build_observe_context()}"
        )
        payload["max_tokens"] = min(int(payload.get("max_tokens", 180) or 180), 180)
        payload["temperature"] = min(float(payload.get("temperature", 0.1) or 0.1), 0.2)
    elif route.family == "minimal" and route.variant == "greeting":
        payload.pop("tools", None)
        payload.pop("tool_choice", None)
        system_prompt = (
            "Responde en espanol, muy breve y natural. "
            "No uses HARD_FACTS, no uses secciones y no inventes datos."
        )
        payload["model"] = "llama-3.1-8b-instruct"
        payload["max_tokens"] = min(int(payload.get("max_tokens", 96) or 96), 96)
        payload["temperature"] = min(float(payload.get("temperature", 0.2) or 0.2), 0.2)
    elif route.family == "tool_fastpath":
        system_prompt = (
            "Eres el gateway tool-aware de AI-LAB. "
            "Si necesitas usar una herramienta, emite tool_calls estructurados. "
            "Responde en espanol y evita contexto innecesario."
        )
    else:
        if _HAVE_PROMPT_LOADER:
            try:
                prompt_text, _warnings = _load_route_prompt(route.family, "")
                if prompt_text:
                    system_prompt = prompt_text
                else:
                    system_prompt = load_agent_prompt()
            except Exception:
                system_prompt = load_agent_prompt()
        else:
            system_prompt = load_agent_prompt()

    if is_report_request(user_text) and system_prompt is not None:
        system_prompt += (
            "\nPara solicitudes de informe, resumen, diagnóstico o auditoría, no uses la herramienta question. "
            "Genera la respuesta con los datos disponibles y marca lo que falte como NO DISPONIBLE."
        )

    if system_prompt is not None:
        injected = [
            {
                "role": "system",
                "content": system_prompt,
            }
        ]

        for msg in messages:
            injected.append(msg)

        payload["messages"] = injected

    if "temperature" not in payload:
        payload["temperature"] = 0.2

    if "max_tokens" not in payload:
        payload["max_tokens"] = 2048
    elif route.family in ("minimal", "observe"):
        pass
    elif payload.get("max_tokens", 0) < 1024:
        payload["max_tokens"] = 2048

    return payload


def sanitize_completion_response(data):
    choices = data.get("choices", [])

    for choice in choices:
        message = choice.get("message", {})

        tool_calls = extract_tool_calls_from_message(message)
        if tool_calls:
            safe_tool_calls, blocked_reason = filter_dangerous_tool_calls(tool_calls)
            if blocked_reason:
                record_blocked_prompt()
                GOVERNANCE_BLOCKED.inc()
                GOVERNANCE_BLOCKED_BY_REASON.labels(reason=blocked_reason).inc()
                message.pop("tool_calls", None)
                message["content"] = f"Solicitud bloqueada por policy: {blocked_reason}"
                choice["finish_reason"] = "stop"
            else:
                message["tool_calls"] = [repair_tool_call_arguments(tc) for tc in safe_tool_calls if isinstance(tc, dict)]
                message["content"] = None

        message.pop("reasoning_content", None)

        content = message.get("content", "")

        if content:
            message["content"] = sanitize_prompt_text(sanitize_text(content))

        if current_mode() == "observe" and isinstance(message.get("content"), str):
            message["content"] = sanitize_observe_output(message.get("content"))

        if not message.get("content") and not tool_calls:
            message["content"] = (
                "Respuesta generada, pero el contenido final "
                "llegó vacío desde el modelo."
            )

    return data


def backend_headers():
    return {
        "Content-Type": "application/json",
        "Authorization": "Bearer lm-studio",
    }


def _response_error_message(response):
    try:
        data = response.json()
        return str(data.get("error", {}).get("message", data.get("message", "")))
    except Exception:
        try:
            return response.text or ""
        except Exception:
            return ""


class GatewayHandler(BaseHTTPRequestHandler):
    timeout = 30

    def log_message(self, format, *args):
        print(
            "%s - - [%s] %s"
            % (
                self.client_address[0],
                self.log_date_time_string(),
                format % args,
            )
        )

    def _send_json(self, status, data):
        body = json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header(
            "Content-Length",
            str(len(body)),
        )
        self.end_headers()
        self.wfile.write(body)

    def _send_sse_headers(self):
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/event-stream; charset=utf-8",
        )
        self.send_header(
            "Cache-Control",
            "no-cache",
        )
        self.send_header(
            "Connection",
            "keep-alive",
        )
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        client_ip = self.client_address[0]
        if not check_rate_limit(client_ip):
            self._send_json(429, {"error": "rate_limit_exceeded", "message": "Too many requests. Try again later."})
            return
        if self.path == "/health":
            self._send_json(
                200,
                {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "backend": get_active_backend()["url"],
                    "mode": "stream-aware sanitized",
                    "time": int(time.time()),
                },
            )
            return

        
        
        if self.path == "/metrics":
            metrics = load_metrics()
            prom_text = (
                "# HELP ailab_requests_total Total requests\n"
                "# TYPE ailab_requests_total counter\n"
                f"ailab_requests_total {metrics.get('requests_total', 0)}\n"
                "# HELP ailab_streams_total Total streaming requests\n"
                "# TYPE ailab_streams_total counter\n"
                f"ailab_streams_total {metrics.get('streams_total', 0)}\n"
                "# HELP ailab_errors_total Total errors\n"
                "# TYPE ailab_errors_total counter\n"
                f"ailab_errors_total {metrics.get('errors_total', 0)}\n"
                "# HELP ailab_last_latency_ms Last request latency\n"
                "# TYPE ailab_last_latency_ms gauge\n"
                f"ailab_last_latency_ms {metrics.get('last_latency_ms', 0) or 0}\n"
                "# HELP ailab_active_streams Current active streams\n"
                "# TYPE ailab_active_streams gauge\n"
                f"ailab_active_streams {ACTIVE_STREAMS}\n"
                "# HELP ailab_routing_decisions_total Total routing decisions\n"
                "# TYPE ailab_routing_decisions_total counter\n"
                f"ailab_routing_decisions_total {ROUTING_DECISIONS}\n"
                "# HELP ailab_failovers_total Total failover events\n"
                "# TYPE ailab_failovers_total counter\n"
                f"ailab_memory_writes_total {MEMORY_WRITES}\n"
                + f"ailab_failovers_total {FAILOVERS}\n"
                + "# HELP ailab_episodic_total Total episodic memory entries\n"
                + "# TYPE ailab_episodic_total gauge\n"
                + f"ailab_episodic_total {EPISODIC_TOTAL}\n"
                + "# HELP ailab_episodic_embeddings_total Total embeddings created\n"
                + "# TYPE ailab_episodic_embeddings_total counter\n"
                + f"ailab_episodic_embeddings_total {EPISODIC_EMBEDDINGS}\n"
                + "# HELP ailab_episodic_memory_size_mb Episodic memory file size\n"
                + "# TYPE ailab_episodic_memory_size_mb gauge\n"
                + f"ailab_episodic_memory_size_mb {get_memory_size_mb()}\n"
                + "# HELP ailab_sessions_total Total sessions created\n"
                + "# TYPE ailab_sessions_total counter\n"
                + f"ailab_sessions_total {SESSION_COUNTER}\n"
                + "# HELP ailab_sessions_concurrent Current concurrent sessions\n"
                + "# TYPE ailab_sessions_concurrent gauge\n"
                + f"ailab_sessions_concurrent {len([s for s in SESSION_STORE.values() if s['status'] == 'active'])}\n"
                + "# HELP ailab_sessions_orphan Total orphan sessions\n"
                + "# TYPE ailab_sessions_orphan counter\n"
                + f"ailab_sessions_orphan {ORPHAN_SESSIONS}\n"
                + "# HELP ailab_episodic_recalls_total Total episodic recalls\n"
                + "# TYPE ailab_episodic_recalls_total counter\n"
                + f"ailab_episodic_recalls_total {EPISODIC_RECALLS}\n"
                + "# HELP ailab_accumulated_memory_total Accumulated memory tokens\n"
                + "# TYPE ailab_accumulated_memory_total counter\n"
                + f"ailab_accumulated_memory_total {ACCUMULATED_MEMORY}\n"
                + "# HELP ailab_governance_blocked_prompts_total Blocked prompts\n"
                + "# TYPE ailab_governance_blocked_prompts_total counter\n"
                + f"ailab_governance_blocked_prompts_total {BLOCKED_PROMPTS}\n"
                + "# HELP ailab_governance_sanitizations_total Sanitizations performed\n"
                + "# TYPE ailab_governance_sanitizations_total counter\n"
                + f"ailab_governance_sanitizations_total {SANITIZATIONS}\n"
                + "# HELP ailab_governance_rate_limit_hits_total Rate limit blocked requests\n"
                + "# TYPE ailab_governance_rate_limit_hits_total counter\n"
                + f"ailab_governance_rate_limit_hits_total {RATE_LIMIT_HITS}\n"
                + "# HELP ailab_governance_context_overflows_total Context size overflow errors\n"
                + "# TYPE ailab_governance_context_overflows_total counter\n"
                + f"ailab_governance_context_overflows_total {CONTEXT_OVERFLOWS}\n"
                + "# HELP ailab_governance_hallucination_guards_total Hallucination guard activations\n"
                + "# TYPE ailab_governance_hallucination_guards_total counter\n"
                + f"ailab_governance_hallucination_guards_total {HALLUCINATION_GUARDS}\n"
                + "# HELP ailab_governance_parser_failures_total Parser failures\n"
                + "# TYPE ailab_governance_parser_failures_total counter\n"
                + f"ailab_governance_parser_failures_total {PARSER_FAILURES}\n"
                + "\n# ── prometheus_client managed metrics ──\n"
                + prom_generate_latest(prom_REGISTRY).decode("utf-8")
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(prom_text.encode("utf-8"))
            return


        if self.path == "/api/v1/models/selections":
            selections = get_model_selections(100)
            body = json.dumps(selections, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return




        if self.path == "/api/v1/governance":
            data = {
                "blocked_prompts": BLOCKED_PROMPTS,
                "sanitizations": SANITIZATIONS,
                "rate_limit_hits": RATE_LIMIT_HITS,
                "context_overflows": CONTEXT_OVERFLOWS,
                "hallucination_guards": HALLUCINATION_GUARDS,
                "parser_failures": PARSER_FAILURES,
            }
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/api/v1/episodic":
            data = {
                "total": EPISODIC_TOTAL,
                "embeddings": EPISODIC_EMBEDDINGS,
                "size_mb": get_memory_size_mb(),
                "top_domains": get_top_domains(10),
            }
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/api/v1/sessions":
            sessions = get_sessions(100)
            body = json.dumps(sessions, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/runtime/topology":
            self._send_json(
                200,
                get_topology()
            )
            return

        if self.path == "/runtime/status":

            self._send_json(
                200,
                runtime_snapshot()
            )
            return

        if self.path == "/gateway/metrics":

            self._send_json(
                200,
                load_metrics(),
            )
            return

        if self.path == "/v1/models":
            start_time = time.time()

            try:
                response = requests.get(
                    f"{get_active_backend()['url']}/models",
                    headers=backend_headers(),
                    timeout=(5, 30),
                )

                latency_ms = int(
                    (time.time() - start_time) * 1000
                )

                record_routing_decision()
                record_request(
                    self.path,
                    model=None,
                    latency_ms=latency_ms,
                    stream=False,
                )

                self._send_json(
                    response.status_code,
                    response.json(),
                )

            except Exception as exc:
                record_error(
                    self.path,
                    exc,
                )

                self._send_json(
                    502,
                    {
                        "error": "gateway_models_proxy_failed",
                        "detail": str(exc),
                    },
                )

            return

        self._send_json(
            404,
            {
                "error": "not_found",
                "path": self.path,
            },
        )

    def do_POST(self):
        client_ip = self.client_address[0]
        route_family = "unknown"
        if not check_rate_limit(client_ip):
            self._send_json(429, {"error": "rate_limit_exceeded", "message": "Too many requests. Try again later."})
            return
        if self.path != "/v1/chat/completions":
            self._send_json(
                404,
                {
                    "error": "not_found",
                    "path": self.path,
                },
            )
            return

        start_time = time.time()

        try:
            content_length = int(
                self.headers.get(
                    "Content-Length",
                    "0",
                )
            )

            raw_body = self.rfile.read(content_length)

            payload = json.loads(
                raw_body.decode("utf-8")
            )

            payload = inject_agent_context(payload)
            route_family = payload.pop("_ai_lab_route_family", "cognitive")
            payload.pop("_ai_lab_route_variant", None)
            payload.pop("_ai_lab_route_reason", None)

            requested_model = payload.get(
                "model",
                "default"
            )

            observe_user_text = ""
            for msg in reversed(payload.get("messages", [])):
                if isinstance(msg, dict) and msg.get("role") == "user" and isinstance(msg.get("content"), str):
                    observe_user_text = msg.get("content", "")
                    break
            task_type = infer_task(observe_user_text or "")
            observe_fastpath = detect_intent(observe_user_text).mode == "observe" and not should_use_tool_fastpath(payload)

            selected_model = choose_model(task_type)
            if route_family in {"minimal", "observe"}:
                selected_model = "llama-3.1-8b-instruct"
            if route_family in {"minimal", "observe"}:
                selected_model = "llama-3.1-8b-instruct"
            elif (current_mode() == "observe" or observe_fastpath) and not should_use_tool_fastpath(payload):
                selected_model = "llama-3.1-8b-instruct"
            elif should_use_greeting_fastpath(payload):
                selected_model = "llama-3.1-8b-instruct"
            elif task_type in ("fast", "general", "coding"):
                selected_model = "qwen2.5-coder-14b-instruct"
            session_id = create_session(task_type, selected_model, get_active_backend()["name"])
            payload["model"] = selected_model

            stream_enabled = bool(
                payload.get("stream", False)
            )

            upstream_payload = dict(payload)
            upstream_payload.pop("stream", None)

            response = requests.post(
                f"{get_active_backend()['url']}/chat/completions",
                headers=backend_headers(),
                json=upstream_payload,
                stream=False,
                timeout=(10, 600),
            )

            if response.status_code >= 400:
                error_msg = _response_error_message(response)
                if "unloaded" in error_msg.lower():
                    response.close()
                    response = requests.post(
                        f"{get_active_backend()['url']}/chat/completions",
                        headers=backend_headers(),
                        json=upstream_payload,
                        stream=False,
                        timeout=(10, 600),
                    )

            latency_ms = int(
                (time.time() - start_time) * 1000
            )

            record_routing_decision()
            record_request(
                self.path,
                model=payload.get("model"),
                latency_ms=latency_ms,
                stream=stream_enabled,
            )
            record_model_selection(task_type, selected_model, get_active_backend()["name"], latency_ms)

            if stream_enabled:
                if response.status_code >= 400:
                    record_route_family_metrics(route_family, count=False, latency_ms=latency_ms, error=True)
                    try:
                        self._send_json(
                            response.status_code,
                            response.json(),
                        )
                    except Exception:
                        self._send_json(
                            response.status_code,
                            {"error": "upstream_error", "detail": _response_error_message(response)},
                        )
                    return

                register_stream()
                self._send_sse_headers()

                try:
                    data = response.json()
                except Exception as exc:
                    record_error(self.path, exc)
                    record_route_family_metrics(route_family, count=False, latency_ms=latency_ms, error=True)
                    self._send_json(502, {"error": "gateway_stream_decode_failed", "detail": str(exc)})
                    return

                choices = data.get("choices", [])
                first_choice = choices[0] if choices else {}
                message = first_choice.get("message", {}) if isinstance(first_choice, dict) else {}

                chunk_id = data.get("id", "chatcmpl-" + str(int(time.time())))
                model_name = data.get("model", selected_model)
                base = {"id": chunk_id, "object": "chat.completion.chunk", "model": model_name}

                delta = {"role": "assistant"}
                if isinstance(message.get("content"), str) and message.get("content"):
                    delta["content"] = message.get("content")
                if message.get("tool_calls"):
                    delta["tool_calls"] = [repair_tool_call_arguments(tc) for tc in message.get("tool_calls") if isinstance(tc, dict)]

                self.wfile.write(
                    f"data: {json.dumps({**base, 'choices': [{'index': 0, 'delta': delta, 'finish_reason': None}]}, ensure_ascii=False)}\n\n".encode("utf-8")
                )
                self.wfile.flush()

                finish_reason = first_choice.get("finish_reason", "stop") if isinstance(first_choice, dict) else "stop"
                self.wfile.write(
                    f"data: {json.dumps({**base, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': finish_reason}]}, ensure_ascii=False)}\n\n".encode("utf-8")
                )
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()

                try:
                    from runtime.routing.routing_history import record_route_result as _rrr
                    _rrr(task_type=task_type, model=selected_model,
                         node=get_active_backend()["name"], host=get_active_backend()["url"],
                         latency_ms=latency_ms, success=True, stream=True, failover=False)
                except ImportError:
                    pass

                usage = data.get("usage", {}) if isinstance(data, dict) else {}
                record_route_family_metrics(
                    route_family,
                    count=False,
                    latency_ms=latency_ms,
                    prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
                    completion_tokens=int(usage.get("completion_tokens", 0) or 0),
                )

                return

            data = response.json()

            data = sanitize_completion_response(data)

            self._send_json(
                response.status_code,
                data,
            )

            try:
                from runtime.routing.routing_history import record_route_result as _rrr
                _rrr(task_type=task_type, model=selected_model,
                     node=get_active_backend()["name"], host=get_active_backend()["url"],
                     latency_ms=latency_ms, success=True, stream=False, failover=False)
            except ImportError:
                pass

            usage = data.get("usage", {}) if isinstance(data, dict) else {}
            blocked = False
            for choice in data.get("choices", []):
                msg = choice.get("message", {}) if isinstance(choice, dict) else {}
                if msg.get("content", "").startswith("Solicitud bloqueada por policy"):
                    blocked = True
                    break
            record_route_family_metrics(
                route_family,
                count=False,
                latency_ms=latency_ms,
                prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
                completion_tokens=int(usage.get("completion_tokens", 0) or 0),
                blocked=blocked,
            )

        except requests.exceptions.RequestException as exc:
            latency_ms = int((time.time() - start_time) * 1000)
            record_error(self.path, exc)
            record_route_family_metrics(route_family, count=False, latency_ms=latency_ms, error=True)
            self._send_json(502, {"error": "backend_unreachable", "detail": str(exc)})
            try:
                from runtime.routing.routing_history import record_route_result as _rrr
                _rrr(task_type=task_type, model=selected_model,
                     node=get_active_backend()["name"], host=get_active_backend()["url"],
                     latency_ms=latency_ms, success=False, stream=stream_enabled,
                     failover=False, error=str(exc))
            except ImportError:
                pass

        except Exception as exc:
            latency_ms = int((time.time() - start_time) * 1000)
            record_error(self.path, exc)
            record_route_family_metrics(route_family, count=False, latency_ms=latency_ms, error=True)
            self._send_json(500, {"error": "gateway_error", "detail": str(exc)})
            try:
                from runtime.routing.routing_history import record_route_result as _rrr
                _rrr(task_type=task_type, model=selected_model if 'selected_model' in locals() else "unknown",
                     node=get_active_backend()["name"], host=get_active_backend()["url"],
                     latency_ms=latency_ms, success=False, stream=False,
                     failover=False, error=str(exc))
            except ImportError:
                pass


def run():
    server = ThreadingHTTPServer(
        (HOST, PORT),
        GatewayHandler,
    )

    print("AI-LAB OPENAI GATEWAY")
    print("=====================")
    print(f"Listening: http://{HOST}:{PORT}")
    backend = get_active_backend()
    print(f"Backend:   {backend['name']} @ {backend['url']}")
    print("Mode:      stream-aware sanitized + metrics")
    print()

    server.serve_forever()


if __name__ == "__main__":
    run()
