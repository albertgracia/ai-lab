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
from runtime.router.model_policy import (
    is_operational_prompt,
    is_coding_prompt,
    is_deprecated_model,
    validate_model_selection,
    PRIMARY_OPERATIONAL_MODEL,
    PRIMARY_CODING_MODEL,
    DEPRECATED_MODEL_IDS,
)
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
from runtime.gateway.tool_request_classifier import build_minimal_report_messages, build_observe_context, build_observe_context_compact, build_capability_answer, classify_chat_route, is_report_request, is_report_request_heavy, sanitize_observe_output, sanitize_payload_messages, sanitize_prompt_text, sanitize_report_output, should_use_greeting_fastpath, should_use_tool_fastpath, strip_question_tool, is_lightweight_prompt, get_qwen_escalation_reason, should_apply_evidence_guard, detect_runtime_grounded_intent, FORBIDDEN_TOOL_RECOMMENDATIONS, select_operational_response_profile, detect_operational_fastpath_intent
from runtime.context.report_runtime_context import build_report_runtime_context, format_report_runtime_context, extract_target_ip
from runtime.formatters.runtime_operational_formatter import compact_runtime_response
from runtime.context.runtime_grounding import (
    is_runtime_grounded_prompt,
    validate_response_against_observed_runtime,
    build_grounding_envelope,
)
from runtime.gateway.gateway_metrics import (
    load_metrics,
    record_request,
    record_error as record_error_legacy,
)
from runtime.errors import (
    build_error_event, emit_error, classify_exception,
    RuntimeErrorCategory, classify_timeout_stage,
)

record_error = record_error_legacy  # legacy compat for existing call sites
from runtime.telemetry.prometheus_metrics import GOVERNANCE_BLOCKED, GOVERNANCE_BLOCKED_BY_REASON, TOOL_PARALLEL_BLOCKED, prime_route_family_metrics, record_route_family_metrics
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


def _slo_is_enabled() -> bool:
    return os.environ.get("AI_LAB_ENABLE_SLO_ENFORCEMENT", "false").lower() in ("true", "1", "yes")


_DISABLED_SLO_PAYLOAD = {
    "enabled": False,
    "state": "disabled",
    "mode": "passive",
    "enforcement": False,
    "reason": "slo_enforcement_disabled",
}


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

# ── FASE 28.2: Executor Readonly Runtime ──
try:
    from runtime.agentic.readonly_executor import RealReadonlyExecutor, ENABLE_EXECUTOR as _EXECUTOR_ENABLED, DRY_RUN as _EXECUTOR_DRY_RUN
    from runtime.agentic.execution_context import RuntimeExecutionContext, ExecutionMode, DryRunReason
    _HAVE_EXECUTOR = True
except ImportError:
    _RealReadonlyExecutor = None  # type: ignore[assignment]
    _HAVE_EXECUTOR = False

# ── FASE 28.3: Sandbox Write Runtime ──
os.environ.setdefault("AI_LAB_ENABLE_SANDBOX_WRITE", "false")

try:
    from runtime.agentic.sandbox_executor import SandboxWriteExecutor, ENABLE_SANDBOX_WRITE as _SANDBOX_ENABLED, DRY_RUN as _SANDBOX_DRY_RUN
    from runtime.agentic.mutation_context import MutationExecutionContext
    _HAVE_SANDBOX_EXECUTOR = True
except ImportError:
    _SandboxWriteExecutor = None  # type: ignore[assignment]
    _HAVE_SANDBOX_EXECUTOR = False

AI_LAB_ENABLE_PLANNER = os.environ.get("AI_LAB_ENABLE_PLANNER", "false").lower() == "true"
AI_LAB_PLANNER_DRY_RUN = os.environ.get("AI_LAB_PLANNER_DRY_RUN", "true").lower() != "false"
AI_LAB_ENABLE_SANDBOX_WRITE = os.environ.get("AI_LAB_ENABLE_SANDBOX_WRITE", "false").lower() == "true"


def _has_sandbox_intents(intents: list) -> bool:
    from runtime.agentic.sandbox_registry import SANDBOX_WRITE_INTENTS
    return any(getattr(i, "intent", "") in SANDBOX_WRITE_INTENTS for i in intents)


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
    # Local tests/health checks should not trip rate limiting.
    if client_ip in {"127.0.0.1", "::1"}:
        return True
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

    payload["_user_text"] = user_text
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
            emit_error(build_error_event(
                RuntimeError("format_report_runtime_context failed"),
                category=RuntimeErrorCategory.GATEWAY_INTERNAL,
                origin_stage="reporting", component="gateway",
                source_file=__file__,
            ))

    _report_runtime = None
    _report_runtime_dict = None
    _operational_response_profile = select_operational_response_profile(user_text)
    payload["_operational_response_profile"] = _operational_response_profile
    _fastpath_intent = None
    try:
        _fastpath_intent = detect_operational_fastpath_intent(user_text)
        if _fastpath_intent:
            payload["_fastpath_intent"] = _fastpath_intent
    except Exception:
        _fastpath_intent = None
    if route.family in ("minimal", "report") and route.variant in ("report", "heavy"):
        try:
            _report_grounded_target = extract_target_ip(user_text)
            _report_runtime_dict = build_report_runtime_context(target_ip=_report_grounded_target)
            _report_runtime = format_report_runtime_context(target_ip=_report_grounded_target)
            payload["_report_grounded"] = True
            if _report_grounded_target:
                payload["_report_grounded_target"] = _report_grounded_target
            try:
                from runtime.telemetry.prometheus_metrics import (
                    REPORT_GROUNDING_TOTAL, REPORT_MISSING_FIELDS_TOTAL,
                    REPORT_TARGET_IP_TOTAL, REPORT_UNGROUNDED_TOTAL,
                    REPORT_RUNTIME_IDENTITY_MATCH,
                    REPORT_RUNTIME_IDENTITY_MISMATCH,
                )
                REPORT_GROUNDING_TOTAL.inc()
                if _report_grounded_target:
                    REPORT_TARGET_IP_TOTAL.inc()
                import json as _json
                _ctx = _json.loads(_report_runtime)
                if _ctx.get("target_runtime_match"):
                    REPORT_RUNTIME_IDENTITY_MATCH.inc()
                elif _ctx.get("target_runtime_ip"):
                    REPORT_RUNTIME_IDENTITY_MISMATCH.inc()
                _miss = _ctx.get("missing_fields", [])
                if _miss:
                    REPORT_MISSING_FIELDS_TOTAL.labels(count=str(len(_miss))).inc()
                if not _ctx.get("observed_fields"):
                    REPORT_UNGROUNDED_TOTAL.inc()
            except ImportError:
                pass
            # FASE 30G: record report classification metrics
            try:
                from runtime.telemetry.prometheus_metrics import (
                    record_report_request,
                    record_report_model_classification,
                    record_report_node_classification,
                    record_report_data_quality,
                )
                import json as _report_json
                if _report_runtime:
                    _rep_ctx = _report_json.loads(_report_runtime)
                else:
                    _rep_ctx = {}
                _report_model = payload.get("model", "unknown")
                record_report_request(_report_model, route.variant)
                _models_dict = _rep_ctx.get("models", {}) if isinstance(_rep_ctx.get("models"), dict) else {}
                for _m_status_key, _m_list in _models_dict.items():
                    if isinstance(_m_list, list):
                        for _m in _m_list:
                            _m_status = _m.get("status", "") if isinstance(_m, dict) else ""
                            if _m_status:
                                record_report_model_classification(_m_status)
                _nodes_dict = _rep_ctx.get("inference_nodes", {}) if isinstance(_rep_ctx.get("inference_nodes"), dict) else {}
                for _n_key, _n_val in _nodes_dict.items():
                    if isinstance(_n_val, dict):
                        _n_status = "active" if _n_val.get("online") else "inventory"
                        record_report_node_classification(_n_status)
                _obs = _rep_ctx.get("observed_fields", 0)
                if isinstance(_obs, list):
                    _obs = len(_obs)
                if _obs > 5:
                    record_report_data_quality("complete")
                elif _obs > 2:
                    record_report_data_quality("partial")
                else:
                    record_report_data_quality("minimal")
            except ImportError:
                pass
        except Exception:
            pass

    # Store report runtime context in payload for access outside inject_agent_context
    payload["_report_runtime_context"] = _report_runtime

    # FASE 30H.2: build real runtime context if runtime intent detected
    # replaces FASE 30H.1 synthetic minimal context with format_report_runtime_context()
    # FASE 34C: avoid heavy runtime grounding context for fast-path operational queries.
    if _report_runtime is None and detect_runtime_grounded_intent(user_text) and _fastpath_intent not in {"governance", "validation", "observability", "watchdogs", "infrastructure", "authority", "semantic"}:
        _report_runtime_dict = build_report_runtime_context()
        _report_runtime = format_report_runtime_context()
        payload["_report_runtime_context"] = _report_runtime
        payload["_report_grounded"] = True
        try:
            from runtime.telemetry.prometheus_metrics import (
                record_runtime_context_autoinjected,
            )
            record_runtime_context_autoinjected()
        except ImportError:
            pass

    if _operational_response_profile == "operational_compact" and _report_runtime_dict and detect_runtime_grounded_intent(user_text):
        _compact_answer = compact_runtime_response(user_text, _report_runtime_dict, profile=_operational_response_profile)
        if _compact_answer:
            payload["_compact_runtime_answer"] = _compact_answer
            payload["_runtime_only_reasoning"] = True

    # ── FASE 34C: Operational fast-path (authority-first, non-LLM) ──
    if _operational_response_profile == "operational_compact" and not payload.get("_compact_runtime_answer"):
        try:
            _intent = detect_operational_fastpath_intent(user_text)
            if _intent in {"governance", "validation", "observability", "watchdogs", "infrastructure", "authority"}:
                from runtime.performance import build_fast_operational_summary, compress_operational_noise, prime_async_diagnostics

                # Keep background caches warm without blocking the request.
                try:
                    prime_async_diagnostics(extra_ctx={})
                except Exception:
                    pass

                if _intent == "watchdogs":
                    try:
                        from runtime.reporting.reporting_engine import build_hardening_summary
                        _hs = build_hardening_summary(sensor_snapshot=_report_runtime_dict or {}, extra_ctx={})
                    except Exception as _exc:
                        _hs = {"contract_version": "34A", "error": str(_exc)}
                    lines = [
                        "AI-LAB Operational Fast-Path",
                        f"hardening_score={_hs.get('hardening_score', 0.0)}",
                        f"hardening_level={_hs.get('hardening_level', 'unknown')}",
                        f"escalation_state={_hs.get('escalation_state', 'unknown')}",
                        f"containment_mode={bool(_hs.get('containment_mode'))}",
                    ]
                    payload["_compact_runtime_answer"] = compress_operational_noise("\n".join(lines), level="operational")
                elif _intent == "infrastructure":
                    try:
                        from runtime.infrastructure import identify_infrastructure
                        rep = identify_infrastructure(user_text)
                        lines = [
                            "AI-LAB Operational Fast-Path",
                            f"identity={rep.get('identity') or 'NO DISPONIBLE'}",
                            f"operational_state={rep.get('operational_state', 'unknown')}",
                            f"authority_root={bool(rep.get('authority_root'))}",
                            f"expected_offline={bool(rep.get('expected_offline'))}",
                            f"roles={','.join(rep.get('roles', []) or []) or 'unknown'}",
                        ]
                        payload["_compact_runtime_answer"] = compress_operational_noise("\n".join(lines), level="operational")
                        payload["_runtime_only_reasoning"] = True
                    except Exception:
                        pass
                elif _intent == "authority":
                    try:
                        from runtime.authority import build_live_authority_snapshot
                        snap = build_live_authority_snapshot(extra_ctx={})
                        fresh = snap.get("freshness", {}) or {}
                        targets = (snap.get("prometheus", {}) or {}).get("targets", {}) or {}
                        down = targets.get("down_targets", []) or []
                        lines = [
                            "AI-LAB Operational Fast-Path",
                            f"authority_freshness={fresh.get('status', 'unknown')}",
                            f"targets_total={targets.get('active_total', 0)}",
                            f"targets_up={targets.get('scrape_up', 0)}",
                            f"targets_down={targets.get('scrape_down', 0)}",
                            f"down_examples={','.join([str(d.get('job') or '?') for d in down[:3]]) or 'none'}",
                        ]
                        payload["_compact_runtime_answer"] = compress_operational_noise("\n".join(lines), level="operational")
                        payload["_runtime_only_reasoning"] = True
                    except Exception:
                        pass
                else:
                    _fp = build_fast_operational_summary(_intent, extra_ctx={}, sensor_snapshot=_report_runtime_dict or {})
                    if _intent == "governance":
                        g = _fp.get("governance", {}) or {}
                        lines = [
                            "AI-LAB Operational Fast-Path",
                            f"governance_score={g.get('score', 'unknown')}",
                            f"governance_level={g.get('level', 'unknown')}",
                            f"degraded_domains={','.join(g.get('degraded_domains', []) or []) or 'none'}",
                        ]
                    elif _intent == "validation":
                        v = _fp.get("validation", {}) or {}
                        lines = [
                            "AI-LAB Operational Fast-Path",
                            f"validation_score={v.get('validation_score', 'unknown')}",
                            f"validation_level={v.get('validation_level', 'unknown')}",
                            f"failed_invariants={v.get('failed_invariants', 'unknown')}",
                            f"failed_gates={v.get('failed_gates', 'unknown')}",
                        ]
                    else:
                        o = _fp.get("observability_live", {}) or {}
                        lines = [
                            "AI-LAB Operational Fast-Path",
                            f"live_observability_score={o.get('live_observability_score', 0.0)}",
                            f"live_observability_level={o.get('live_observability_level', 'unknown')}",
                            f"highest_incident_severity={o.get('highest_incident_severity', 'info')}",
                            f"authority_freshness={o.get('authority_freshness', 'unknown')}",
                        ]

                    payload["_compact_runtime_answer"] = compress_operational_noise("\n".join(lines), level="operational")
                    payload["_runtime_only_reasoning"] = True
        except Exception:
            pass

    if route.family == "minimal" and route.variant == "report":
        payload.pop("tools", None)
        payload.pop("tool_choice", None)
        payload["messages"] = build_minimal_report_messages(user_text, observed_runtime=_report_runtime, response_profile=_operational_response_profile)
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
        payload["messages"] = build_minimal_report_messages(user_text, observed_runtime=_report_runtime, response_profile=_operational_response_profile)
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

    # FASE 30H.2: inject OBSERVED_RUNTIME into system_prompt for non-report routes
    # report routes use build_minimal_report_messages() which already handles this
    if payload.get("_report_grounded") and payload.get("_report_runtime_context") and system_prompt is not None and not payload.get("_observed_runtime_injected"):
        system_prompt += (
            f"\n\nOBSERVED_RUNTIME_BEGIN\n{payload['_report_runtime_context']}\nOBSERVED_RUNTIME_END"
        )
        payload["_observed_runtime_injected"] = True

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


def sanitize_completion_response(
    data: dict,
    route_family: str = "unknown",
    model: str = "unknown",
    profile: str = "unknown",
) -> dict:
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

        # FASE 29.4.4-D: normalize >1 tool_calls to single call
        final_calls = message.get("tool_calls")
        if isinstance(final_calls, list) and len(final_calls) > 1:
            TOOL_PARALLEL_BLOCKED.inc()
            emit_error(build_error_event(
                RuntimeError("parallel tool calls blocked"),
                category=RuntimeErrorCategory.TOOL_PARALLEL_UNSUPPORTED,
                origin_stage="governance", component="gateway",
            ))
            message["tool_calls"] = [final_calls[0]]

        message.pop("reasoning_content", None)

        content = message.get("content", "")

        if content:
            message["content"] = sanitize_prompt_text(sanitize_text(content))

        if current_mode() == "observe" and isinstance(message.get("content"), str):
            message["content"] = sanitize_observe_output(message.get("content"))

        # FASE 30B.1: preserve valid content even if finish_reason="length"
        finish = choice.get("finish_reason", "stop") if isinstance(choice, dict) else "stop"
        content_len = len(message.get("content") or "")

        if not message.get("content") and not tool_calls:
            if finish == "length":
                message["content"] = (
                    "La respuesta fue truncada por limite de tokens antes de generar contenido visible. "
                    "Reintenta con un limite mayor o usa un perfil de informe."
                )
                try:
                    from runtime.telemetry.prometheus_metrics import COMPLETION_EMPTY_AFTER_TRUNCATION, EMPTY_RESPONSE_PREVENTED
                    COMPLETION_EMPTY_AFTER_TRUNCATION.inc()
                    EMPTY_RESPONSE_PREVENTED.labels(reason="finish_reason_length").inc()
                except ImportError:
                    pass
            else:
                message["content"] = (
                    "Respuesta generada, pero el contenido final "
                    "llegó vacío desde el modelo."
                )

        if finish == "length" and content_len > 0:
            existing = message.get("content", "") or ""
            message["content"] = existing + "\n\n[TRUNCATED: max_tokens alcanzado]"
            try:
                from runtime.telemetry.prometheus_metrics import COMPLETION_TRUNCATED
                COMPLETION_TRUNCATED.labels(
                    model=model,
                    route_family=route_family,
                    profile=profile,
                ).inc()
            except ImportError:
                pass
            print(
                f"FASE30B.1 completion_truncated "
                f"finish_reason=length chars={content_len} "
                f"route={route_family} model={model} profile={profile}",
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

        # FASE 29.4.4-C: SLO health endpoint — always responds 200
        if self.path == "/slo/health":
            if _HAVE_SLO and _slo_is_enabled():
                self._send_json(200, _slo_manager.get_runtime_health())
            else:
                self._send_json(200, _DISABLED_SLO_PAYLOAD)
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

        if self.path == "/runtime/governance":
            try:
                from runtime.maturity.builder import build_governance_visibility
                gov = build_governance_visibility()
                data = gov.to_dict() if hasattr(gov, 'to_dict') else {"level": "unknown", "operational_state": "unavailable", "source": "fallback"}
            except Exception:
                data = {"level": "unknown", "operational_state": "unavailable", "source": "fallback", "blocked_total": 0, "blocks_by_reason": {}, "active_policies": [], "error": "governance_visibility_unavailable"}
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/runtime/routes/semantics":
            try:
                from runtime.maturity.builder import build_route_semantics_snapshot
                data = build_route_semantics_snapshot()
            except Exception:
                data = {"source": "fallback", "generated_at": time.time(), "families": {}, "error": "route_semantics_unavailable"}
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

        if self.path == "/runtime/degraded-state":
            disabled_state = None
            try:
                from runtime.slo import is_slo_enabled
                if not is_slo_enabled():
                    from runtime.slo import build_disabled_degraded_state
                    disabled_state = build_disabled_degraded_state()
            except Exception:
                pass
            if disabled_state is not None:
                self._send_json(200, disabled_state.to_dict())
                return
            try:
                from runtime.slo import DegradationManager, is_slo_enabled
                _dummy = DegradationManager()
                state = _dummy.get_degraded_state()
                self._send_json(200, state.to_dict())
            except Exception as exc:
                record_error_legacy(self.path, exc)
                self._send_json(500, {"error": "degraded_state_unavailable", "detail": str(exc)})
            return

        if self.path == "/runtime/maturity":
            try:
                from runtime.context.sensor_fusion import SensorFusionEngine
                from runtime.semantics.runtime_maturity import (
                    RuntimeMaturityEngine,
                    RUNTIME_MATURITY_CONTRACT_VERSION,
                )

                _engine = SensorFusionEngine()
                _snap = _engine.collect()
                _snap_dict = _snap.to_dict()

                _mat_engine = RuntimeMaturityEngine()
                _maturity = _mat_engine.evaluate(_snap_dict)

                try:
                    from runtime.telemetry.prometheus_metrics import (
                        record_runtime_maturity,
                    )
                    record_runtime_maturity(_maturity)
                except ImportError:
                    pass

                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/maturity",
                    "timestamp": time.time(),
                    "contract_version": RUNTIME_MATURITY_CONTRACT_VERSION,
                    "runtime_maturity": _maturity,
                    "needs_attention": _mat_engine.needs_attention(),
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/maturity",
                    "timestamp": time.time(),
                    "contract_version": "31B",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/models/state":
            try:
                from runtime.state.lmstudio_state import get_model_tracker
                tracker = get_model_tracker()
                tracker.rebuild_from_nodes()
                self._send_json(200, tracker.to_dict())
            except Exception as exc:
                record_error_legacy(self.path, exc)
                self._send_json(500, {"error": "models_state_unavailable", "detail": str(exc)})
            return

        if self.path == "/runtime/topology":
            self._send_json(
                200,
                get_topology()
            )
            return

        # FASE 31D: Runtime Topology Awareness — always-on 200
        if self.path == "/runtime/topology/dependencies":
            try:
                from runtime.topology import build_dependency_graph
                _dep = build_dependency_graph()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/topology/dependencies",
                    "timestamp": time.time(),
                    "contract_version": "31D",
                    "dependencies": _dep,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/topology/dependencies",
                    "timestamp": time.time(),
                    "contract_version": "31D",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/topology/authority":
            try:
                from runtime.topology import build_authority_graph
                _auth = build_authority_graph()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/topology/authority",
                    "timestamp": time.time(),
                    "contract_version": "31D",
                    "authority_graph": _auth,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/topology/authority",
                    "timestamp": time.time(),
                    "contract_version": "31D",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/topology/blast-radius":
            try:
                from runtime.topology import calculate_blast_radius
                _blast = calculate_blast_radius()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/topology/blast-radius",
                    "timestamp": time.time(),
                    "contract_version": "31D",
                    "blast_radius": _blast,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/topology/blast-radius",
                    "timestamp": time.time(),
                    "contract_version": "31D",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/topology/confidence":
            try:
                from runtime.topology import calculate_topology_confidence
                _conf = calculate_topology_confidence()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/topology/confidence",
                    "timestamp": time.time(),
                    "contract_version": "31D",
                    "topology_confidence": _conf,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/topology/confidence",
                    "timestamp": time.time(),
                    "contract_version": "31D",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/topology/drift":
            try:
                from runtime.topology import detect_topology_drift
                _drift = detect_topology_drift()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/topology/drift",
                    "timestamp": time.time(),
                    "contract_version": "31D",
                    "topology_drift": _drift,
                    "total_drifts": len(_drift),
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/topology/drift",
                    "timestamp": time.time(),
                    "contract_version": "31D",
                    "error": str(exc),
                })
            return

        # FASE 32A: Runtime UI Alignment — always-on 200
        if self.path == "/runtime/ui-alignment":
            try:
                from runtime.ui_alignment_validator import validate_ui_runtime_alignment
                _result = validate_ui_runtime_alignment()
                try:
                    from runtime.telemetry.prometheus_metrics import (
                        UI_ALIGNMENT_SCORE,
                        UI_HARDCODED_ENTITIES_TOTAL,
                        UI_TOPOLOGY_DRIFT_TOTAL,
                        UI_RUNTIME_MISMATCH_TOTAL,
                        UI_FAKE_INVENTORY_TOTAL,
                    )
                    _score = _result.get("alignment_score", {}).get("overall_score", 0)
                    UI_ALIGNMENT_SCORE.set(float(_score))
                    _summary = _result.get("summary", {})
                    _issues = _result.get("issues", {})
                    UI_HARDCODED_ENTITIES_TOTAL.set(float(_summary.get("total_hardcoded", 0)))
                    UI_TOPOLOGY_DRIFT_TOTAL.set(float(_summary.get("total_drift", 0)))
                    UI_RUNTIME_MISMATCH_TOTAL.set(float(_summary.get("total_mismatch", 0)))
                    UI_FAKE_INVENTORY_TOTAL.set(float(_summary.get("total_fake", 0)))
                except ImportError:
                    pass
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/ui-alignment",
                    "timestamp": time.time(),
                    "contract_version": "32A",
                    "ui_alignment": _result,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/ui-alignment",
                    "timestamp": time.time(),
                    "contract_version": "32A",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/ui-alignment/drift":
            try:
                from runtime.ui_alignment_validator import detect_ui_topology_drift
                _drift = detect_ui_topology_drift()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/ui-alignment/drift",
                    "timestamp": time.time(),
                    "contract_version": "32A",
                    "topology_drift": _drift,
                    "total_drifts": len(_drift),
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/ui-alignment/drift",
                    "timestamp": time.time(),
                    "contract_version": "32A",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/ui-alignment/score":
            try:
                from runtime.ui_alignment_validator import calculate_ui_alignment_score
                _score = calculate_ui_alignment_score()
                try:
                    from runtime.telemetry.prometheus_metrics import UI_ALIGNMENT_SCORE
                    UI_ALIGNMENT_SCORE.set(float(_score.get("overall_score", 0)))
                except ImportError:
                    pass
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/ui-alignment/score",
                    "timestamp": time.time(),
                    "contract_version": "32A",
                    "alignment_score": _score,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/ui-alignment/score",
                    "timestamp": time.time(),
                    "contract_version": "32A",
                    "error": str(exc),
                })
            return

        # FASE 30I: Runtime Sensor Fusion — always-on 200
        if self.path == "/runtime/sensors":
            try:
                from runtime.context.sensor_fusion import SensorFusionEngine
                _engine = SensorFusionEngine()
                _snap = _engine.collect()
                _snap_dict = _snap.to_dict()
                _sensor_contract = _engine.build_sensor_contract(_snap)
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/sensors",
                    "timestamp": time.time(),
                    "sensor_contract_version": _sensor_contract["sensor_contract_version"],
                    "topology_mode": _sensor_contract["topology_mode"],
                    "topology": _snap.topology.to_dict(),
                    "observed_sources": _snap.observed_sources,
                    "missing_sources": _snap.missing_sources,
                    "expected_offline": _sensor_contract["expected_offline_targets"],
                    "unexpected_down": _sensor_contract["unexpected_down_targets"],
                    "expected_offline_targets": _sensor_contract["expected_offline_targets"],
                    "unexpected_down_targets": _sensor_contract["unexpected_down_targets"],
                    "domain_confidence": _sensor_contract["domain_confidence"],
                    "gpu_operational_summaries": _sensor_contract["gpu_operational_summaries"],
                    "gpu_summary": _sensor_contract["gpu_summary"],
                    "source_quality": _sensor_contract["source_quality"],
                    "derived_state": {k: v for k, v in _snap.derived_state.items() if k in ("gpu_nodes", "gateway", "control_plane")},
                    "freshness": {k: f"{v:.1f}s ago" for k, v in _snap.last_scrape_seconds_ago.items() if v is not None},
                    "sensor_snapshot": _snap_dict,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/sensors",
                    "error": str(exc),
                    "timestamp": time.time(),
                })
            return

        # FASE 30I-F: Runtime Cognitive Summary — always-on 200
        if self.path == "/runtime/cognitive-summary":
            try:
                from runtime.context.sensor_fusion import SensorFusionEngine
                from runtime.context.cognitive_compression import (
                    build_runtime_cognitive_summary,
                    COGNITIVE_CONTRACT_VERSION,
                )
                _engine = SensorFusionEngine()
                _snap = _engine.collect()
                _snap_dict = _snap.to_dict()
                _cognitive = build_runtime_cognitive_summary(_snap_dict)
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/cognitive-summary",
                    "timestamp": time.time(),
                    "cognitive_summary": _cognitive,
                    "source_snapshot_time": _snap.timestamp,
                    "confidence": _cognitive.get("confidence", "low"),
                    "unavailable_data": _cognitive.get("unavailable_data", []),
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/cognitive-summary",
                    "timestamp": time.time(),
                    "cognitive_summary": {
                        "contract_version": "30I-F",
                        "overall_state": "unknown",
                        "topology_mode": "unknown",
                        "summary": "NO DISPONIBLE",
                        "important_signals": [],
                        "risks": ["cognitive compression unavailable"],
                        "recommended_actions": ["verificar sensor fusion"],
                        "unavailable_data": ["cognitive_summary"],
                        "confidence": "low",
                        "freshness": "unavailable",
                    },
                    "confidence": "low",
                    "error": str(exc),
                })
            return

        # FASE 31E: Entity State Taxonomy — always-on 200
        if self.path == "/runtime/entities":
            try:
                from runtime.entities import (
                    build_entity_registry as _31e_build,
                    build_active_entities,
                    build_inventory_entities,
                    build_discoverable_entities,
                    build_deprecated_entities,
                    build_routability_summary,
                    build_topology_preparation,
                )
                _31e_entities = _31e_build()
                _active = build_active_entities()
                _inventory = build_inventory_entities()
                _discoverable = build_discoverable_entities()
                _deprecated = build_deprecated_entities()
                _routability = build_routability_summary()
                _topology = build_topology_preparation()
                try:
                    from runtime.telemetry.prometheus_metrics import record_entity_registry_metrics
                    record_entity_registry_metrics(_31e_entities)
                except ImportError:
                    pass
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/entities",
                    "timestamp": time.time(),
                    "contract_version": "31E",
                    "total_entities": len(_31e_entities),
                    "total_active": len(_active),
                    "total_inventory": len(_inventory),
                    "total_discoverable": len(_discoverable),
                    "total_deprecated": len(_deprecated),
                    "active": _active,
                    "inventory": _inventory,
                    "discoverable": _discoverable,
                    "deprecated": _deprecated,
                    "routability": _routability,
                    "topology": _topology,
                    "entities": _31e_entities,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/entities",
                    "timestamp": time.time(),
                    "contract_version": "31E",
                    "error": str(exc),
                })
            return

        # FASE 30I-G + 31E: Runtime Grounding — always-on 200
        if self.path == "/runtime/grounding":
            try:
                from runtime.context.runtime_entity_registry import (
                    RuntimeEntityRegistry,
                    OBSERVED_ENTITY_TYPES,
                )
                from runtime.context.runtime_grounding import (
                    build_grounding_envelope,
                )
                _reg = RuntimeEntityRegistry()
                _envelope = build_grounding_envelope("", entity_registry=_reg)

                # FASE 31E: enrich with entity state taxonomy counts
                try:
                    from runtime.entities import build_entity_registry as _31e_build
                    _31e_entities = _31e_build()
                    _31e_active = sum(1 for e in _31e_entities if e.get("operational_state") == "active")
                    _31e_inventory = sum(1 for e in _31e_entities if e.get("inventory_state") in ("inventory", "expected_offline") and e.get("operational_state") != "active")
                    _31e_deprecated = sum(1 for e in _31e_entities if e.get("deprecated"))
                    _31e_discoverable = sum(1 for e in _31e_entities if e.get("discoverability") == "discoverable" and e.get("operational_state") != "active")
                    _31e_routable = sum(1 for e in _31e_entities if e.get("routable"))
                    _31e_summary = {
                        "total_entities": len(_31e_entities),
                        "active": _31e_active,
                        "inventory": _31e_inventory,
                        "deprecated": _31e_deprecated,
                        "discoverable": _31e_discoverable,
                        "routable": _31e_routable,
                    }
                except Exception:
                    _31e_summary = {}

                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/grounding",
                    "timestamp": time.time(),
                    "contract_version": "31E",
                    "observed_entity_types": sorted(OBSERVED_ENTITY_TYPES),
                    "grounding_enabled": True,
                    "grounding_envelope": _envelope,
                    "denylist_active": True,
                    "entity_registry_active": True,
                    "entity_taxonomy_31e": _31e_summary,
                    "unknown_state_semantics": sorted(UNKNOWN_STATE_TOKENS),
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/grounding",
                    "timestamp": time.time(),
                    "contract_version": "30I-G",
                    "error": str(exc),
                })
            return

        # ── FASE OBS-31A: Observability Source-of-Truth Audit endpoints ──
        if self.path == "/runtime/observability/audit":
            try:
                from runtime.observability import (
                    build_prometheus_audit_summary,
                )
                from runtime.observability.dashboard_validator import DashboardValidator
                from runtime.observability.drift_detector import DriftDetector
                from runtime.observability.loki_audit import build_loki_audit_summary
                from runtime.observability.metric_inventory import build_observability_health_score

                _targets = build_prometheus_audit_summary()
                _dashboards = DashboardValidator().build_dashboard_audit_summary()
                _drift = DriftDetector().detect_all()
                _loki = build_loki_audit_summary()
                _score = build_observability_health_score(
                    targets_healthy=_targets.get("classification", {}).get("healthy", 0),
                    targets_total=_targets.get("total_targets", 0),
                    dashboards_healthy=_dashboards.get("critical_dashboards_healthy", 0),
                    dashboards_total=_dashboards.get("total_dashboards", 0),
                    no_data_panels=_dashboards.get("total_no_data_panels", 0),
                    stale_metrics=0,
                    query_failures=0,
                    runtime_alignment_score=_targets.get("critical_targets", {}).get("alignment_pct", 0) / 100.0,
                )
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/audit",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A",
                    "prometheus_audit": _targets,
                    "dashboard_audit": _dashboards,
                    "loki_audit": _loki,
                    "drift_detection": _drift.to_dict(),
                    "observability_health_score": _score,
                })
                try:
                    from runtime.telemetry.prometheus_metrics import (
                        record_observability_audit,
                        record_observability_alignment_score,
                    )
                    record_observability_audit("full_audit", "ok")
                    record_observability_alignment_score(_score.get("score", 0))
                except ImportError:
                    pass
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/audit",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/observability/targets":
            try:
                from runtime.observability.prometheus_audit import run_prometheus_authority_audit
                _data = run_prometheus_authority_audit()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/targets",
                    "timestamp": time.time(),
                    "contract_version": _data.get("contract_version", "OBS-31A.1"),
                    "prometheus_audit": _data,
                })
                try:
                    from runtime.telemetry.prometheus_metrics import record_observability_audit
                    record_observability_audit("targets", "ok")
                except ImportError:
                    pass
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/targets",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/observability/dashboards":
            try:
                from runtime.observability.dashboard_validator import DashboardValidator
                _data = DashboardValidator().build_dashboard_audit_summary()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/dashboards",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A",
                    "dashboard_audit": _data,
                })
                try:
                    from runtime.telemetry.prometheus_metrics import record_observability_audit
                    record_observability_audit("dashboards", "ok")
                except ImportError:
                    pass
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/dashboards",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/observability/metrics":
            try:
                from runtime.observability.metric_inventory import build_metric_inventory
                _metrics = build_metric_inventory()
                _critical = sum(1 for m in _metrics if m.get("criticality") == "critical")
                _high = sum(1 for m in _metrics if m.get("criticality") == "high")
                _total = len(_metrics)
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/metrics",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A",
                    "total_metrics": _total,
                    "classification": {
                        "critical": _critical,
                        "high": _high,
                        "medium": sum(1 for m in _metrics if m.get("criticality") == "medium"),
                        "low": sum(1 for m in _metrics if m.get("criticality") == "low"),
                        "info": sum(1 for m in _metrics if m.get("criticality") == "info"),
                    },
                    "metrics": _metrics,
                })
                try:
                    from runtime.telemetry.prometheus_metrics import record_observability_audit
                    record_observability_audit("metrics", "ok")
                except ImportError:
                    pass
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/metrics",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A",
                    "total_metrics": 0,
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/observability/drift":
            try:
                from runtime.observability.drift_detector import DriftDetector
                _drift = DriftDetector().detect_all()
                _total = len(_drift.gpu_drift) + len(_drift.topology_drift) \
                    + len(_drift.service_drift) + len(_drift.model_drift) + len(_drift.semantic_drift)
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/drift",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A",
                    "total_drifts": _total,
                    "drift": _drift.to_dict(),
                })
                if _total > 0:
                    try:
                        from runtime.telemetry.prometheus_metrics import (
                            record_observability_runtime_drift,
                        )
                        for _d in _drift.gpu_drift:
                            record_observability_runtime_drift("gpu", _d.get("severity", "low"))
                    except ImportError:
                        pass
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/drift",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/observability/datasources":
            try:
                from runtime.observability.contracts import build_datasource_contract
                from runtime.observability.grafana_inventory import _KNOWN_DATASOURCES
                _results = []
                for ds in _KNOWN_DATASOURCES:
                    _contract = build_datasource_contract(
                        name=ds["name"], uid=ds["uid"], type=ds["type"],
                        url=ds["url"], accessible=ds.get("accessible", True),
                        default=ds.get("default", False),
                    )
                    _results.append(_contract)
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/datasources",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A.2",
                    "total_datasources": len(_results),
                    "datasources": _results,
                })
                try:
                    from runtime.telemetry.prometheus_metrics import record_observability_audit
                    record_observability_audit("datasources", "ok")
                except ImportError:
                    pass
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/datasources",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A.2",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/observability/runtime-alignment":
            try:
                from runtime.observability.drift_detector import DriftDetector, build_runtime_alignment_summary
                from runtime.observability.dashboard_validator import DashboardValidator
                _drift = DriftDetector().detect_all()
                _dashboards = DashboardValidator().validate_all_known()
                _alignment = build_runtime_alignment_summary(_drift, _dashboards)
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/runtime-alignment",
                    "timestamp": time.time(),
                    "contract_version": _alignment.get("contract_version", "OBS-31A.2"),
                    "runtime_alignment": _alignment,
                })
                try:
                    from runtime.telemetry.prometheus_metrics import (
                        record_observability_alignment_score,
                        record_observability_audit,
                    )
                    record_observability_alignment_score(_alignment.get("alignment_score", 0))
                    record_observability_audit("runtime_alignment", "ok")
                except ImportError:
                    pass
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/runtime-alignment",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A.2",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/observability/drift-audit":
            try:
                from runtime.observability.dashboard_validator import DashboardValidator
                _audit = DashboardValidator().run_grafana_drift_audit()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/drift-audit",
                    "timestamp": time.time(),
                    "contract_version": _audit.get("contract_version", "OBS-31A.2"),
                    "drift_audit": _audit,
                })
                try:
                    from runtime.telemetry.prometheus_metrics import record_observability_audit
                    record_observability_audit("drift_audit", "ok")
                except ImportError:
                    pass
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/drift-audit",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A.2",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/observability/cross-validate":
            try:
                from runtime.observability.runtime_alignment import (
                    RuntimeAlignmentValidator,
                )
                from runtime.observability.prometheus_audit import (
                    run_prometheus_authority_audit,
                )
                from runtime.observability.dashboard_validator import DashboardValidator
                from runtime.observability.drift_detector import (
                    DRIFT_DETECTOR_CONTRACT_VERSION,
                )
                from runtime.observability.grafana_inventory import (
                    GRAFANA_INVENTORY_CONTRACT_VERSION,
                )
                from runtime.context.sensor_fusion import build_sensor_fusion_snapshot

                _validator = RuntimeAlignmentValidator()
                _sensor = build_sensor_fusion_snapshot() or {}
                _targets = run_prometheus_authority_audit() or {}
                _dashboards = DashboardValidator().validate_all_known() or []

                _lmstudio = _sensor.get("lmstudio", {}).get("statuses", {})
                _rt_models = _sensor.get("runtime_models", {})

                _contracts = {
                    "sensor": _sensor.get("sensor_contract_version", "30I-D"),
                    "cognitive": _sensor.get("cognitive_contract_version", "30I-F"),
                    "grounding": _sensor.get("grounding_contract_version", "30I-G"),
                    "observability": _sensor.get("observability_audit", {}).get("contract_version", "OBS-31A"),
                    "prometheus_audit": _targets.get("contract_version", "OBS-31A.1"),
                    "drift_detector": DRIFT_DETECTOR_CONTRACT_VERSION,
                    "grafana_inventory": GRAFANA_INVENTORY_CONTRACT_VERSION,
                    "runtime_alignment": "OBS-31A.3",
                }
                _result = _validator.validate_all(
                    sensor_snapshot=_sensor,
                    runtime_summary=_sensor,
                    prometheus_targets=_targets,
                    grafana_dashboards=_dashboards,
                    lmstudio_state=_lmstudio,
                    runtime_models=_rt_models,
                    contracts=_contracts,
                )
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/cross-validate",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A.3",
                    "runtime_alignment": _result.to_dict(),
                })
                try:
                    from runtime.telemetry.prometheus_metrics import (
                        record_observability_alignment_score,
                        record_observability_audit,
                    )
                    record_observability_alignment_score(_result.alignment_score)
                    record_observability_audit("cross_validate", "ok")
                except ImportError:
                    pass
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/cross-validate",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A.3",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/observability/remediation-plan":
            try:
                from runtime.observability.remediation_planner import RemediationPlanner
                from runtime.observability.dashboard_validator import DashboardValidator
                from runtime.observability.prometheus_audit import run_prometheus_authority_audit

                _drift = None
                _inventory = DashboardValidator().validate_all_known()
                _audit = DashboardValidator().build_dashboard_audit_summary()
                _targets = run_prometheus_authority_audit()
                _alignment = None

                _plan = RemediationPlanner().build_remediation_plan(
                    drift_result=_drift,
                    dashboard_inventory=_inventory,
                    dashboard_audit=_audit,
                    prometheus_targets=_targets,
                    runtime_alignment=_alignment,
                    grafana_dashboards=_inventory,
                )
                _plan_dict = _plan.to_dict()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/remediation-plan",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A.4",
                    "remediation_plan": _plan_dict,
                })
                try:
                    from runtime.telemetry.prometheus_metrics import (
                        record_observability_remediation,
                        record_observability_audit,
                    )
                    record_observability_audit("remediation_plan", "ok")
                    for _item in _plan.items:
                        record_observability_remediation(_item.domain, _item.severity)
                except ImportError:
                    pass
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/remediation-plan",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A.4",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/observability/remediation-summary":
            try:
                from runtime.observability.remediation_planner import RemediationPlanner
                from runtime.observability.dashboard_validator import DashboardValidator
                from runtime.observability.prometheus_audit import run_prometheus_authority_audit

                _inventory = DashboardValidator().validate_all_known()
                _audit = DashboardValidator().build_dashboard_audit_summary()
                _targets = run_prometheus_authority_audit()

                _planner = RemediationPlanner()
                _plan = _planner.build_remediation_plan(
                    dashboard_inventory=_inventory,
                    dashboard_audit=_audit,
                    prometheus_targets=_targets,
                    grafana_dashboards=_inventory,
                )
                _summary = _planner.generate_remediation_summary(_plan)
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/remediation-summary",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A.4",
                    "remediation_summary": _summary.to_dict(),
                })
                try:
                    from runtime.telemetry.prometheus_metrics import (
                        record_observability_remediation_score,
                        record_observability_audit,
                    )
                    record_observability_remediation_score(_summary.remediation_score)
                    record_observability_audit("remediation_summary", "ok")
                except ImportError:
                    pass
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/remediation-summary",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A.4",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/observability/technical-debt":
            try:
                from runtime.observability.remediation_planner import RemediationPlanner
                from runtime.observability.dashboard_validator import DashboardValidator
                from runtime.observability.prometheus_audit import run_prometheus_authority_audit

                _inventory = DashboardValidator().validate_all_known()
                _audit = DashboardValidator().build_dashboard_audit_summary()
                _targets = run_prometheus_authority_audit()

                _planner = RemediationPlanner()
                _plan = _planner.build_remediation_plan(
                    dashboard_inventory=_inventory,
                    dashboard_audit=_audit,
                    prometheus_targets=_targets,
                    grafana_dashboards=_inventory,
                )
                _debt = _planner.get_technical_debt_report(_plan)
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/technical-debt",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A.4",
                    "technical_debt": _debt,
                })
                try:
                    from runtime.telemetry.prometheus_metrics import (
                        record_observability_technical_debt,
                        record_observability_audit,
                    )
                    record_observability_audit("technical_debt", "ok")
                    for _domain, _count in _debt.get('by_domain', {}).items():
                        for _ in range(_count):
                            record_observability_technical_debt(_domain)
                except ImportError:
                    pass
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/technical-debt",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A.4",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/observability/execute-quick-wins":
            try:
                from runtime.observability.remediation_planner import (
                    build_remediation_plan,
                )
                from runtime.observability.remediation_executor import (
                    RemediationExecutor,
                    EXECUTOR_CONTRACT_VERSION,
                )
                from runtime.observability.dashboard_validator import DashboardValidator
                from runtime.observability.prometheus_audit import (
                    run_prometheus_authority_audit,
                )

                _inventory = DashboardValidator().validate_all_known() or []
                _audit = DashboardValidator().build_dashboard_audit_summary()
                _targets = run_prometheus_authority_audit() or {}

                _plan = build_remediation_plan(
                    dashboard_inventory=_inventory,
                    dashboard_audit=_audit,
                    prometheus_targets=_targets,
                    grafana_dashboards=_inventory,
                )
                _items = _plan.get("items", [])
                _executor = RemediationExecutor()
                _results = _executor.execute_quick_wins(_items)
                _summary = _executor.get_execution_summary()

                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/execute-quick-wins",
                    "timestamp": time.time(),
                    "contract_version": EXECUTOR_CONTRACT_VERSION,
                    "execution_results": _results,
                    "execution_summary": _summary,
                    "plan_timestamp": _plan.get("timestamp", 0),
                })
                try:
                    from runtime.telemetry.prometheus_metrics import (
                        record_observability_execution,
                        record_observability_execution_auto,
                        record_observability_execution_manual,
                        record_observability_execution_time,
                    )
                    for _r in _results:
                        _domain = _r.get("domain", "unknown")
                        _status = "executed" if _r.get("executed") else "manual"
                        record_observability_execution(_domain, _status)
                        if _r.get("auto_fix_applied"):
                            record_observability_execution_auto(_domain)
                        else:
                            record_observability_execution_manual(_domain)
                    record_observability_execution_time()
                except ImportError:
                    pass
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/execute-quick-wins",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A.5",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/observability/execution-status":
            try:
                from runtime.observability.remediation_executor import (
                    RemediationExecutor,
                    EXECUTOR_CONTRACT_VERSION,
                )
                _summary = RemediationExecutor().get_execution_summary()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/execution-status",
                    "timestamp": time.time(),
                    "contract_version": EXECUTOR_CONTRACT_VERSION,
                    "execution_status": _summary,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/execution-status",
                    "timestamp": time.time(),
                    "contract_version": "OBS-31A.5",
                    "error": str(exc),
                })
            return

        # FASE 32B: Grafana Semantic Cleanup — always-on 200
        if self.path == "/runtime/observability/grafana/semantic-audit":
            try:
                from runtime.observability.grafana_semantic_validator import build_grafana_semantic_summary
                _result = build_grafana_semantic_summary()
                try:
                    from runtime.telemetry.prometheus_metrics import (
                        GRAFANA_ALIGNMENT_SCORE,
                        GRAFANA_FAKE_PANELS_TOTAL,
                        GRAFANA_STALE_PANELS_TOTAL,
                        GRAFANA_ORPHAN_DATASOURCES_TOTAL,
                        GRAFANA_METRIC_DRIFT_TOTAL,
                        GRAFANA_RUNTIME_ALIGNED_DASHBOARDS_TOTAL,
                    )
                    _score = _result.get("grafana_alignment_score", {}).get("overall_score", 0)
                    GRAFANA_ALIGNMENT_SCORE.set(float(_score))
                    _issues = _result.get("issues", {})
                    GRAFANA_FAKE_PANELS_TOTAL.set(float(len(_issues.get("fake_gpu_panels", []))))
                    GRAFANA_STALE_PANELS_TOTAL.set(float(len(_issues.get("stale_panels", []))))
                    GRAFANA_ORPHAN_DATASOURCES_TOTAL.set(float(len(_issues.get("orphan_datasources", []))))
                    GRAFANA_METRIC_DRIFT_TOTAL.set(float(len(_issues.get("metric_drift", []))))
                    GRAFANA_RUNTIME_ALIGNED_DASHBOARDS_TOTAL.set(float(_result.get("inventory", {}).get("runtime_aligned", 0)))
                except ImportError:
                    pass
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/grafana/semantic-audit",
                    "timestamp": time.time(),
                    "contract_version": "32B",
                    "grafana_semantic": _result,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/grafana/semantic-audit",
                    "timestamp": time.time(),
                    "contract_version": "32B",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/observability/grafana/alignment-score":
            try:
                from runtime.observability.grafana_semantic_validator import build_grafana_semantic_summary, calculate_grafana_alignment_score
                _result = build_grafana_semantic_summary()
                _score = calculate_grafana_alignment_score(
                    total_dashboards=_result.get("inventory", {}).get("total_inventory", 1),
                    fake_panels=_result.get("summary", {}).get("total_fake_gpu_panels", 0),
                    stale_panels=_result.get("summary", {}).get("total_stale_panels", 0),
                    orphan_datasources=_result.get("summary", {}).get("total_orphan_datasources", 0),
                    metric_drifts=_result.get("summary", {}).get("total_metric_drifts", 0),
                    topology_issues=_result.get("summary", {}).get("total_topology_issues", 0),
                    runtime_aligned_count=_result.get("inventory", {}).get("runtime_aligned", 0),
                )
                try:
                    from runtime.telemetry.prometheus_metrics import GRAFANA_ALIGNMENT_SCORE
                    GRAFANA_ALIGNMENT_SCORE.set(float(_score.get("overall_score", 0)))
                except ImportError:
                    pass
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/grafana/alignment-score",
                    "timestamp": time.time(),
                    "contract_version": "32B",
                    "grafana_alignment_score": _score,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/grafana/alignment-score",
                    "timestamp": time.time(),
                    "contract_version": "32B",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/observability/grafana/dashboard-inventory":
            try:
                from runtime.observability.grafana_semantic_validator import build_dashboard_inventory_32b
                _inventory = build_dashboard_inventory_32b()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/grafana/dashboard-inventory",
                    "timestamp": time.time(),
                    "contract_version": "32B",
                    "total_dashboards": len(_inventory),
                    "dashboards": _inventory,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/grafana/dashboard-inventory",
                    "timestamp": time.time(),
                    "contract_version": "32B",
                    "error": str(exc),
                })
            return

        # ── FASE OBS-34B: Live observability diagnostics — always-on 200 ──
        if self.path == "/runtime/observability/live":
            try:
                from runtime.observability import run_live_observability_diagnostics, OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION
                from runtime.telemetry.prometheus_metrics import record_live_observability_diagnostics
                _diag = run_live_observability_diagnostics(extra_ctx={})
                record_live_observability_diagnostics(_diag)
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/live",
                    "timestamp": time.time(),
                    "contract_version": OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION,
                    "live": _diag,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/live",
                    "timestamp": time.time(),
                    "contract_version": "OBS-34B",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/observability/live/prometheus":
            try:
                from runtime.observability import diagnose_prometheus_authority, OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION
                _p = diagnose_prometheus_authority(extra_ctx={})
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/live/prometheus",
                    "timestamp": time.time(),
                    "contract_version": OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION,
                    "prometheus": _p,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/live/prometheus",
                    "timestamp": time.time(),
                    "contract_version": "OBS-34B",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/observability/live/grafana":
            try:
                from runtime.observability import diagnose_grafana_platform, OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION
                _g = diagnose_grafana_platform(extra_ctx={})
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/live/grafana",
                    "timestamp": time.time(),
                    "contract_version": OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION,
                    "grafana": _g,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/live/grafana",
                    "timestamp": time.time(),
                    "contract_version": "OBS-34B",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/observability/live/loki":
            try:
                from runtime.observability import diagnose_loki_platform, OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION
                _l = diagnose_loki_platform(extra_ctx={})
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/live/loki",
                    "timestamp": time.time(),
                    "contract_version": OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION,
                    "loki": _l,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/live/loki",
                    "timestamp": time.time(),
                    "contract_version": "OBS-34B",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/observability/live/exporters":
            try:
                from runtime.observability import run_live_observability_diagnostics, OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION
                _diag = run_live_observability_diagnostics(extra_ctx={})
                _e = _diag.get("exporters", {})
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/live/exporters",
                    "timestamp": time.time(),
                    "contract_version": OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION,
                    "exporters": _e,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/live/exporters",
                    "timestamp": time.time(),
                    "contract_version": "OBS-34B",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/observability/live/incidents":
            try:
                from runtime.observability import run_live_observability_diagnostics, OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION
                _diag = run_live_observability_diagnostics(extra_ctx={})
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/live/incidents",
                    "timestamp": time.time(),
                    "contract_version": OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION,
                    "incidents": _diag.get("incidents", {}),
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/live/incidents",
                    "timestamp": time.time(),
                    "contract_version": "OBS-34B",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/observability/live/score":
            try:
                from runtime.observability import run_live_observability_diagnostics, OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION
                _diag = run_live_observability_diagnostics(extra_ctx={})
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/live/score",
                    "timestamp": time.time(),
                    "contract_version": OBS_LIVE_DIAGNOSTICS_CONTRACT_VERSION,
                    "score": _diag.get("score", {}),
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/observability/live/score",
                    "timestamp": time.time(),
                    "contract_version": "OBS-34B",
                    "error": str(exc),
                })
            return

        # ── FASE 34C: Runtime performance & governance latency calibration ──
        if self.path == "/runtime/performance" or self.path.startswith("/runtime/performance/"):
            try:
                from runtime.performance import (
                    profile_runtime_latency,
                    profile_governance_latency,
                    profile_validation_latency,
                    get_performance_cache_state,
                    calculate_runtime_performance_score,
                    build_latency_breakdown,
                    prime_async_diagnostics,
                )
                prime_async_diagnostics(extra_ctx={})

                if self.path == "/runtime/performance" or self.path == "/runtime/performance/score":
                    rep = profile_runtime_latency(extra_ctx={}, sensor_snapshot={})
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": self.path.lstrip("/"),
                        "timestamp": time.time(),
                        "contract_version": "34C",
                        "performance": rep.get("performance", {}),
                        "latency": rep.get("latency", {}),
                        "cache": get_performance_cache_state(),
                    })
                    return

                if self.path == "/runtime/performance/latency":
                    rep = profile_runtime_latency(extra_ctx={}, sensor_snapshot={})
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/performance/latency",
                        "timestamp": time.time(),
                        "contract_version": "34C",
                        "latency": rep,
                    })
                    return

                if self.path == "/runtime/performance/governance":
                    g = profile_governance_latency(extra_ctx={}, sensor_snapshot={})
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/performance/governance",
                        "timestamp": time.time(),
                        "contract_version": "34C",
                        "governance": g,
                    })
                    return

                if self.path == "/runtime/performance/validation":
                    v = profile_validation_latency(extra_ctx={}, sensor_snapshot={})
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/performance/validation",
                        "timestamp": time.time(),
                        "contract_version": "34C",
                        "validation": v,
                    })
                    return

                if self.path == "/runtime/performance/cache":
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/performance/cache",
                        "timestamp": time.time(),
                        "contract_version": "34C",
                        "cache": get_performance_cache_state(),
                    })
                    return

                if self.path == "/runtime/performance/noise":
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/performance/noise",
                        "timestamp": time.time(),
                        "contract_version": "34C",
                        "verbosity_levels": ["minimal", "operational", "technical", "deep"],
                        "default_level": "operational",
                    })
                    return

                if self.path == "/runtime/performance/fastpath":
                    # This endpoint is informational; fast-path execution happens in /v1/chat/completions.
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/performance/fastpath",
                        "timestamp": time.time(),
                        "contract_version": "34C",
                        "fastpath": {
                            "enabled": True,
                            "authority_first": True,
                            "intents": ["runtime", "gpu", "observability", "governance", "validation", "watchdogs"],
                            "model": "llama-3.1-8b-instruct",
                        },
                    })
                    return

                # Unknown /runtime/performance/* -> always-on 200.
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": self.path.lstrip("/"),
                    "timestamp": time.time(),
                    "contract_version": "34C",
                    "error": "unknown_performance_endpoint",
                })
                return

            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": self.path.lstrip("/"),
                    "timestamp": time.time(),
                    "contract_version": "34C",
                    "error": str(exc),
                })
                return

        # ── FASE 35A: Infrastructure Identity Registry — always-on 200 ──
        if self.path == "/runtime/infrastructure" or self.path.startswith("/runtime/infrastructure/"):
            try:
                from runtime.infrastructure import (
                    build_infrastructure_identity_registry,
                    build_authority_root_map,
                    build_operational_node_map,
                    build_infrastructure_semantic_summary,
                    calculate_infrastructure_identity_score,
                )
                from runtime.telemetry.prometheus_metrics import record_infrastructure_metrics

                reg = build_infrastructure_identity_registry(extra_ctx={})
                try:
                    record_infrastructure_metrics(reg)
                except Exception:
                    pass

                if self.path == "/runtime/infrastructure" or self.path == "/runtime/infrastructure/score":
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": self.path.lstrip("/"),
                        "timestamp": time.time(),
                        "contract_version": "35A",
                        "infrastructure": reg,
                        "score": calculate_infrastructure_identity_score(reg),
                    })
                    return

                if self.path == "/runtime/infrastructure/authority":
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/infrastructure/authority",
                        "timestamp": time.time(),
                        "contract_version": "35A",
                        "authority": build_authority_root_map(),
                    })
                    return

                if self.path == "/runtime/infrastructure/nodes":
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/infrastructure/nodes",
                        "timestamp": time.time(),
                        "contract_version": "35A",
                        "nodes": build_operational_node_map(),
                    })
                    return

                if self.path == "/runtime/infrastructure/control-plane":
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/infrastructure/control-plane",
                        "timestamp": time.time(),
                        "contract_version": "35A",
                        "control_plane": reg.get("control_plane", []),
                    })
                    return

                if self.path == "/runtime/infrastructure/operational":
                    inv = reg.get("inventory", {}) or {}
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/infrastructure/operational",
                        "timestamp": time.time(),
                        "contract_version": "35A",
                        "operational_nodes": inv.get("operational_nodes", []),
                    })
                    return

                if self.path == "/runtime/infrastructure/inventory":
                    inv = reg.get("inventory", {}) or {}
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/infrastructure/inventory",
                        "timestamp": time.time(),
                        "contract_version": "35A",
                        "inventory_only_nodes": inv.get("inventory_only_nodes", []),
                    })
                    return

                if self.path == "/runtime/infrastructure/discoverable":
                    inv = reg.get("inventory", {}) or {}
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/infrastructure/discoverable",
                        "timestamp": time.time(),
                        "contract_version": "35A",
                        "discoverable_nodes": inv.get("discoverable_nodes", []),
                    })
                    return

                if self.path.startswith("/runtime/infrastructure/semantic-summary"):
                    # Optional query: ?id=192.168.1.40
                    target = None
                    try:
                        from urllib.parse import urlparse, parse_qs
                        q = parse_qs(urlparse(self.path).query)
                        target = (q.get("id") or [None])[0]
                    except Exception:
                        target = None
                    if not target:
                        target = "192.168.1.40"
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/infrastructure/semantic-summary",
                        "timestamp": time.time(),
                        "contract_version": "35A",
                        "summary": build_infrastructure_semantic_summary(str(target)),
                    })
                    return

                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": self.path.lstrip("/"),
                    "timestamp": time.time(),
                    "contract_version": "35A",
                    "error": "unknown_infrastructure_endpoint",
                })
                return

            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": self.path.lstrip("/"),
                    "timestamp": time.time(),
                    "contract_version": "35A",
                    "error": str(exc),
                })
                return

        # ── FASE 35B: Semantic sterilization & identity hygiene — always-on 200 ──
        if self.path == "/runtime/semantic" or self.path.startswith("/runtime/semantic/"):
            try:
                from runtime.semantic import (
                    build_operational_truth,
                    sterilize_semantic_entities,
                    build_identity_hygiene_summary,
                    build_semantic_integrity_report,
                )
                from runtime.telemetry.prometheus_metrics import record_semantic_metrics

                sem = build_semantic_integrity_report(extra_ctx={})
                try:
                    record_semantic_metrics(sem)
                except Exception:
                    pass

                if self.path == "/runtime/semantic" or self.path == "/runtime/semantic/score":
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": self.path.lstrip("/"),
                        "timestamp": time.time(),
                        "contract_version": "35B",
                        "semantic": sem,
                    })
                    return

                if self.path == "/runtime/semantic/truth":
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/semantic/truth",
                        "timestamp": time.time(),
                        "contract_version": "35B",
                        "truth": build_operational_truth(extra_ctx={}),
                    })
                    return

                if self.path == "/runtime/semantic/phantom":
                    ster = sterilize_semantic_entities(extra_ctx={})
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/semantic/phantom",
                        "timestamp": time.time(),
                        "contract_version": "35B",
                        "phantom": ster.get("phantom_entities", []),
                    })
                    return

                if self.path == "/runtime/semantic/legacy":
                    ster = sterilize_semantic_entities(extra_ctx={})
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/semantic/legacy",
                        "timestamp": time.time(),
                        "contract_version": "35B",
                        "legacy": ster.get("legacy_entities", []),
                    })
                    return

                if self.path == "/runtime/semantic/discoverable":
                    truth = build_operational_truth(extra_ctx={})
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/semantic/discoverable",
                        "timestamp": time.time(),
                        "contract_version": "35B",
                        "discoverable_nodes": truth.get("discoverable_nodes", []),
                    })
                    return

                if self.path == "/runtime/semantic/inventory":
                    truth = build_operational_truth(extra_ctx={})
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/semantic/inventory",
                        "timestamp": time.time(),
                        "contract_version": "35B",
                        "inventory_only_nodes": truth.get("inventory_only_nodes", []),
                    })
                    return

                if self.path == "/runtime/semantic/hygiene":
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/semantic/hygiene",
                        "timestamp": time.time(),
                        "contract_version": "35B",
                        "hygiene": build_identity_hygiene_summary(extra_ctx={}),
                    })
                    return

                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": self.path.lstrip("/"),
                    "timestamp": time.time(),
                    "contract_version": "35B",
                    "error": "unknown_semantic_endpoint",
                })
                return

            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": self.path.lstrip("/"),
                    "timestamp": time.time(),
                    "contract_version": "35B",
                    "error": str(exc),
                })
                return
 
        # ── FASE 35C: Live authority-backed cognition — always-on 200 ──
        if self.path == "/runtime/authority" or self.path.startswith("/runtime/authority/"):
            try:
                from runtime.authority import (
                    build_live_authority_snapshot,
                    build_authority_cognition_summary,
                    query_prometheus_authority,
                    get_authority_cache_state,
                    prime_authority_cache,
                )
                from runtime.telemetry.prometheus_metrics import record_authority_summary

                if self.path == "/runtime/authority" or self.path == "/runtime/authority/score":
                    summ = build_authority_cognition_summary(extra_ctx={})
                    try:
                        record_authority_summary(summ)
                    except Exception:
                        pass
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": self.path.lstrip("/"),
                        "timestamp": time.time(),
                        "contract_version": "35C",
                        "summary": summ,
                        "cache": get_authority_cache_state(),
                    })
                    return

                if self.path == "/runtime/authority/live":
                    snap = build_live_authority_snapshot(extra_ctx={})
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/authority/live",
                        "timestamp": time.time(),
                        "contract_version": "35C",
                        "snapshot": snap,
                    })
                    return

                if self.path == "/runtime/authority/freshness":
                    snap = build_live_authority_snapshot(extra_ctx={})
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/authority/freshness",
                        "timestamp": time.time(),
                        "contract_version": "35C",
                        "freshness": snap.get("freshness", {}),
                    })
                    return

                if self.path == "/runtime/authority/prometheus":
                    prom = query_prometheus_authority(extra_ctx={})
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/authority/prometheus",
                        "timestamp": time.time(),
                        "contract_version": "35C",
                        "prometheus": prom,
                    })
                    return

                if self.path == "/runtime/authority/operational":
                    snap = build_live_authority_snapshot(extra_ctx={})
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/authority/operational",
                        "timestamp": time.time(),
                        "contract_version": "35C",
                        "operational_truth": snap.get("operational_truth", {}),
                    })
                    return

                if self.path == "/runtime/authority/gaps":
                    snap = build_live_authority_snapshot(extra_ctx={})
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/authority/gaps",
                        "timestamp": time.time(),
                        "contract_version": "35C",
                        "gaps": snap.get("gaps", []),
                    })
                    return

                if self.path == "/runtime/authority/grounded":
                    snap = build_live_authority_snapshot(extra_ctx={})
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/authority/grounded",
                        "timestamp": time.time(),
                        "contract_version": "35C",
                        "grounded": (snap.get("freshness", {}) or {}).get("status") in ("fresh", "partial"),
                        "freshness": snap.get("freshness", {}),
                    })
                    return

                if self.path == "/runtime/authority/cache":
                    self._send_json(200, {
                        "status": "ok",
                        "service": "ai-lab-openai-gateway",
                        "endpoint": "runtime/authority/cache",
                        "timestamp": time.time(),
                        "contract_version": "35C",
                        "cache": get_authority_cache_state(),
                        "primed": prime_authority_cache(extra_ctx={}),
                    })
                    return

                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": self.path.lstrip("/"),
                    "timestamp": time.time(),
                    "contract_version": "35C",
                    "error": "unknown_authority_endpoint",
                })
                return
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": self.path.lstrip("/"),
                    "timestamp": time.time(),
                    "contract_version": "35C",
                    "error": str(exc),
                })
                return
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": self.path.lstrip("/"),
                    "timestamp": time.time(),
                    "contract_version": "35B",
                    "error": str(exc),
                })
                return
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": self.path.lstrip("/"),
                    "timestamp": time.time(),
                    "contract_version": "35A",
                    "error": str(exc),
                })
                return

        if self.path == "/runtime/reports/discipline":
            try:
                from runtime.gateway.tool_request_classifier import FORBIDDEN_TOOL_RECOMMENDATIONS
                _forbidden_list = sorted(FORBIDDEN_TOOL_RECOMMENDATIONS)
            except Exception:
                _forbidden_list = []
            self._send_json(200, {
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/reports/discipline",
                "forbidden_tools": _forbidden_list,
                "section_target": "12. RECOMENDACIONES TECNICAS",
                "generic_recommendation_guard": True,
                "status": "operational",
                "timestamp": int(time.time()),
            })
            return

        # FASE 30H: runtime/reports/evidence — always-on 200
        if self.path == "/runtime/reports/evidence":
            try:
                from runtime.context.evidence_guard import (
                    STRICT_EVIDENCE_MODE, MAX_UNVERIFIED_CLAIMS,
                )
                _strict_mode = STRICT_EVIDENCE_MODE
                _max_claims = MAX_UNVERIFIED_CLAIMS
            except Exception:
                _strict_mode = True
                _max_claims = 5
            self._send_json(200, {
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/reports/evidence",
                "evidence_guard_enabled": True,
                "strict_evidence_mode": _strict_mode,
                "max_unverified_claims": _max_claims,
                "phase": "30H",
                "categories_guarded": [
                    "forbidden_model_prefixes",
                    "forbidden_gpu_models",
                    "forbidden_security_tools",
                    "forbidden_external_platforms",
                    "unknown_model_ids",
                    "unknown_hosts_ips",
                ],
                "hallucination_risk_thresholds": {
                    "low": "0-2 unverified claims",
                    "medium": "3-4 unverified claims",
                    "high": "5+ unverified claims",
                },
                "status": "operational",
                "timestamp": int(time.time()),
            })
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
                record_error_legacy(self.path, exc)
                emit_error(build_error_event(
                    exc, origin_stage="upstream", component="gateway",
                    source_file=__file__, slo_impact=True,
                ))

                self._send_json(
                    502,
                    {
                        "error": "gateway_models_proxy_failed",
                        "detail": str(exc),
                    },
                )

            return

        # ── FASE 33A: Runtime Governance Registry — always-on 200 ──
        if self.path == "/runtime/governance":
            try:
                from runtime.governance import build_runtime_governance_registry, GOVERNANCE_CONTRACT_VERSION
                from runtime.telemetry.prometheus_metrics import record_governance_metrics
                _registry = build_runtime_governance_registry()
                record_governance_metrics(_registry)
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/governance",
                    "timestamp": time.time(),
                    "contract_version": GOVERNANCE_CONTRACT_VERSION,
                    "governance_registry": _registry,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/governance",
                    "timestamp": time.time(),
                    "contract_version": "33A",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/governance/domains":
            try:
                from runtime.governance import build_governance_domains, GOVERNANCE_CONTRACT_VERSION
                _domains = build_governance_domains()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/governance/domains",
                    "timestamp": time.time(),
                    "contract_version": GOVERNANCE_CONTRACT_VERSION,
                    "domains": _domains,
                    "total_domains": len(_domains),
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/governance/domains",
                    "timestamp": time.time(),
                    "contract_version": "33A",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/governance/contracts":
            try:
                from runtime.governance import build_governance_contract_registry, GOVERNANCE_CONTRACT_VERSION
                _contracts = build_governance_contract_registry()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/governance/contracts",
                    "timestamp": time.time(),
                    "contract_version": GOVERNANCE_CONTRACT_VERSION,
                    "contract_registry": _contracts,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/governance/contracts",
                    "timestamp": time.time(),
                    "contract_version": "33A",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/governance/risks":
            try:
                from runtime.governance import build_governance_risk_summary, GOVERNANCE_CONTRACT_VERSION
                _risks = build_governance_risk_summary()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/governance/risks",
                    "timestamp": time.time(),
                    "contract_version": GOVERNANCE_CONTRACT_VERSION,
                    "risks": _risks,
                    "total_risks": len(_risks),
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/governance/risks",
                    "timestamp": time.time(),
                    "contract_version": "33A",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/governance/confidence":
            try:
                from runtime.governance import build_governance_confidence_map, GOVERNANCE_CONTRACT_VERSION
                _confidence = build_governance_confidence_map()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/governance/confidence",
                    "timestamp": time.time(),
                    "contract_version": GOVERNANCE_CONTRACT_VERSION,
                    "confidence_map": _confidence,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/governance/confidence",
                    "timestamp": time.time(),
                    "contract_version": "33A",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/governance/remediation":
            try:
                from runtime.governance import build_governance_remediation_summary, GOVERNANCE_CONTRACT_VERSION
                _remediation = build_governance_remediation_summary()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/governance/remediation",
                    "timestamp": time.time(),
                    "contract_version": GOVERNANCE_CONTRACT_VERSION,
                    "remediation": _remediation,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/governance/remediation",
                    "timestamp": time.time(),
                    "contract_version": "33A",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/governance/score":
            try:
                from runtime.governance import calculate_governance_score, GOVERNANCE_CONTRACT_VERSION
                from runtime.telemetry.prometheus_metrics import GOVERNANCE_SCORE
                _score = calculate_governance_score()
                GOVERNANCE_SCORE.set(float(_score.get("governance_score", 0)))
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/governance/score",
                    "timestamp": time.time(),
                    "contract_version": GOVERNANCE_CONTRACT_VERSION,
                    "governance_score": _score,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/governance/score",
                    "timestamp": time.time(),
                    "contract_version": "33A",
                    "error": str(exc),
                })
            return

        # ── FASE 33B: Runtime Pre-Pilot Validation Framework — always-on 200 ──
        if self.path == "/runtime/validation":
            try:
                from runtime.validation import build_runtime_validation_report, VALIDATION_CONTRACT_VERSION
                from runtime.telemetry.prometheus_metrics import record_validation_metrics
                _report = build_runtime_validation_report()
                record_validation_metrics(_report)
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/validation",
                    "timestamp": time.time(),
                    "contract_version": VALIDATION_CONTRACT_VERSION,
                    "validation": _report,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/validation",
                    "timestamp": time.time(),
                    "contract_version": "33B",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/validation/invariants":
            try:
                from runtime.validation import build_runtime_invariants, VALIDATION_CONTRACT_VERSION
                _inv = build_runtime_invariants()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/validation/invariants",
                    "timestamp": time.time(),
                    "contract_version": VALIDATION_CONTRACT_VERSION,
                    "invariants": _inv,
                    "total_invariants": len(_inv),
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/validation/invariants",
                    "timestamp": time.time(),
                    "contract_version": "33B",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/validation/gates":
            try:
                from runtime.validation import build_runtime_safety_gates, VALIDATION_CONTRACT_VERSION
                _gates = build_runtime_safety_gates()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/validation/gates",
                    "timestamp": time.time(),
                    "contract_version": VALIDATION_CONTRACT_VERSION,
                    "safety_gates": _gates,
                    "total_gates": len(_gates),
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/validation/gates",
                    "timestamp": time.time(),
                    "contract_version": "33B",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/validation/readiness":
            try:
                from runtime.validation import build_runtime_pilot_readiness, VALIDATION_CONTRACT_VERSION
                _readiness = build_runtime_pilot_readiness()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/validation/readiness",
                    "timestamp": time.time(),
                    "contract_version": VALIDATION_CONTRACT_VERSION,
                    "pilot_readiness": _readiness,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/validation/readiness",
                    "timestamp": time.time(),
                    "contract_version": "33B",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/validation/failures":
            try:
                from runtime.validation import detect_runtime_validation_failures, VALIDATION_CONTRACT_VERSION
                _fail = detect_runtime_validation_failures()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/validation/failures",
                    "timestamp": time.time(),
                    "contract_version": VALIDATION_CONTRACT_VERSION,
                    "failures": _fail,
                    "total_failures": len(_fail),
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/validation/failures",
                    "timestamp": time.time(),
                    "contract_version": "33B",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/validation/regressions":
            try:
                from runtime.validation import build_runtime_regression_summary, VALIDATION_CONTRACT_VERSION
                _reg = build_runtime_regression_summary()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/validation/regressions",
                    "timestamp": time.time(),
                    "contract_version": VALIDATION_CONTRACT_VERSION,
                    "regressions": _reg,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/validation/regressions",
                    "timestamp": time.time(),
                    "contract_version": "33B",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/validation/score":
            try:
                from runtime.validation import calculate_runtime_validation_score, VALIDATION_CONTRACT_VERSION
                from runtime.telemetry.prometheus_metrics import VALIDATION_SCORE
                _score = calculate_runtime_validation_score()
                VALIDATION_SCORE.set(float(_score.get("validation_score", 0)))
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/validation/score",
                    "timestamp": time.time(),
                    "contract_version": VALIDATION_CONTRACT_VERSION,
                    "validation_score": _score,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/validation/score",
                    "timestamp": time.time(),
                    "contract_version": "33B",
                    "error": str(exc),
                })
            return

        # ── FASE 34A: Runtime Operational Hardening — always-on 200 ──
        if self.path == "/runtime/hardening":
            try:
                from runtime.hardening import build_runtime_hardening_report, HARDENING_CONTRACT_VERSION
                _report = build_runtime_hardening_report()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/hardening",
                    "timestamp": time.time(),
                    "contract_version": HARDENING_CONTRACT_VERSION,
                    "hardening": _report,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/hardening",
                    "timestamp": time.time(),
                    "contract_version": "34A",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/hardening/watchdogs":
            try:
                from runtime.hardening import build_runtime_watchdogs, HARDENING_CONTRACT_VERSION
                _watchdogs = build_runtime_watchdogs()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/hardening/watchdogs",
                    "timestamp": time.time(),
                    "contract_version": HARDENING_CONTRACT_VERSION,
                    "watchdogs": _watchdogs,
                    "total_watchdogs": len(_watchdogs),
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/hardening/watchdogs",
                    "timestamp": time.time(),
                    "contract_version": "34A",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/hardening/timeouts":
            try:
                from runtime.hardening import build_timeout_governance, HARDENING_CONTRACT_VERSION
                _timeouts = build_timeout_governance()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/hardening/timeouts",
                    "timestamp": time.time(),
                    "contract_version": HARDENING_CONTRACT_VERSION,
                    "timeouts": _timeouts,
                    "total_timeouts": len(_timeouts),
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/hardening/timeouts",
                    "timestamp": time.time(),
                    "contract_version": "34A",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/hardening/escalation":
            try:
                from runtime.hardening import build_degraded_escalation, HARDENING_CONTRACT_VERSION
                _esc = build_degraded_escalation()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/hardening/escalation",
                    "timestamp": time.time(),
                    "contract_version": HARDENING_CONTRACT_VERSION,
                    "escalation": _esc,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/hardening/escalation",
                    "timestamp": time.time(),
                    "contract_version": "34A",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/hardening/containment":
            try:
                from runtime.hardening import build_failure_containment_summary, HARDENING_CONTRACT_VERSION
                _cont = build_failure_containment_summary()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/hardening/containment",
                    "timestamp": time.time(),
                    "contract_version": HARDENING_CONTRACT_VERSION,
                    "containment": _cont,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/hardening/containment",
                    "timestamp": time.time(),
                    "contract_version": "34A",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/hardening/safeguards":
            try:
                from runtime.hardening import build_operational_safeguards, HARDENING_CONTRACT_VERSION
                _sg = build_operational_safeguards()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/hardening/safeguards",
                    "timestamp": time.time(),
                    "contract_version": HARDENING_CONTRACT_VERSION,
                    "safeguards": _sg,
                    "total_safeguards": len(_sg),
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/hardening/safeguards",
                    "timestamp": time.time(),
                    "contract_version": "34A",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/hardening/survivability":
            try:
                from runtime.hardening import build_runtime_survivability, HARDENING_CONTRACT_VERSION
                _sv = build_runtime_survivability()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/hardening/survivability",
                    "timestamp": time.time(),
                    "contract_version": HARDENING_CONTRACT_VERSION,
                    "survivability": _sv,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/hardening/survivability",
                    "timestamp": time.time(),
                    "contract_version": "34A",
                    "error": str(exc),
                })
            return

        if self.path == "/runtime/hardening/score":
            try:
                from runtime.hardening import calculate_hardening_score, HARDENING_CONTRACT_VERSION
                _score = calculate_hardening_score()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/hardening/score",
                    "timestamp": time.time(),
                    "contract_version": HARDENING_CONTRACT_VERSION,
                    "hardening_score": _score,
                })
            except Exception as exc:
                self._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/hardening/score",
                    "timestamp": time.time(),
                    "contract_version": "34A",
                    "error": str(exc),
                })
            return

        # ── FASE 28.4: Tool Contracts & Cross-Plan GC — always-on 200 ──
        if self.path == "/runtime/tools":
            try:
                from runtime.tools import build_tool_registry
                data = build_tool_registry()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/tools",
                    "timestamp": time.time(),
                    "tools": data,
                })
            except Exception as exc:
                self._send_json(200, {"status": "degraded", "endpoint": "runtime/tools", "error": str(exc), "timestamp": time.time()})
            return

        if self.path == "/runtime/tools/contracts":
            try:
                from runtime.tools import build_tool_contracts, TOOL_CONTRACT_VERSION
                data = build_tool_contracts()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/tools/contracts",
                    "timestamp": time.time(),
                    "contract_version": TOOL_CONTRACT_VERSION,
                    "tool_contracts": data,
                    "total": len(data),
                })
            except Exception as exc:
                self._send_json(200, {"status": "degraded", "endpoint": "runtime/tools/contracts", "error": str(exc), "timestamp": time.time(), "contract_version": "28.4"})
            return

        if self.path == "/runtime/tools/governance":
            try:
                from runtime.tools import calculate_tool_governance_score
                from runtime.plans import build_plan_registry
                from runtime.gc import build_gc_inventory, detect_gc_candidates, protect_governance_artifacts, protect_active_validation_artifacts, protect_runtime_authority_artifacts, calculate_gc_safety_score
                tool_gov = calculate_tool_governance_score()
                plans = build_plan_registry()
                inv = build_gc_inventory()
                inv = protect_governance_artifacts(inv)
                inv = protect_active_validation_artifacts(inv)
                inv = protect_runtime_authority_artifacts(inv)
                cand = detect_gc_candidates(inv)
                safety = calculate_gc_safety_score(inv, cand)
                try:
                    from runtime.telemetry.prometheus_metrics import record_tool_gc_metrics
                    record_tool_gc_metrics(tool_gov, plans, {"inventory": inv, "candidates": cand, "safety": safety})
                except ImportError:
                    pass
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/tools/governance",
                    "timestamp": time.time(),
                    "tool_governance": tool_gov,
                    "plan_registry": {"total_plans": plans.get("total_plans", 0)},
                    "gc": {"candidates_total": len(cand), "gc_safety_score": safety.get("gc_safety_score", 0)},
                })
            except Exception as exc:
                self._send_json(200, {"status": "degraded", "endpoint": "runtime/tools/governance", "error": str(exc), "timestamp": time.time()})
            return

        if self.path == "/runtime/plans":
            try:
                from runtime.plans import build_plan_registry, PLAN_CONTRACT_VERSION
                data = build_plan_registry()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/plans",
                    "timestamp": time.time(),
                    "contract_version": PLAN_CONTRACT_VERSION,
                    "plan_registry": data,
                })
            except Exception as exc:
                self._send_json(200, {"status": "degraded", "endpoint": "runtime/plans", "error": str(exc), "timestamp": time.time(), "contract_version": "28.4"})
            return

        if self.path == "/runtime/plans/graph":
            try:
                from runtime.plans import build_cross_plan_references, PLAN_CONTRACT_VERSION
                graph = build_cross_plan_references()
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/plans/graph",
                    "timestamp": time.time(),
                    "contract_version": PLAN_CONTRACT_VERSION,
                    "crossplan_graph": graph,
                })
            except Exception as exc:
                self._send_json(200, {"status": "degraded", "endpoint": "runtime/plans/graph", "error": str(exc), "timestamp": time.time(), "contract_version": "28.4"})
            return

        if self.path == "/runtime/gc":
            try:
                from runtime.gc import (
                    build_gc_inventory, detect_gc_candidates,
                    protect_governance_artifacts, protect_active_validation_artifacts, protect_runtime_authority_artifacts,
                    calculate_gc_safety_score, build_gc_execution_plan,
                    GC_CONTRACT_VERSION,
                )
                inv = build_gc_inventory()
                inv = protect_governance_artifacts(inv)
                inv = protect_active_validation_artifacts(inv)
                inv = protect_runtime_authority_artifacts(inv)
                cand = detect_gc_candidates(inv)
                safety = calculate_gc_safety_score(inv, cand)
                plan = build_gc_execution_plan(inv, cand)
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/gc",
                    "timestamp": time.time(),
                    "contract_version": GC_CONTRACT_VERSION,
                    "inventory": inv,
                    "candidates": cand,
                    "safety": safety,
                    "execution_plan": plan,
                })
            except Exception as exc:
                self._send_json(200, {"status": "degraded", "endpoint": "runtime/gc", "error": str(exc), "timestamp": time.time(), "contract_version": "28.4"})
            return

        if self.path == "/runtime/gc/candidates":
            try:
                from runtime.gc import (
                    build_gc_inventory, detect_gc_candidates,
                    protect_governance_artifacts, protect_active_validation_artifacts, protect_runtime_authority_artifacts,
                    GC_CONTRACT_VERSION,
                )
                inv = build_gc_inventory()
                inv = protect_governance_artifacts(inv)
                inv = protect_active_validation_artifacts(inv)
                inv = protect_runtime_authority_artifacts(inv)
                cand = detect_gc_candidates(inv)
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/gc/candidates",
                    "timestamp": time.time(),
                    "contract_version": GC_CONTRACT_VERSION,
                    "candidates": cand,
                    "total": len(cand),
                })
            except Exception as exc:
                self._send_json(200, {"status": "degraded", "endpoint": "runtime/gc/candidates", "error": str(exc), "timestamp": time.time(), "contract_version": "28.4"})
            return

        if self.path == "/runtime/gc/safety":
            try:
                from runtime.gc import (
                    build_gc_inventory, detect_gc_candidates,
                    protect_governance_artifacts, protect_active_validation_artifacts, protect_runtime_authority_artifacts,
                    calculate_gc_safety_score, GC_CONTRACT_VERSION,
                )
                inv = build_gc_inventory()
                inv = protect_governance_artifacts(inv)
                inv = protect_active_validation_artifacts(inv)
                inv = protect_runtime_authority_artifacts(inv)
                cand = detect_gc_candidates(inv)
                safety = calculate_gc_safety_score(inv, cand)
                self._send_json(200, {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/gc/safety",
                    "timestamp": time.time(),
                    "contract_version": GC_CONTRACT_VERSION,
                    "gc_safety": safety,
                })
            except Exception as exc:
                self._send_json(200, {"status": "degraded", "endpoint": "runtime/gc/safety", "error": str(exc), "timestamp": time.time(), "contract_version": "28.4"})
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
            stream_enabled = False

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

            compact_runtime_answer = payload.pop("_compact_runtime_answer", None)
            if compact_runtime_answer:
                self._send_json(200, {
                    "id": f"chatcmpl-operational-{_request_id}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": payload.get("model", "runtime-operational-formatter"),
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": compact_runtime_answer}, "finish_reason": "stop"}],
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
            # FASE 30I-F0: Also block deprecated lmstudio-community/qwen2.5-coder-14b-instruct
            DISABLED_MODELS = {"qwen3.6-27b", "qwen/qwen3.6-27b", "lmstudio-community/qwen3.6-27b"}
            if selected_model in DISABLED_MODELS or "qwen3.6" in (selected_model or "").lower():
                original = selected_model
                selected_model = "qwen2.5-coder-14b-instruct"
                try:
                    from runtime.telemetry.prometheus_metrics import record_disabled_model_selection
                    record_disabled_model_selection(original, "disabled_model_redirect")
                except ImportError:
                    pass
                emit_error(build_error_event(
                    RuntimeError(f"disabled model {original} redirected to {selected_model}"),
                    category=RuntimeErrorCategory.MODEL_DISABLED,
                    origin_stage="routing", component="gateway",
                    source_file=__file__,
                    model=selected_model, route_type=route_family,
                    slo_impact=False,
                ))
            elif is_deprecated_model(selected_model):
                original = selected_model
                selected_model = "qwen2.5-coder-14b-instruct"
                try:
                    from runtime.telemetry.prometheus_metrics import (
                        record_deprecated_model_routing,
                        record_disabled_model_selection,
                    )
                    record_deprecated_model_routing("blocked_to_qwen_fallback")
                    record_disabled_model_selection(original, "deprecated_model_redirect")
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

            # FASE 30I-F0: Model routing policy — validate operational/coding/deprecated
            _validated = validate_model_selection(
                task_type=task_type,
                model_id=selected_model,
                route_family=route_family,
                user_text=observe_user_text,
            )
            if _validated != selected_model:
                try:
                    from runtime.telemetry.prometheus_metrics import (
                        record_deprecated_model_routing,
                        record_operational_model_selected,
                        record_coding_model_selected,
                    )
                    if is_deprecated_model(selected_model):
                        record_deprecated_model_routing("blocked_to_operational")
                    if _validated == PRIMARY_OPERATIONAL_MODEL:
                        record_operational_model_selected()
                    elif _validated == PRIMARY_CODING_MODEL:
                        record_coding_model_selected()
                except ImportError:
                    pass
                selected_model = _validated
            else:
                if selected_model == PRIMARY_OPERATIONAL_MODEL:
                    try:
                        from runtime.telemetry.prometheus_metrics import record_operational_model_selected
                        record_operational_model_selected()
                    except ImportError:
                        pass
                elif selected_model == PRIMARY_CODING_MODEL:
                    try:
                        from runtime.telemetry.prometheus_metrics import record_coding_model_selected
                        record_coding_model_selected()
                    except ImportError:
                        pass

            # FASE 30H.1: respect explicit model request from payload (AFTER routing policy)
            # so burn-in / testing with specific models can override routing + degradation
            _rm_lower = requested_model.lower() if isinstance(requested_model, str) else ""
            _sm_lower = selected_model.lower() if isinstance(selected_model, str) else ""
            if _rm_lower and _rm_lower != _sm_lower:
                if _rm_lower in ("qwen/qwen2.5-coder-14b-instruct", "qwen2.5-coder-14b-instruct"):
                    selected_model = "qwen/qwen2.5-coder-14b-instruct"
                elif _rm_lower == "llama-3.1-8b-instruct":
                    selected_model = "llama-3.1-8b-instruct"

            if selected_model not in _warmed_models:
                _warmed_models.add(selected_model)
                try:
                    from runtime.telemetry.prometheus_metrics import COLD_START_TOTAL
                    COLD_START_TOTAL.labels(model=selected_model).inc()
                except ImportError:
                    pass

            session_id = create_session(task_type, selected_model, get_active_backend()["name"])
            payload["model"] = selected_model
            payload["_ai_lab_selected_model"] = selected_model
            payload["_ai_lab_route_family"] = route_family

            stream_enabled = bool(payload.get("stream", False))

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

            upstream_payload["parallel_tool_calls"] = False

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
                        record_error_legacy(self.path, exc)
                        emit_error(build_error_event(
                            exc, origin_stage="streaming", component="gateway",
                            source_file=__file__, streaming=True,
                            model=selected_model, route_type=route_family,
                            slo_impact=True, latency_ms=latency_ms,
                        ))
                        record_route_family_metrics(route_family, count=False, latency_ms=latency_ms, error=True)
                        if _HAVE_SLO:
                            _circuit_breakers.record_failure(selected_model)
                    return

                # Legacy: Fake SSE path (FASE 27.1.1 — fallback when AI_LAB_REAL_STREAMING=false)
                try:
                    data = response.json()
                except Exception as exc:
                    record_error_legacy(self.path, exc)
                    emit_error(build_error_event(
                        exc, category=RuntimeErrorCategory.UPSTREAM_INVALID_RESPONSE,
                        origin_stage="upstream", component="gateway",
                        source_file=__file__, streaming=False,
                        model=selected_model, route_type=route_family,
                    ))
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

            _sanitize_route = route_family if 'route_family' in dir() and route_family else payload.get("_ai_lab_route_family", "unknown")
            _sanitize_model = selected_model if 'selected_model' in dir() and selected_model else payload.get("model", "unknown")
            _sanitize_profile = payload.get("_profile", "unknown")
            data = sanitize_completion_response(data, route_family=_sanitize_route, model=_sanitize_model, profile=_sanitize_profile)

            _compact_profile = payload.get("_operational_response_profile", "operational_compact") if isinstance(payload, dict) else "operational_compact"
            _runtime_json = payload.get("_report_runtime_context") if isinstance(payload, dict) else None
            _user_prompt = payload.get("_user_text", "") if isinstance(payload, dict) else ""
            _formatted_response = compact_runtime_response(_user_prompt, _runtime_json, profile=_compact_profile)
            if _formatted_response:
                for _choice in data.get("choices", []):
                    _msg = _choice.get("message", {}) if isinstance(_choice, dict) else {}
                    if isinstance(_msg, dict):
                        _msg["content"] = _formatted_response

            # FASE 30H.1: Universal Evidence Guard — applies to ALL routes
            # when should_apply_evidence_guard detects runtime-state intent
            _guard_scope = should_apply_evidence_guard(
                payload, _sanitize_route, payload.get("_user_text", ""),
            )
            if _guard_scope:
                for _choice in data.get("choices", []):
                    _msg = _choice.get("message", {}) if isinstance(_choice, dict) else {}
                    _content = _msg.get("content", "")
                    if isinstance(_content, str) and _content:
                        _report_json = payload.get("_report_runtime_context") if isinstance(payload, dict) else None
                        _cleaned, _found = sanitize_report_output(
                            _content,
                            runtime_context_json=_report_json,
                        )
                        if _found:
                            _msg["content"] = _cleaned
                            try:
                                from runtime.telemetry.prometheus_metrics import (
                                    record_report_forbidden_recommendation,
                                )
                                for _tool in _found:
                                    if _tool.startswith("model_not_in_observed:") or _tool.startswith("gpu_not_in_observed:") or _tool.startswith("security_tool_not_in_runtime:") or _tool.startswith("external_platform_not_in_runtime:") or _tool.startswith("orchestration_tool_not_in_runtime:") or _tool.startswith("os_version_not_observed:") or _tool.startswith("unknown_model:") or _tool.startswith("unknown_ip:") or _tool.startswith("unknown_host:"):
                                        continue
                                    record_report_forbidden_recommendation(_tool)
                            except ImportError:
                                pass
                        # FASE 30H.1: record evidence guard metrics (scoped)
                        try:
                            from runtime.telemetry.prometheus_metrics import (
                                record_report_evidence_guard,
                                record_report_evidence_guard_scoped,
                                record_report_unverified_claim,
                                record_report_evidence_score,
                                record_report_hallucination_suppressed,
                            )
                            record_report_evidence_guard()
                            record_report_evidence_guard_scoped(
                                action="passed",
                                model=_sanitize_model,
                                route_family=_sanitize_route,
                                guard_scope=_guard_scope,
                            )
                            _evidence_claims = [c for c in _found if c.startswith((
                                "model_not_in_observed:", "gpu_not_in_observed:",
                                "security_tool_not_in_runtime:", "external_platform_not_in_runtime:",
                                "orchestration_tool_not_in_runtime:", "os_version_not_observed:",
                                "unknown_model:", "unknown_ip:", "unknown_host:",
                            ))]
                            if _evidence_claims:
                                record_report_unverified_claim(len(_evidence_claims))
                                _evidence_score = max(0.0, 1.0 - (0.15 * len(_evidence_claims)))
                                record_report_evidence_score(_evidence_score)
                                record_report_evidence_guard_scoped(
                                    action="sanitized",
                                    model=_sanitize_model,
                                    route_family=_sanitize_route,
                                    guard_scope=_guard_scope,
                                )
                                if len(_evidence_claims) >= 5:
                                    record_report_hallucination_suppressed()
                                    record_report_evidence_guard_scoped(
                                        action="blocked",
                                        model=_sanitize_model,
                                        route_family=_sanitize_route,
                                        guard_scope=_guard_scope,
                                    )
                        except ImportError:
                            pass
            else:
                # FASE 30H.1: record skipped scoped metric with route family
                try:
                    from runtime.telemetry.prometheus_metrics import (
                        record_report_evidence_guard_scoped,
                    )
                    record_report_evidence_guard_scoped(
                        action="skipped",
                        model=_sanitize_model,
                        route_family=_sanitize_route,
                        guard_scope="fallback_disabled",
                    )
                except ImportError:
                    pass

            # FASE 28.2: Agentic Pipeline — READONLY EXECUTION — BEFORE sending response
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
                        record_executor_dry_run, record_executor_validation_failure,
                    )
                    from runtime.agentic.execution_context import RuntimeExecutionContext, ExecutionMode, DryRunReason

                    plan = Planner.plan(intents, request_id=payload.get("_request_id", ""))
                    record_agentic_plan(route_family or "unknown", len(intents))

                    dry_run = DryRunEngine.run(plan)
                    record_agentic_dry_run(dry_run.overall_risk)
                    record_agentic_risk_score(route_family or "unknown", dry_run.risk_score)

                    report = ExplainabilityEngine.explain(plan, dry_run)

                    timeline = WorkflowTimeline(plan_id=plan.plan_id)
                    timeline.add_event("plan_generated", "planning", {"intent_count": len(intents)})
                    timeline.add_event("dry_run_completed", "evaluated", dry_run.to_dict())

                    _simulation_only = True
                    _execution_dry_run = True
                    _dry_run_reason = DryRunReason.FEATURE_FLAG.value

                    if dry_run.blocked:
                        timeline.transition(WorkflowState.FAILED)
                    elif dry_run.requires_approval:
                        timeline.transition(WorkflowState.AWAITING_APPROVAL)
                    elif AI_LAB_ENABLE_SANDBOX_WRITE and _HAVE_SANDBOX_EXECUTOR and _has_sandbox_intents(intents):
                        _execution_dry_run = False
                        _simulation_only = False
                        _dry_run_reason = None
                        ctx = MutationExecutionContext(
                            execution_id=plan.plan_id[:8] if plan.plan_id else "",
                            mode=ExecutionMode.SANDBOX_WRITE,
                            dry_run=False,
                            phase="28.3",
                        )
                        execution = SandboxWriteExecutor.execute(plan, timeline, ctx=ctx)
                        record_agentic_execution("completed", "sandbox_write")
                        for ar in execution.actions_results:
                            record_agentic_action(ar.tool, ar.status, ar.intent)
                        record_agentic_execution_duration("sandbox_write", execution.total_duration_ms)
                        verifier = Verifier.verify(plan, dry_run, execution)
                        timeline.add_event("verifier_completed", "done", verifier.to_dict())
                    elif AI_LAB_ENABLE_PLANNER and not AI_LAB_PLANNER_DRY_RUN and _HAVE_EXECUTOR:
                        _execution_dry_run = False
                        _simulation_only = False
                        _dry_run_reason = None
                        ctx = RuntimeExecutionContext(
                            execution_id=plan.plan_id[:8] if plan.plan_id else "",
                            mode=ExecutionMode.READONLY,
                            dry_run=False,
                        )
                        execution = RealReadonlyExecutor.execute(plan, timeline, ctx=ctx)
                        record_agentic_execution("completed", "readonly")
                        for ar in execution.actions_results:
                            record_agentic_action(ar.tool, ar.status, ar.intent)
                        record_agentic_execution_duration("readonly", execution.total_duration_ms)
                        verifier = Verifier.verify(plan, dry_run, execution)
                        timeline.add_event("verifier_completed", "done", verifier.to_dict())
                    else:
                        # Dry-run / simulation-only path
                        if AI_LAB_PLANNER_DRY_RUN:
                            _dry_run_reason = DryRunReason.READONLY_PHASE.value
                        ctx = RuntimeExecutionContext(
                            execution_id=plan.plan_id[:8] if plan.plan_id else "",
                            mode=ExecutionMode.READONLY,
                            dry_run=True,
                            dry_run_reason=_dry_run_reason,
                        )
                        execution = SimulationExecutor.execute_with_context(plan, timeline, ctx)
                        record_agentic_execution("simulated_success", "simulation_only")
                        record_executor_dry_run(_dry_run_reason)
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
                            "simulation_only": _simulation_only,
                            "execution_mode": ctx.mode.value if ctx else "readonly",
                            "dry_run": _execution_dry_run,
                            "dry_run_reason": _dry_run_reason,
                        })
                    except ImportError:
                        pass
            except Exception as e:
                print(f"AGENTIC ERROR: {e}", flush=True)
                emit_error(build_error_event(
                    e, category=RuntimeErrorCategory.WORKFLOW_INVALID_STATE,
                    origin_stage="agentic", component="gateway",
                    source_file=__file__,
                    model=selected_model if 'selected_model' in dir() else None,
                    route_type=route_family, slo_impact=False,
                ))

            # FASE 30I-G: Post-response grounding validation
            _grounding_prompt = payload.get("_user_text", "")
            if _grounding_prompt and is_runtime_grounded_prompt(_grounding_prompt):
                _response_content = ""
                for _choice in data.get("choices", []):
                    _msg = _choice.get("message", {}) if isinstance(_choice, dict) else {}
                    _response_content = _msg.get("content", "") if isinstance(_msg.get("content"), str) else ""
                    break
                if _response_content:
                    _runtime_json = payload.get("_report_runtime_context") if isinstance(payload, dict) else None
                    _gr_ctx = None
                    if _runtime_json:
                        try:
                            _gr_ctx = json.loads(_runtime_json) if isinstance(_runtime_json, str) else _runtime_json
                        except (json.JSONDecodeError, TypeError):
                            pass
                    _grounding_result = validate_response_against_observed_runtime(
                        _response_content, runtime_context=_gr_ctx,
                    )
                    if not _grounding_result.get("valid", True):
                        try:
                            from runtime.telemetry.prometheus_metrics import (
                                record_runtime_grounding_rejected,
                                record_runtime_grounding_rejection_reason,
                                record_runtime_grounding_unknown_state,
                            )
                            _inv_entities = _grounding_result.get("invented_entities", [])
                            for _inv in _inv_entities:
                                _etype = "gpu" if "gpu" in _inv.lower() else "model" if any(
                                    m in _inv.lower() for m in ("llama", "qwen", "gpt", "claude")
                                ) else "host"
                                record_runtime_grounding_rejected(
                                    model=selected_model, route_family=route_family,
                                    entity_type=_etype,
                                )
                                record_runtime_grounding_rejection_reason(
                                    f"entity_not_observed:{_etype}:{_inv}"
                                )
                            for _uclaim in _grounding_result.get("unverified_claims", []):
                                record_runtime_grounding_rejection_reason(_uclaim)
                            _ustate = _grounding_result.get("unknown_state")
                            if _ustate:
                                record_runtime_grounding_unknown_state(_ustate)
                            else:
                                record_runtime_grounding_unknown_state("NOT_OBSERVED")
                        except ImportError:
                            pass
                        # Replace content with sanitized version if violations detected
                        _sanitized = _grounding_result.get("sanitized_text", _response_content)
                        if _sanitized != _response_content:
                            for _choice in data.get("choices", []):
                                _msg = _choice.get("message", {}) if isinstance(_choice, dict) else {}
                                if isinstance(_msg, dict):
                                    _msg["content"] = _sanitized
                    else:
                        try:
                            from runtime.telemetry.prometheus_metrics import (
                                record_runtime_grounding_passed,
                            )
                            record_runtime_grounding_passed(
                                model=selected_model, route_family=route_family,
                            )
                        except ImportError:
                            pass

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
            record_error_legacy(self.path, exc)
            _stage = classify_timeout_stage(exc)
            emit_error(build_error_event(
                exc, origin_stage=_stage, component="gateway",
                source_file=__file__, streaming=stream_enabled,
                model=selected_model if 'selected_model' in dir() else None,
                route_type=route_family, slo_impact=True,
                latency_ms=latency_ms,
            ))
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
            record_error_legacy(self.path, exc)
            emit_error(build_error_event(
                exc, origin_stage="gateway", component="gateway",
                source_file=__file__, streaming=stream_enabled,
                model=selected_model if 'selected_model' in dir() else None,
                route_type=route_family, slo_impact=True,
                latency_ms=latency_ms,
            ))
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
