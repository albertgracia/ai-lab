import os
os.environ.setdefault("AI_LAB_ENABLE_MEMORY_INJECTOR", "true")
os.environ.setdefault("AI_LAB_REAL_STREAMING", "true")

import json
import signal
import sys
import time
import atexit
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
from runtime.gateway.tool_request_classifier import build_minimal_report_messages, build_observe_context, build_observe_context_compact, build_capability_answer, classify_chat_route, is_report_request, is_report_request_heavy, sanitize_observe_output, sanitize_payload_messages, sanitize_prompt_text, should_use_greeting_fastpath, should_use_tool_fastpath, strip_question_tool, is_lightweight_prompt, get_qwen_escalation_reason
from runtime.context.report_runtime_context import format_report_runtime_context, extract_target_ip
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

# ── FASE 29.4: SLO Enforcement & Adaptive Runtime Protection ──
try:
    from runtime.slo import (
        RuntimeSLOManager,
        SLOState,
        DegradationManager,
        AdaptiveConcurrency,
        PrioritySlotManager,
        CircuitBreakerRegistry,
        is_slo_enabled,
        is_slo_dry_run,
        get_lane_for_route,
    )
    _slo_state = SLOState()
    _slo_manager = RuntimeSLOManager(_slo_state)
    _degradation = DegradationManager()
    _adaptive_concurrency = AdaptiveConcurrency()
    _priority_slots = PrioritySlotManager()
    _circuit_breakers = CircuitBreakerRegistry()
    _HAVE_SLO = True
except ImportError:
    _slo_state = None
    _slo_manager = None
    _degradation = None
    _adaptive_concurrency = None
    _priority_slots = None
    _circuit_breakers = None
    _HAVE_SLO = False

# ── FASE 28.1: Planner Runtime Skeleton ──
os.environ.setdefault("AI_LAB_ENABLE_PLANNER", "false")
os.environ.setdefault("AI_LAB_PLANNER_DRY_RUN", "true")

try:
    from runtime.agentic.planner import Planner
    from runtime.agentic.governance_hooks import validate_plan_against_policy
    from runtime.agentic.permissions import PermissionScope
    _planner = Planner()
    _HAVE_PLANNER = True
except ImportError:
    _planner = None  # type: ignore[assignment]
    _HAVE_PLANNER = False

AI_LAB_ENABLE_PLANNER = os.environ.get("AI_LAB_ENABLE_PLANNER", "false").lower() == "true"
AI_LAB_PLANNER_DRY_RUN = os.environ.get("AI_LAB_PLANNER_DRY_RUN", "true").lower() != "false"

_warmed_models = set()

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

    # FASE 25+26: OpenCode/OpenWebUI production guard
    if payload.get("_client") in ("opencode", "openwebui"):
        payload["_client_profile"] = payload["_client"]
        tools = payload.get("tools")
        if isinstance(tools, list):
            payload["tools"] = [t for t in tools if (t.get("function", {}).get("name", "") if isinstance(t.get("function"), dict) else "") != "question"]
        if not payload.get("tools"):
            payload.pop("tool_choice", None)
            payload.pop("tools", None)
        user_text = ""
        for msg in reversed(payload.get("messages", [])):
            if isinstance(msg, dict) and msg.get("role") == "user":
                user_text = msg.get("content", "") if isinstance(msg.get("content"), str) else ""
                break
        hf_keywords = ("razonamiento", "auditoría", "arquitectura", "debug profundo", "analiza la arquitectura")
        if not any(kw in (user_text or "").lower() for kw in hf_keywords):
            payload["_suppress_hard_facts"] = True
        payload["_wrapper_suppressed"] = True

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
                "model": payload.get("model", "default"),
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
                "_request_id": payload.get("_request_id", ""),
                "_trace_family": payload.get("_trace_family", ""),
            })
        except ImportError:
            pass

    _report_runtime = None
    _report_grounded_target = None
    if route.family in ("minimal", "report") and route.variant in ("report", "heavy"):
        try:
            _report_runtime = format_report_runtime_context()
            _report_grounded_target = extract_target_ip(user_text)
            payload["_report_grounded"] = True
            if _report_grounded_target:
                payload["_report_grounded_target"] = _report_grounded_target
            try:
                from runtime.telemetry.prometheus_metrics import (
                    REPORT_GROUNDING_TOTAL, REPORT_MISSING_FIELDS_TOTAL,
                    REPORT_TARGET_IP_TOTAL, REPORT_UNGROUNDED_TOTAL,
                )
                REPORT_GROUNDING_TOTAL.inc()
                if _report_grounded_target:
                    REPORT_TARGET_IP_TOTAL.inc()
                import json as _json
                _ctx = _json.loads(_report_runtime)
                _miss = _ctx.get("missing_fields", [])
                if _miss:
                    REPORT_MISSING_FIELDS_TOTAL.labels(count=str(len(_miss))).inc()
                if not _ctx.get("observed_fields"):
                    REPORT_UNGROUNDED_TOTAL.inc()
            except ImportError:
                pass
        except Exception:
            pass

    if route.family == "minimal" and route.variant == "report":
        payload.pop("tools", None)
        payload.pop("tool_choice", None)
        payload["messages"] = build_minimal_report_messages(user_text, observed_runtime=_report_runtime)
        payload["max_tokens"] = min(int(payload.get("max_tokens", 512) or 512), 512)
        payload["temperature"] = min(float(payload.get("temperature", 0.1) or 0.1), 0.2)
        system_prompt = None
    elif route.family == "minimal" and route.variant == "capability":
        payload.pop("tools", None)
        payload.pop("tool_choice", None)
        payload["_capability_answer"] = build_capability_answer()
        system_prompt = None
    elif route.family == "minimal" and route.variant == "creative":
        payload.pop("tools", None)
        payload.pop("tool_choice", None)
        payload["model"] = "qwen/qwen2.5-coder-14b-instruct"
        payload["max_tokens"] = min(int(payload.get("max_tokens", 2048) or 2048), 2048)
        payload["temperature"] = min(float(payload.get("temperature", 0.7) or 0.7), 0.8)
        system_prompt = "Eres un escritor creativo en espanol. Desarrolla la peticion sin excusas. Si el texto es muy largo, entrega una primera parte clara y ofrece continuar."
        try:
            from runtime.telemetry.prometheus_metrics import CREATIVE_REQUESTS_TOTAL
            CREATIVE_REQUESTS_TOTAL.inc()
        except ImportError:
            pass
    elif route.family == "report":
        payload.pop("tools", None)
        payload.pop("tool_choice", None)
        payload["model"] = "qwen2.5-coder-14b-instruct"
        payload["messages"] = build_minimal_report_messages(user_text, observed_runtime=_report_runtime)
        payload["max_tokens"] = min(int(payload.get("max_tokens", 1024) or 1024), 1024)
        payload["temperature"] = min(float(payload.get("temperature", 0.3) or 0.3), 0.3)
        system_prompt = None
    elif route.family == "minimal" and route.variant == "casual":
        payload["temperature"] = min(float(payload.get("temperature", 0.2) or 0.2), 0.2)
        system_prompt = (
            "Responde en espanol, breve y natural. "
            "No uses HARD_FACTS, no uses secciones y no inventes datos."
        )
    elif route.family == "observe":
        system_prompt = (
            "Responde en espanol, natural y breve. Usa solo informacion observable. "
            "No uses HARD_FACTS, no uses secciones y no inventes datos. "
            "Si el usuario pide detalle, resume en 3-5 lineas. "
            f"OBSERVED_RUNTIME: {build_observe_context()}"
        )
        payload["max_tokens"] = min(int(payload.get("max_tokens", 180) or 180), 180)
    elif route.family == "minimal" and route.variant == "greeting":
        system_prompt = (
            "Responde en espanol, muy breve y natural. "
            "No uses HARD_FACTS, no uses secciones y no inventes datos."
        )
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

    # FASE 27.1-B: governed memory recall injection
    try:
        mem_profile = payload.get("_profile", route.family)
        from runtime.policies.memory.memory_loader import get_policy_for_profile
        mem_policy = get_policy_for_profile(mem_profile)
        if mem_policy.get("semantic_recall") and mem_policy.get("sources") and user_text:
            from runtime.policies.memory.memory_injector import build_memory_context
            mem_ctx = build_memory_context(mem_policy, user_text, route.family)
            if not mem_ctx.get("skipped") and mem_ctx.get("items"):
                mem_block = "MEMORIA RELEVANTE:\n" + "\n".join(
                    f"[{i['source']}] {i['text'][:200]}" for i in mem_ctx["items"]
                )
                system_prompt = (system_prompt or "") + "\n\n" + mem_block
    except ImportError:
        pass

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

        # FASE 26.1.1: preserve valid content even if finish_reason="length"
        finish = choice.get("finish_reason", "stop") if isinstance(choice, dict) else "stop"
        content_len = len(message.get("content") or "")

        if not message.get("content") and not tool_calls:
            if finish == "length":
                message["content"] = (
                    "La respuesta fue truncada por limite de tokens antes de generar contenido visible. "
                    "Reintenta con un limite mayor o usa un perfil de informe."
                )
                try:
                    from runtime.telemetry.prometheus_metrics import COMPLETION_EMPTY_AFTER_TRUNCATION
                    COMPLETION_EMPTY_AFTER_TRUNCATION.inc()
                except ImportError:
                    pass
            else:
                message["content"] = (
                    "Respuesta generada, pero el contenido final "
                    "llegó vacío desde el modelo."
                )

        if finish == "length" and content_len > 0:
            try:
                from runtime.telemetry.prometheus_metrics import COMPLETION_TRUNCATED
                COMPLETION_TRUNCATED.labels(route_family="unknown").inc()
            except ImportError:
                pass
            print(
                f"FASE26.1.1 completion_truncated_but_valid "
                f"finish_reason=length chars={content_len}",
                flush=True,
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

        # FASE 29.4: SLO health endpoint
        if self.path == "/slo/health":
            if _HAVE_SLO:
                self._send_json(200, _slo_manager.get_runtime_health())
            else:
                self._send_json(503, {"error": "slo_module_unavailable"})
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
        import uuid as _uuid
        _request_id = str(_uuid.uuid4())[:8]
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

            # FASE 25/26: detect OpenCode/OpenWebUI client from headers
            ua = str(self.headers.get("User-Agent", "")).lower()
            xclient = str(self.headers.get("X-AI-LAB-Client", "")).lower()
            if "opencode" in ua or "opencode" in xclient:
                payload["_client"] = "opencode"
            elif "openwebui" in ua or "openwebui" in xclient:
                payload["_client"] = "openwebui"

            payload["_request_id"] = _request_id
            payload = inject_agent_context(payload)

            # FASE 26.2.3: capability answers — early return, no LM Studio
            capability_answer = payload.pop("_capability_answer", None)
            if capability_answer:
                self._send_json(200, {
                    "id": f"chatcmpl-capability-{_request_id}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": "llama-3.1-8b-instruct",
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": capability_answer}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                })
                return

            # FASE 22B.4: confirmation gate for write/agentic tools
            if payload.get("_tool_requires_confirmation"):
                write_names = {"write", "edit", "rm", "mv", "cp", "dd", "tee", "bash"}
                tools = payload.get("tools") or []
                write_tools = [
                    (t.get("function") or {}).get("name", "")
                    for t in tools if isinstance(t, dict)
                    and ((t.get("function") or {}).get("name", "") in write_names)
                ]
                if write_tools:
                    payload["_tool_confirmation_pending"] = True
                    try:
                        from runtime.telemetry.prometheus_metrics import CONFIRMATION_REQUIRED
                        CONFIRMATION_REQUIRED.inc()
                    except ImportError:
                        pass
                    self._send_json(428, {
                        "error": "confirmation_required",
                        "message": "Esta solicitud contiene herramientas de escritura. Confirma explicitamente para continuar.",
                        "tool_policy": payload.get("_tool_policy"),
                        "tool_mode": payload.get("_tool_mode"),
                        "tool_names": write_tools,
                    })
                    return

            payload["_request_id"] = _request_id
            route_family = payload.pop("_ai_lab_route_family", "cognitive")
            route_variant = payload.pop("_ai_lab_route_variant", "")
            payload.pop("_ai_lab_route_reason", None)
            payload["_trace_family"] = route_family

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
            if route_variant == "creative" or route_family == "report":
                selected_model = "qwen/qwen2.5-coder-14b-instruct"
            elif route_family in {"minimal", "observe"}:
                # FASE 29.3.1: but if message demands qwen14b (deep reasoning), escalate
                escalation = get_qwen_escalation_reason(observe_user_text)
                if escalation and route_family == "observe":
                    selected_model = "qwen2.5-coder-14b-instruct"
                    try:
                        from runtime.telemetry.prometheus_metrics import record_qwen_escalation
                        record_qwen_escalation(f"observe_override:{escalation}")
                    except ImportError:
                        pass
                else:
                    selected_model = "llama-3.1-8b-instruct"
            # FASE 29.3.1: don't override qwen escalation with observe fastpath
            _already_qwen = "qwen" in (selected_model or "").lower()
            if (current_mode() == "observe" or observe_fastpath) and not should_use_tool_fastpath(payload) and not _already_qwen:
                selected_model = "llama-3.1-8b-instruct"
            elif should_use_greeting_fastpath(payload):
                selected_model = "llama-3.1-8b-instruct"
                try:
                    from runtime.telemetry.prometheus_metrics import record_greeting_fastpath
                    record_greeting_fastpath()
                except ImportError:
                    pass
            # FASE 29.3.1: Lightweight prompt heuristic — short/simple → llama
            elif is_lightweight_prompt(observe_user_text):
                selected_model = "llama-3.1-8b-instruct"
                try:
                    from runtime.telemetry.prometheus_metrics import record_llama_fastpath
                    record_llama_fastpath()
                except ImportError:
                    pass
            elif task_type in ("fast", "general", "coding"):
                escalation_reason = get_qwen_escalation_reason(observe_user_text)
                if escalation_reason:
                    selected_model = "qwen2.5-coder-14b-instruct"
                    try:
                        from runtime.telemetry.prometheus_metrics import record_qwen_escalation
                        record_qwen_escalation(escalation_reason)
                    except ImportError:
                        pass
                else:
                    selected_model = "llama-3.1-8b-instruct"

            # FASE 29.3: Hard guard — qwen3.6-27b disabled, redirect to qwen2.5-14b
            DISABLED_MODELS = {"qwen3.6-27b", "qwen/qwen3.6-27b", "lmstudio-community/qwen3.6-27b"}
            if selected_model in DISABLED_MODELS or "qwen3.6" in (selected_model or "").lower():
                original = selected_model
                selected_model = "qwen2.5-coder-14b-instruct"
                try:
                    from runtime.telemetry.prometheus_metrics import record_disabled_model_selection
                    record_disabled_model_selection(original, "disabled_model_redirect")
                except ImportError:
                    pass

            # FASE 29.4: Degradation-based model override
            if _HAVE_SLO:
                _degradation_level = _degradation.get_current_level()
                if _degradation.should_force_llama(_degradation_level):
                    selected_model = "llama-3.1-8b-instruct"
                    _degradation.record_llama_forced("degradation_force_llama", is_slo_dry_run())
                elif _degradation.should_pause_qwen_routing(_degradation_level):
                    if "qwen" in (selected_model or "").lower():
                        selected_model = "llama-3.1-8b-instruct"
                        _degradation.record_llama_forced("degradation_pause_qwen", is_slo_dry_run())
                elif _degradation.should_block_qwen_escalation(_degradation_level):
                    if route_family in {"minimal", "observe"} and "qwen" in (selected_model or "").lower():
                        selected_model = "llama-3.1-8b-instruct"
                        _degradation.record_qwen_protection("degradation_block_escalation", is_slo_dry_run())

            if selected_model not in _warmed_models:
                _warmed_models.add(selected_model)
                try:
                    from runtime.telemetry.prometheus_metrics import COLD_START_TOTAL
                    COLD_START_TOTAL.labels(model=selected_model).inc()
                except ImportError:
                    pass

            session_id = create_session(task_type, selected_model, get_active_backend()["name"])
            payload["model"] = selected_model

            stream_enabled = bool(
                payload.get("stream", False)
            )

            upstream_payload = dict(payload)

            # FASE 29.2: Real Streaming — pass stream=true to LM Studio
            _real_streaming = False
            try:
                from runtime.gateway.stream_sanitizer import is_real_streaming_enabled
                _real_streaming = is_real_streaming_enabled()
            except ImportError:
                pass

            if _real_streaming and stream_enabled:
                upstream_payload["stream"] = True
            else:
                upstream_payload.pop("stream", None)

            response = requests.post(
                f"{get_active_backend()['url']}/chat/completions",
                headers=backend_headers(),
                json=upstream_payload,
                stream=stream_enabled if _real_streaming else False,
                timeout=(10, 600),
            )

            # FASE 27.1: track TTFB + request total latency
            ttfb_ms = int((time.time() - start_time) * 1000)
            try:
                from runtime.telemetry.prometheus_metrics import FIRST_TOKEN_LATENCY, REQUEST_TOTAL_LATENCY
                FIRST_TOKEN_LATENCY.labels(model=selected_model).observe(float(ttfb_ms))
            except ImportError:
                pass
            try:
                from runtime.telemetry.prometheus_metrics import GPU_ACTIVE_REQUESTS, GPU_ESTIMATED_UTILIZATION
                GPU_ACTIVE_REQUESTS.inc()
                GPU_ESTIMATED_UTILIZATION.set(min(100, float(GPU_ACTIVE_REQUESTS._value.get()) / 4.0 * 100))
            except ImportError:
                pass

            # FASE 29.4: Record TTFB to SLO state
            if _HAVE_SLO:
                _slo_state.record_ttfb(float(ttfb_ms))
                _slo_state.record_gpu_state(
                    min(1.0, float(GPU_ACTIVE_REQUESTS._value.get()) / 4.0),
                    0.0,
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

            # FASE 27.1: track total request latency + completion duration
            try:
                from runtime.telemetry.prometheus_metrics import REQUEST_TOTAL_LATENCY, COMPLETION_STREAM_DURATION
                REQUEST_TOTAL_LATENCY.labels(route_family=route_family or "unknown").observe(float(latency_ms))
                completion_ms = latency_ms - ttfb_ms if 'ttfb_ms' in dir() and ttfb_ms else latency_ms
                COMPLETION_STREAM_DURATION.labels(model=selected_model).observe(float(completion_ms))
            except ImportError:
                pass
            try:
                from runtime.telemetry.prometheus_metrics import GPU_ACTIVE_REQUESTS
                GPU_ACTIVE_REQUESTS.dec()
            except ImportError:
                pass

            # FASE 29.4: Periodic SLO evaluation + adaptive concurrency
            if _HAVE_SLO:
                _slo_state.record_gpu_state(
                    min(1.0, float(GPU_ACTIVE_REQUESTS._value.get()) / 4.0) if 'GPU_ACTIVE_REQUESTS' in dir() else 0.0,
                    0.0,
                )
                slo_state_code = _slo_manager.evaluate_slo_state()
                slo_snap = _slo_state.get_snapshot()
                _degradation.evaluate_and_apply(slo_state_code, slo_snap, is_slo_dry_run())
                _adaptive_concurrency.update(
                    gpu_util=slo_snap["gpu_util"],
                    vram_pressure=slo_snap["vram_pressure"],
                    timeout_rate=slo_snap["timeout_rate"],
                    degradation_level=_degradation.get_current_level(),
                    dry_run=is_slo_dry_run(),
                )
                _slo_manager.update_metrics()
                # Push adaptive concurrency limit to stream_sanitizer
                try:
                    from runtime.gateway.stream_sanitizer import set_max_streams
                    set_max_streams(_adaptive_concurrency.get_streams_max())
                except ImportError:
                    pass

            record_routing_decision()
            record_request(
                self.path,
                model=payload.get("model"),
                latency_ms=latency_ms,
                stream=stream_enabled,
            )
            record_model_selection(task_type, selected_model, get_active_backend()["name"], latency_ms)

            # FASE 29.4: Record stream backlog
            if _HAVE_SLO:
                try:
                    from runtime.gateway.stream_sanitizer import get_stream_stats
                    _sstats = get_stream_stats()
                    _slo_state.record_stream_metrics(
                        backlog=max(0, _sstats.get("active_streams", 0)),
                        active=_sstats.get("active_streams", 0),
                    )
                except ImportError:
                    pass

            if stream_enabled:
                if response.status_code >= 400:
                    if _HAVE_SLO:
                        _circuit_breakers.record_failure(selected_model)
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

                # FASE 29.2: Real Streaming path
                if _real_streaming:
                    try:
                        chunk_count = relay_stream(response, self, selected_model)
                        # Record real TTFB and metrics
                        try:
                            from runtime.telemetry.prometheus_metrics import record_stream_first_chunk
                            from runtime.telemetry.prometheus_metrics import STREAM_CHUNKS_TOTAL
                            if chunk_count:
                                for _ in range(chunk_count):
                                    STREAM_CHUNKS_TOTAL.inc()
                        except ImportError:
                            pass
                        # FASE 29.4: circuit breaker success
                        if _HAVE_SLO and chunk_count and chunk_count > 0:
                            _circuit_breakers.record_success(selected_model)
                    except Exception as exc:
                        record_error(self.path, exc)
                        record_route_family_metrics(route_family, count=False, latency_ms=latency_ms, error=True)
                        if _HAVE_SLO:
                            _circuit_breakers.record_failure(selected_model)
                    return

                # Legacy: Fake SSE path (FASE 27.1.1 — fallback when AI_LAB_REAL_STREAMING=false)
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
                has_content = isinstance(message.get("content"), str) and message.get("content")
                if has_content:
                    delta["content"] = message.get("content")
                if message.get("tool_calls"):
                    delta["tool_calls"] = [repair_tool_call_arguments(tc) for tc in message.get("tool_calls") if isinstance(tc, dict)]

                try:
                    from runtime.telemetry.prometheus_metrics import STREAM_CHUNKS_TOTAL, STREAM_EMPTY_CHUNKS
                    STREAM_CHUNKS_TOTAL.inc()
                    if not has_content and not message.get("tool_calls"):
                        STREAM_EMPTY_CHUNKS.inc()
                except ImportError:
                    pass

                self.wfile.write(
                    f"data: {json.dumps({**base, 'choices': [{'index': 0, 'delta': delta, 'finish_reason': None}]}, ensure_ascii=False)}\n\n".encode("utf-8")
                )
                self.wfile.flush()

                finish_reason = first_choice.get("finish_reason", "stop") if isinstance(first_choice, dict) else "stop"
                try:
                    if not has_content and not message.get("tool_calls") and finish_reason == "stop":
                        from runtime.telemetry.prometheus_metrics import STREAM_FINISH_INCONSISTENT
                        STREAM_FINISH_INCONSISTENT.inc()
                except ImportError:
                    pass
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

            # FASE 28.0: Agentic Pipeline (simulation-only) — BEFORE sending response
            _agentic_content = ""
            _agentic_choices = data.get("choices", [])
            for _ac in _agentic_choices:
                _agentic_msg = _ac.get("message", {}) if isinstance(_ac, dict) else {}
                _agentic_content = _agentic_msg.get("content", "") if isinstance(_agentic_msg.get("content"), str) else ""
                break
            try:
                from runtime.agentic.intents import IntentParser
                intents = IntentParser.from_llm_response(_agentic_content)
                if intents:
                    from runtime.agentic.planner import Planner
                    from runtime.agentic.dryrun import DryRunEngine
                    from runtime.agentic.explainability import ExplainabilityEngine
                    from runtime.agentic.executor import SimulationExecutor
                    from runtime.agentic.verifier import Verifier
                    from runtime.agentic.workflow_state import WorkflowState, WorkflowTimeline
                    from runtime.telemetry.prometheus_metrics import (
                        record_agentic_plan, record_agentic_dry_run,
                        record_agentic_risk_score, record_agentic_execution,
                        record_agentic_action, record_agentic_execution_duration,
                    )

                    plan = Planner.plan(intents, request_id=payload.get("_request_id", ""))
                    record_agentic_plan(route_family or "unknown", len(intents))

                    dry_run = DryRunEngine.run(plan)
                    record_agentic_dry_run(dry_run.overall_risk)
                    record_agentic_risk_score(route_family or "unknown", dry_run.risk_score)

                    report = ExplainabilityEngine.explain(plan, dry_run)

                    timeline = WorkflowTimeline(plan_id=plan.plan_id)
                    timeline.add_event("plan_generated", "planning", {"intent_count": len(intents)})
                    timeline.add_event("dry_run_completed", "evaluated", dry_run.to_dict())

                    if dry_run.blocked:
                        timeline.transition(WorkflowState.FAILED)
                    elif dry_run.requires_approval:
                        timeline.transition(WorkflowState.AWAITING_APPROVAL)
                    else:
                        execution = SimulationExecutor.execute(plan, timeline)
                        record_agentic_execution("simulated_success", "simulation_only")
                        for ar in execution.actions_results:
                            record_agentic_action(ar.tool, ar.status, ar.intent)
                        record_agentic_execution_duration("simulating", execution.total_duration_ms)

                        verifier = Verifier.verify(plan, dry_run, execution)
                        timeline.add_event("verifier_completed", "done", verifier.to_dict())

                    if _agentic_choices and isinstance(_agentic_choices[0].get("message"), dict):
                        _agentic_choices[0]["message"]["content"] = (
                            _agentic_choices[0]["message"].get("content", "")
                            + "\n\n" + report.to_markdown()
                        )

                    try:
                        from runtime.audit.audit_logger import audit_event
                        audit_event("agentic_pipeline_completed", {
                            "plan_id": plan.plan_id,
                            "request_id": payload.get("_request_id", ""),
                            "intent_count": len(intents),
                            "risk": dry_run.overall_risk,
                            "blocked": dry_run.blocked,
                            "simulation_only": True,
                        })
                    except ImportError:
                        pass
            except Exception as e:
                print(f"AGENTIC ERROR: {e}", flush=True)

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

            # FASE 29.4: Record circuit breaker success
            if _HAVE_SLO:
                _circuit_breakers.record_success(selected_model)

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

            # FASE 27.1-B: quality + hallucination risk scoring (lightweight heuristics)
            try:
                from runtime.telemetry.prometheus_metrics import QUALITY_SCORE, HALLUCINATION_RISK
                _choices = data.get("choices", [])
                _first = _choices[0] if _choices else {}
                _content = _first.get("message", {}).get("content", "") if isinstance(_first, dict) else ""
                _finish = _first.get("finish_reason", "stop") if isinstance(_first, dict) else "stop"
                # Quality: stop=0.9, length=0.6, error/empty=0.2
                if _finish == "stop":
                    _qs = 0.9
                elif _finish == "length":
                    _qs = 0.6
                else:
                    _qs = 0.2
                if blocked:
                    _qs = min(_qs, 0.1)
                QUALITY_SCORE.labels(route_family=route_family or "unknown").observe(float(_qs))
                # Hallucination risk: detect NO DISPONIBLE (low risk) vs repetition (high risk)
                _hr = 0.1
                if isinstance(_content, str) and _content:
                    if "NO DISPONIBLE" in _content:
                        _hr = 0.05
                    words = _content.lower().split()
                    if len(words) > 10:
                        uniq = len(set(words))
                        repeat_ratio = 1.0 - (uniq / len(words))
                        if repeat_ratio > 0.4:
                            _hr = max(_hr, min(repeat_ratio, 0.8))
                HALLUCINATION_RISK.labels(route_family=route_family or "unknown").observe(float(_hr))
            except ImportError:
                pass

        except requests.exceptions.RequestException as exc:
            latency_ms = int((time.time() - start_time) * 1000)
            if _HAVE_SLO and 'selected_model' in dir() and selected_model:
                _circuit_breakers.record_failure(selected_model)
                _slo_state.record_timeout(True)
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
            if _HAVE_SLO and 'selected_model' in dir() and selected_model:
                _circuit_breakers.record_failure(selected_model)
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


_shutting_down = False
_server_ref = None


def _handle_sigterm(signum, frame):
    global _shutting_down, _server_ref
    _shutting_down = True
    print("Received signal, shutting down gracefully...", flush=True)
    try:
        from runtime.gateway.process_guard import release_lock
        release_lock()
    except ImportError:
        pass
    try:
        from runtime.telemetry.prometheus_metrics import record_gateway_clean_shutdown
        record_gateway_clean_shutdown()
    except ImportError:
        pass
    if _server_ref:
        _server_ref.shutdown()
    sys.exit(0)


signal.signal(signal.SIGTERM, _handle_sigterm)
signal.signal(signal.SIGINT, _handle_sigterm)


def run():
    global _server_ref

    # FASE 29.0: Pre-bind cleanup — kill rogue uvicorn on port 8008
    try:
        from runtime.gateway.process_guard import prebind_cleanup
        prebind_cleanup()
    except ImportError:
        pass

    # FASE 29.0: Singleton PID lock
    try:
        from runtime.gateway.process_guard import acquire_lock
        if not acquire_lock():
            print("FATAL: Another gateway instance is already running", flush=True)
            try:
                from runtime.telemetry.prometheus_metrics import record_gateway_singleton_violation
                record_gateway_singleton_violation()
            except ImportError:
                pass
            sys.exit(1)
    except ImportError:
        pass

    # FASE 29.0: Register atexit cleanup
    try:
        from runtime.gateway.process_guard import release_lock
        atexit.register(release_lock)
    except ImportError:
        pass

    server = ThreadingHTTPServer(
        (HOST, PORT),
        GatewayHandler,
    )
    _server_ref = server

    print("AI-LAB OPENAI GATEWAY")
    print("=====================")
    print(f"Listening: http://{HOST}:{PORT}")
    backend = get_active_backend()
    print(f"Backend:   {backend['name']} @ {backend['url']}")
    print("Mode:      stream-aware sanitized + metrics")
    print()

    try:
        from runtime.telemetry.prometheus_metrics import record_gateway_boot
        record_gateway_boot()
    except ImportError:
        pass

    server.serve_forever()


if __name__ == "__main__":
    run()
