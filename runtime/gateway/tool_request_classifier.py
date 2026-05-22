"""Tool request detection and fastpath helpers."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any

_TOOL_SCHEMA_CACHE: dict[str, str] = {}

_FULL_CONTEXT_MARKERS = (
    "semantic recall",
    "learning",
    "incidents",
    "latency",
    "audit",
    "architect",
    "reasoning",
    "drift",
    "memory contamination",
    "recall",
    "history",
)

_GREETING_MARKERS = (
    # Spanish greetings
    "hola", "buenas", "buenos dias", "buenas tardes", "buenas noches",
    "gracias", "adios", "hasta luego", "nos vemos", "chao", "saludos",
    "que tal", "como estas", "cómo estás", "como va", "cómo va",
    "buen dia", "buen día",
    # Spanish short confirmations
    "ok", "okey", "vale", "genial", "perfecto", "claro", "entendido",
    "de acuerdo", "si", "sí", "no", "nop", "nope", "ya", "listo",
    "venga", "dale", "bien", "correcto", "exacto", "excelente",
    "fenomenal", "estupendo", "magnifico", "magnífico",
    # English
    "hello", "hi", "hey", "thanks", "thank you", "bye", "goodbye",
    "good morning", "good afternoon", "good evening", "see you",
    "cheers", "alright", "nice", "great", "awesome", "cool",
    "yes", "yeah", "yep", "nope", "sure", "got it", "okay",
    "understood", "fine", "done", "ready",
)

_CASUAL_MARKERS = (
    "que puedes hacer",
    "podrias decirme que puedes hacer",
    "podrías decirme que puedes hacer",
    "quien eres",
    "quién eres",
    "como funcionas",
    "cómo funcionas",
    "help",
    "ayuda",
    "what can you do",
)

_SYSTEM_REMINDER_RE = re.compile(
    r"<system-reminder>.*?</system-reminder>",
    re.IGNORECASE | re.DOTALL,
)

_OBSERVE_SECTION_RE = re.compile(
    r"\[(?:HARD_FACTS|INFERIDO|NO DISPONIBLE|PENDIENTE|SELF-CRITIQUE|AI-LAB DEBUG)\].*?(?=\n\[|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_OBSERVE_TAG_RE = re.compile(
    r"\[/?(?:HARD_FACTS|INFERIDO|NO DISPONIBLE|PENDIENTE|SELF-CRITIQUE|AI-LAB DEBUG)\]",
    re.IGNORECASE,
)
_OBSERVE_INTROSPECTION_RE = re.compile(
    r"^(the user is|let me|i need to|i should|i'll|voy a|debo|primero|now let me)",
    re.IGNORECASE,
)

ROUTE_FAMILIES = (
    "minimal",
    "observe",
    "tool_fastpath",
    "cognitive",
    "learning",
)


@dataclass(frozen=True)
class RuntimeRoute:
    family: str
    variant: str = "default"
    reason: str = ""


def sanitize_prompt_text(text: str | None) -> str:
    if not text:
        return ""
    cleaned = _SYSTEM_REMINDER_RE.sub("", text)
    return cleaned.strip()


def sanitize_payload_messages(payload: dict[str, Any]) -> dict[str, Any]:
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return payload

    cleaned_messages: list[dict[str, Any]] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        cleaned = dict(msg)
        content = cleaned.get("content")
        if isinstance(content, str):
            cleaned["content"] = sanitize_prompt_text(content)
        elif isinstance(content, list):
            new_items: list[Any] = []
            for item in content:
                if isinstance(item, dict):
                    new_item = dict(item)
                    if new_item.get("type") == "text" and isinstance(new_item.get("text"), str):
                        new_item["text"] = sanitize_prompt_text(new_item["text"])
                    new_items.append(new_item)
                else:
                    new_items.append(item)
            cleaned["content"] = new_items
        cleaned_messages.append(cleaned)

    payload = dict(payload)
    payload["messages"] = cleaned_messages
    return payload


def sanitize_observe_output(text: str | None, *, max_chars: int = 500) -> str:
    if not text:
        return ""

    cleaned = _OBSERVE_SECTION_RE.sub("\n", text)
    cleaned = _OBSERVE_TAG_RE.sub("", cleaned)

    lines: list[str] = []
    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _OBSERVE_INTROSPECTION_RE.match(line):
            continue
        if line.startswith("[") and line.endswith("]"):
            continue
        lines.append(line)

    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rstrip()
        last_break = cleaned.rfind("\n")
        if last_break > int(max_chars * 0.6):
            cleaned = cleaned[:last_break].rstrip()

    return cleaned


def build_observe_context() -> str:
    try:
        from runtime.state.runtime_state import get_runtime_state

        state = get_runtime_state() or {}
        minimal = {
            "runtime": state.get("runtime", "AI-LAB Cognitive Runtime"),
            "status": state.get("status", "unknown"),
            "mode": state.get("mode", "unknown"),
            "active_sessions": state.get("active_sessions", 0),
            "active_streams": state.get("active_streams", 0),
            "executions": state.get("executions", 0),
            "last_model": state.get("last_model"),
            "last_task": state.get("last_task"),
        }
        return json.dumps(minimal, ensure_ascii=False, default=str)
    except Exception:
        return json.dumps({"runtime": "AI-LAB Cognitive Runtime", "status": "unknown"}, ensure_ascii=False)


def _tool_choice_value(payload: dict[str, Any]) -> str:
    choice = payload.get("tool_choice")
    if isinstance(choice, str):
        return choice.lower().strip()
    if isinstance(choice, dict):
        return "required"
    return "none"


def is_tool_request(payload: dict[str, Any]) -> bool:
    tools = payload.get("tools") or []
    if tools:
        return True
    return _tool_choice_value(payload) in {"auto", "required"}


def _last_user_text(payload: dict[str, Any]) -> str:
    messages = payload.get("messages", [])
    for msg in reversed(messages):
        if msg.get("role") != "user":
            continue
        content = msg.get("content", "")
        if isinstance(content, str):
            return sanitize_prompt_text(content)
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(sanitize_prompt_text(str(item.get("text", ""))))
            return "\n".join(parts)
    return str(payload.get("input", "") or payload.get("query", "") or "")


_REASONING_KEYWORDS = (
    "analisis profundo",
    "análisis profundo",
    "arquitectura",
    "riesgos",
    "auditoria",
    "auditoría",
    "deep analysis",
    "reasoning",
    "tradeoffs",
    "riesgos arquitectura",
)


def _is_reasoning_request(text: str) -> bool:
    t = (text or "").lower().strip()
    if not t:
        return False
    if any(kw in t for kw in ("analisis profundo", "análisis profundo", "deep analysis")):
        return True
    keyword_count = sum(1 for kw in _REASONING_KEYWORDS if kw in t)
    return keyword_count >= 2


def _is_capability_question(text: str) -> bool:
    t = (text or "").lower()
    if not t:
        return False
    return any(k in t for k in (
        "qué puedes hacer", "que puedes hacer",
        "qué herramientas puedes usar", "que herramientas puedes usar",
        "qué sabes hacer", "que sabes hacer",
        "cómo puedes ayudar", "como puedes ayudar",
    ))


def is_creative_request(text_or_payload: Any) -> bool:
    """FASE 26.2.4: Detecta peticiones de escritura creativa/longform."""
    if isinstance(text_or_payload, dict):
        text = _last_user_text(text_or_payload)
    else:
        text = str(text_or_payload or "")
    t = text.lower()
    if not t:
        return False
    return any(k in t for k in (
        "historia", "relato", "cuento", "cyberpunk",
        "poema", "ficción", "novela",
        "escribe una introducción extensa", "escribe una introduccion extensa",
        "continúa esta historia", "continua esta historia",
    ))


def build_capability_answer() -> str:
    """FASE 26.2.3: Respuesta estatica con capacidades del AI-LAB."""
    return (
        "Puedo ayudarte a: "
        "- explicar errores tecnicos y tracebacks "
        "- revisar y corregir codigo "
        "- preparar informes y resumenes "
        "- analizar arquitectura y tradeoffs "
        "- leer archivos, hacer grep, ejecutar comandos readonly (bash) si lo pides explicitamente "
        "- proponer cambios sin ejecutarlos directamente "
        "- generar codigo, scripts, configuraciones "
        "No ejecuto herramientas sin peticion explicita. "
        "No muestro HARD_FACTS ni datos internos del runtime salvo que lo pidas."
    )


def build_observe_context_compact() -> str:
    """FASE 26.2.1: Contexto observado ultra-compacto sin HARD_FACTS."""
    try:
        from runtime.control.control_plane import get_control_state
        state = get_control_state() or {}
        return json.dumps({
            "mode": state.get("mode", "unknown"),
            "router": state.get("router_health", "unknown"),
            "gateway": state.get("gateway_health", "unknown"),
            "active_node": state.get("active_node", "NO DISPONIBLE"),
            "models_loaded": (state.get("models_loaded") or [])[:3],
            "route_summary": state.get("route_summary", {}),
            "governance_blocks": state.get("governance_blocks", 0),
        }, ensure_ascii=False, default=str)
    except Exception:
        pass
    try:
        from runtime.state.runtime_state import get_runtime_state
        s = get_runtime_state() or {}
        return json.dumps({
            "runtime": "AI-LAB Cognitive Runtime",
            "status": s.get("status", "unknown"),
            "active_node": s.get("active_node", "NO DISPONIBLE"),
            "mode": s.get("mode", "unknown"),
        }, ensure_ascii=False, default=str)
    except Exception:
        return '{"runtime": "AI-LAB", "status": "operational"}'


def is_report_request_heavy(text_or_payload: Any) -> bool:
    """FASE 26.1.2: Detecta informes tecnicos pesados que requieren qwen2.5-14b."""
    if isinstance(text_or_payload, dict):
        text = _last_user_text(text_or_payload)
    else:
        text = str(text_or_payload or "")
    t = text.lower()
    if not t:
        return False
    return any(k in t for k in (
        "informe técnico", "informe tecnico",
        "estructura general",
        "documento técnico", "documento tecnico",
        "detallado",
        "exhaustivo",
    ))


def is_report_request(text_or_payload: Any) -> bool:
    if isinstance(text_or_payload, dict):
        text = _last_user_text(text_or_payload)
    else:
        text = str(text_or_payload or "")

    t = text.lower()
    if not t:
        return False

    # FASE 34C: operational fast-path queries are NOT treated as report requests.
    # This prevents expensive grounding/report context construction for short NOC-like prompts.
    fp_intent = detect_operational_fastpath_intent(t)
    if fp_intent in {"governance", "validation", "observability", "watchdogs"} and len(t) <= 220:
        return False

    markers = (
        "informe",
        "resumen",
        "estado de ai-lab",
        "estado del ai-lab",
        "diagnóstico",
        "diagnostico",
        "auditoría",
        "auditoria",
        "reporte",
        "summary",
        "report",
        "status",
        "analysis",
        "analisis",
        "análisis",
        "audit",
    )
    return any(marker in t for marker in markers)


def strip_question_tool(payload: dict[str, Any], user_text: str | None = None) -> dict[str, Any]:
    if not is_report_request(user_text or payload):
        return payload

    tools = payload.get("tools")
    if not isinstance(tools, list):
        return payload

    filtered_tools: list[Any] = []
    for tool in tools:
        if not isinstance(tool, dict):
            filtered_tools.append(tool)
            continue
        fn = tool.get("function") if isinstance(tool.get("function"), dict) else {}
        name = str(fn.get("name") or tool.get("name") or "").strip().lower()
        if name == "question":
            continue
        filtered_tools.append(tool)

    payload = dict(payload)
    if filtered_tools:
        payload["tools"] = filtered_tools
    else:
        payload.pop("tools", None)

    choice = payload.get("tool_choice")
    if choice in {"question", "auto", "required"}:
        payload["tool_choice"] = "none"
    elif isinstance(choice, dict):
        fn = choice.get("function") if isinstance(choice.get("function"), dict) else {}
        if str(fn.get("name") or "").strip().lower() == "question":
            payload["tool_choice"] = "none"

    return payload


def is_greeting_request(payload: dict[str, Any]) -> bool:
    text = _last_user_text(payload).strip().lower()
    if not text:
        return False

    if text in _GREETING_MARKERS:
        return True

    tokens = re.findall(r"\b[\wáéíóúüñ]+\b", text, flags=re.IGNORECASE)
    if not tokens:
        return False

    greeting_words = {"hi", "hello", "hola", "hey", "buenas", "gracias", "thanks", "ok",
                      "adios", "bye", "vale", "genial", "perfecto", "claro", "entendido",
                      "si", "sí", "no", "yes", "yeah", "nope", "saludos", "chao", "listo",
                      "venga", "dale", "bien", "okey", "okay", "ya", "bueno", "excelente"}

    if len(tokens) <= 2 and tokens[0] in greeting_words:
        return True

    # FASE 29.3.1: detect single-token greetings/confirmations even if not in exact markers
    if len(tokens) == 1 and len(text) <= 15:
        return True

    return False


# ── FASE 29.3.1: Short prompt heuristic ──────────────────────

_SHORT_ARCHITECTURE_KEYWORDS = (
    "analiza", "debug", "implementa", "arquitectura", "refactoriza",
    "optimiza", "diseña", "diseña un", "corrige", "explica el codigo",
    "escribe una funcion", "escribe un script", "crea un", "desarrolla",
    "stacktrace", "traceback", "exception", "error en linea",
    "multi-file", "multi-paso", "refactor", "compile", "compila",
)

_LLAMA_SAFE_PATTERNS = (
    "que es", "qué es", "como funciona", "cómo funciona",
    "para que sirve", "para qué sirve", "definicion", "definición",
    "resume", "explica en", "dime", "cuentame", "cuéntame",
    "hola", "gracias", "adios",
)


def is_lightweight_prompt(text: str) -> bool:
    """FASE 29.3.1: Deterministic heuristic — true if prompt should use llama-3.1-8b."""
    t = text.strip().lower()
    if not t:
        return True

    # Short prompts (< 120 chars) without technical keywords → llama
    if len(t) < 120:
        # Check for code fences
        if "```" in t or "`" in t:
            return False
        # Check for architecture/coding keywords
        for kw in _SHORT_ARCHITECTURE_KEYWORDS:
            if kw in t:
                return False
        return True

    # Long prompts with only safe patterns → still llama
    safe_count = sum(1 for p in _LLAMA_SAFE_PATTERNS if p in t)
    arch_count = sum(1 for k in _SHORT_ARCHITECTURE_KEYWORDS if k in t)
    if safe_count > 0 and arch_count == 0 and "```" not in t:
        return True

    return False


# ── FASE 30I-C: GPU runtime intent detection ─────────────────────

GPU_RUNTIME_INTENT_PATTERNS = (
    "gpu",
    "rx9070",
    "rx7900xt", 
    "temperatura",
    "temperatura gpu",
    "vram",
    "vram usada",
    "vram libre",
    "potencia",
    "consumo",
    "consumo gpu",
    "fan",
    "fan rpm",
    "watts",
    "load gpu",
    "gpu load",
    "gpu state",
    "estado gpu",
    "estado de gpu",
)


# ── FASE 34C: operational fast-path intent detection ───────────────

_FASTPATH_INTENTS: dict[str, tuple[str, ...]] = {
    "runtime": (
        "runtime status", "estado runtime", "estado del runtime", "cluster status", "estado cluster",
        "topology", "topologia", "topología",
    ),
    "gpu": GPU_RUNTIME_INTENT_PATTERNS,
    "observability": (
        "observability", "observabilidad", "prometheus", "grafana", "loki",
        "exporters", "exporter", "targets", "scrape", "metricas", "métricas",
    ),
    "governance": (
        "governance", "gobernanza", "policy", "riesgos governance", "governance score",
        "dominios degradados", "degraded domains",
    ),
    "validation": (
        "validation", "validacion", "validación", "invariants", "safety gates",
        "pilot readiness",
    ),
    "watchdogs": (
        "watchdog", "watchdogs", "timeouts", "hardening", "escalation", "containment",
    ),
    "infrastructure": (
        "que es", "qué es", "who is", "what is",
        "infra", "infrastructure", "nodo", "node",
        "prometheus authority", "grafana", "control plane", "control-plane",
    ),
    "semantic": (
        "semantic", "sterilization", "esterilizacion", "hygiene", "higiene",
        "phantom", "legacy leakage", "contamination", "contaminacion",
    ),
}


def detect_operational_fastpath_intent(user_text: str) -> str | None:
    t = (user_text or "").lower().strip()
    if not t:
        return None
    # FASE 35A: direct IP identity queries.
    if re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", t) and any(k in t for k in ("que es", "qué es", "who is", "what is")):
        return "infrastructure"
    for intent, patterns in _FASTPATH_INTENTS.items():
        if any(p in t for p in patterns):
            return intent
    return None

def detect_gpu_runtime_intent(user_text: str) -> bool:
    """
    Detect if user is asking about GPU runtime status.
    Used to prioritize sensor fusion data over static inventory.
    """
    if not user_text:
        return False
    t = user_text.lower().strip()
    return any(pattern in t for pattern in GPU_RUNTIME_INTENT_PATTERNS)


def select_operational_response_profile(user_text: str) -> str:
    t = (user_text or "").lower().strip()
    if not t:
        return "operational_compact"
    if any(term in t for term in ("debug", "raw", "json", "detallado debug")):
        return "operational_debug"
    if any(term in t for term in ("detallado", "verbose", "completo", "exhaustivo")):
        return "operational_verbose"
    # FASE 34C: operational fast-path defaults to compact unless explicitly verbose.
    fp_intent = detect_operational_fastpath_intent(t)
    if len(t) <= 160 and fp_intent in {"governance", "validation", "observability", "watchdogs", "runtime", "gpu", "infrastructure"}:
        return "operational_compact"
    if len(t) <= 120 and (detect_gpu_runtime_intent(t) or detect_runtime_grounded_intent(t)):
        return "operational_compact"
    return "operational_verbose"


# ── FASE 29.3.1: Qwen escalation reasons ─────────────────────

QWEN_ESCALATION_REASONS = {
    "coding_explicit": "code fences, function writing, or explicit coding request",
    "architecture_deep": "multi-step analysis or architecture keywords",
    "debugging": "stacktrace, traceback, or error debugging",
    "long_context": "prompt > 500 chars with technical content",
    "multi_step": "multi-file or multi-paso indicators",
    "structured_output": "markdown table, JSON output, or structured generation",
    "creative_long": "long-form creative writing request",
    "reasoning_deep": "explicit reasoning or analisis profundo request",
    "report_technical": "technical report with structured sections required",
    "multi_gpu": "multi-gpu, rx7900xt, scheduler, failover, warm pool, queue arbitration, vram-aware routing, inference backend, gpu routing, placement",
    "architecture_scaling": "repartir cognitive/report/embeddings/minimal, distribuir cargas, escalado cognitivo, cognitive scaling, resource distribution",
}


_MULTI_GPU_TRIGGERS = (
    "multi-gpu", "rx7900xt", "scheduler", "distribuir cargas",
    "placement", "inference backend", "gpu routing", "failover",
    "warm pool", "queue arbitration", "vram-aware routing",
    "vram aware routing",
)

_ARCHITECTURE_SCALING_TRIGGERS = (
    "repartir cognitive/report/embeddings/minimal",
    "repartir cognitive", "distribuir cognitive",
    "escalado cognitivo", "cognitive scaling",
    "resource distribution",
)


def get_qwen_escalation_reason(text: str) -> str | None:
    """Returns the reason why qwen2.5-14b should be used, or None if llama is sufficient."""
    t = text.strip().lower()
    if not t:
        return None

    # FASE 30B.1: multi-GPU / scheduler / architecture scaling triggers
    if any(term in t for term in _MULTI_GPU_TRIGGERS):
        return "multi_gpu"
    if any(term in t for term in _ARCHITECTURE_SCALING_TRIGGERS):
        return "architecture_scaling"

    if "```" in t or "`" in t:
        return "coding_explicit"
    for kw in ("escribe una funcion", "escribe un script", "corrige este codigo",
               "debug", "stacktrace", "traceback", "exception in"):
        if kw in t:
            return "debugging" if any(k in t for k in ("debug", "stacktrace", "traceback", "exception")) else "coding_explicit"
    for kw in _SHORT_ARCHITECTURE_KEYWORDS:
        if kw in t:
            return "architecture_deep"
    if len(t) > 500:
        return "long_context"
    for kw in ("analiza", "razona", "compara", "evalua", "evalúa"):
        if kw in t and len(t) > 80:
            return "reasoning_deep"
    if any(kw in t for kw in ("informe", "report", "documentacion", "documentación")):
        return "report_technical"

    # Default: llama is sufficient
    return None


def is_casual_request(text_or_payload: Any) -> bool:
    if isinstance(text_or_payload, dict):
        text = _last_user_text(text_or_payload)
    else:
        text = str(text_or_payload or "")

    t = text.lower().strip()
    if not t:
        return False

    if t in _CASUAL_MARKERS:
        return True

    return any(marker in t for marker in _CASUAL_MARKERS)


def requires_full_context(payload: dict[str, Any]) -> bool:
    text = " ".join(
        str(part)
        for part in [
            payload.get("messages", []),
            payload.get("input", ""),
            payload.get("query", ""),
        ]
        if part
    ).lower()

    if len(text) > 2500:
        return True

    return any(marker in text for marker in _FULL_CONTEXT_MARKERS)


def should_use_tool_fastpath(payload: dict[str, Any]) -> bool:
    if not is_tool_request(payload):
        return False
    if _tool_choice_value(payload) == "none":
        return False
    return not requires_full_context(payload)


def should_use_greeting_fastpath(payload: dict[str, Any]) -> bool:
    return is_greeting_request(payload)


def tool_schema_signature(payload: dict[str, Any]) -> str:
    tools = payload.get("tools") or []
    tool_choice = payload.get("tool_choice", "none")
    canonical = json.dumps({"tools": tools, "tool_choice": tool_choice}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def summarize_tool_schema(payload: dict[str, Any]) -> str:
    signature = tool_schema_signature(payload)
    cached = _TOOL_SCHEMA_CACHE.get(signature)
    if cached is not None:
        return cached

    parts: list[str] = []
    tools = payload.get("tools") or []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        fn = tool.get("function") if isinstance(tool.get("function"), dict) else {}
        name = (fn.get("name") or tool.get("name") or "tool").strip()
        desc = (fn.get("description") or tool.get("description") or "").strip()
        parts.append(f"{name}: {desc}".strip())

    summary = "; ".join(parts) if parts else "(no tools provided)"
    _TOOL_SCHEMA_CACHE[signature] = summary
    return summary


def build_minimal_tool_messages(
    payload: dict[str, Any],
    *,
    selected_model: str,
    selected_node: str,
    routing_mode: str,
    reason_codes: list[str] | None,
    discovery_source: str | None,
    user_text: str,
) -> list[dict[str, str]]:
    hard_facts = {
        "mode": "tool_use",
        "selected_model": selected_model,
        "selected_node": selected_node,
        "routing_mode": routing_mode,
        "reason_codes": reason_codes or [],
        "discovery_source": discovery_source,
        "tool_schema_hash": tool_schema_signature(payload),
    }

    system_prompt = (
        "Eres el router tool-aware de AI-LAB.\n"
        "Modo TOOL_FASTPATH: contexto minimo, sin semantic recall, learning ni incidentes.\n"
        f"HARD FACTS MINIMOS: {json.dumps(hard_facts, ensure_ascii=False)}\n"
        f"TOOL SCHEMA: {summarize_tool_schema(payload)}\n"
        "Si necesitas usar una herramienta, emite tool_calls de forma estructurada.\n"
        "Responde en espanol y no inventes datos no presentes."
    )

    if is_report_request(user_text):
        system_prompt += (
            "\nPara informes, res\xFAmenes, diagn\xF3sticos o auditor\xEDas, no uses la herramienta question. "
            "Genera la respuesta con los datos disponibles y marca lo que falte como NO DISPONIBLE."
        )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]


def build_minimal_greeting_messages(user_text: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "Responde en espanol, muy breve y natural. "
                "No uses HARD_FACTS, no uses secciones y no inventes datos."
            ),
        },
        {"role": "user", "content": user_text},
    ]


REPORT_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "report_prompt.md"

_REPORT_PROMPT_CACHE: str | None = None


def _load_report_prompt() -> str:
    global _REPORT_PROMPT_CACHE
    if _REPORT_PROMPT_CACHE is not None:
        return _REPORT_PROMPT_CACHE
    try:
        if REPORT_PROMPT_PATH.exists():
            _REPORT_PROMPT_CACHE = REPORT_PROMPT_PATH.read_text(encoding="utf-8", errors="ignore").strip()
            if _REPORT_PROMPT_CACHE:
                return _REPORT_PROMPT_CACHE
    except Exception:
        pass
    _REPORT_PROMPT_CACHE = (
        "Responde en espanol, directo y util. "
        "Genera un informe breve en 5-8 lineas. "
        "Usa unicamente los datos disponibles en OBSERVED_RUNTIME o en el contexto proporcionado. "
        "No muestres bloques HARD_FACTS ni JSON al usuario. "
        "Si un dato no esta disponible, marca NO DISPONIBLE."
    )
    return _REPORT_PROMPT_CACHE


# ── FASE 30H.1: Universal Evidence Guard Detection ────────

_RUNTIME_INTENT_TRIGGERS = (
    "ai-lab", "ai lab",
    "runtime",
    "estado", "state",
    "informe", "report",
    "topology", "topología",
    "governance", "gobernanza",
    "modelos", "models",
    "rutas", "route family",
    "evidence", "evidencia",
    "observabilidad", "observability",
    "prometheus",
    "grafana",
    "gpu",
    "rx9070",
    "rx7900xt",
    "multi-gpu", "multigpu",
    "scheduler",
    "ailab",
    "kubernetes", "k8s",
    "docker", "contenedores",
    "latencia", "slo",
    "telemetry", "telemetría",
    "seguridad", "security",
    "infraestructura", "infrastructure",
)


def detect_runtime_grounded_intent(
    user_text: str,
    system_prompt: str = "",
) -> bool:
    """Returns True if the user text indicates runtime-state intent.

    Detects:
    - runtime-state keywords in user_text
    - OBSERVED_RUNTIME in system_prompt
    """
    if user_text:
        t = user_text.lower().strip()
        if any(trigger in t for trigger in _RUNTIME_INTENT_TRIGGERS):
            return True
    if "OBSERVED_RUNTIME" in system_prompt:
        return True
    return False


def should_apply_evidence_guard(
    payload: dict[str, Any],
    route_family: str,
    user_text: str,
    system_prompt: str = "",
) -> str | None:
    """Returns guard_scope if evidence guard should apply, None otherwise.

    Scope values:
    - report_route: route family is report/minimal with report variant
    - grounded_runtime: payload has _report_grounded or _report_runtime_context
    - runtime_intent: user text contains runtime-state triggers
    - observed_runtime: system_prompt contains OBSERVED_RUNTIME
    """
    # Direct flags from inject_agent_context
    if payload.get("_report_grounded") is True:
        return "grounded_runtime"
    if payload.get("_report_runtime_context"):
        return "grounded_runtime"

    # Route-based
    if route_family in ("report", "minimal"):
        return "report_route"

    # Runtime intent detection via standalone function
    if detect_runtime_grounded_intent(user_text, system_prompt):
        return "runtime_intent"

    return None


# ── FASE 30G: Operational Reporting Discipline ──────────────

FORBIDDEN_TOOL_RECOMMENDATIONS = {
    "datadog", "new relic", "sentry", "sumo logic",
    "splunk", "elastic", "kibana", "logstash",
    "pagerduty", "opsgenie", "victorops", "nagios",
    "zabbix", "monit", "uptimerobot", "statuscake",
    "pingdom", "appdynamics", "dynatrace",
    "instana", "signalfx", "wavefront",
}

_FORBIDDEN_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(rf"(?i)\b{re.escape(t)}\b"), t) for t in FORBIDDEN_TOOL_RECOMMENDATIONS
]


def sanitize_report_output(
    content: str,
    runtime_context_json: str | None = None,
) -> tuple[str, list[str]]:
    if not content:
        return "", []
    found_tools: list[str] = []
    for pattern, tool_name in _FORBIDDEN_PATTERNS:
        if pattern.search(content):
            found_tools.append(tool_name)
    if found_tools:
        unique_tools = sorted(set(found_tools))
        note = (
            "\n\n---\n"
            "[DISCIPLINA OPERACIONAL] El runtime de AI-LAB "
            "no incluye las herramientas externas mencionadas en esta seccion. "
            "Las referencias a herramientas no presentes en el stack activo "
            "no reflejan el entorno real observado."
        )
        content = content.rstrip() + note

    # FASE 30H: evidence guard — epistemologica discipline
    if runtime_context_json:
        try:
            from runtime.context.evidence_guard import sanitize_unverified_claims
            evidence = sanitize_unverified_claims(
                content,
                runtime_context_json=runtime_context_json,
            )
            if evidence.unverified_claims:
                content = evidence.sanitized_text
                found_tools.extend(evidence.unverified_claims)
        except ImportError:
            pass

    return content, found_tools


def build_minimal_report_messages(
    user_text: str,
    observed_runtime: str | None = None,
    response_profile: str = "operational_compact",
) -> list[dict[str, str]]:
    system_prompt = _load_report_prompt()
    if response_profile == "operational_compact":
        system_prompt += (
            "\n\nPara prompts operacionales cortos: usa formato compacto tipo NOC. "
            "Prioriza operational_state, freshness, confidence y source. "
            "No expliques conceptos basicos y evita parrafos largos."
        )
    elif response_profile == "operational_debug":
        system_prompt += (
            "\n\nPara prompts debug: muestra formato operacional pero conserva mas detalle diagnostico."
        )
    if observed_runtime:
        system_prompt += (
            f"\n\nOBSERVED_RUNTIME_BEGIN\n{observed_runtime}\nOBSERVED_RUNTIME_END"
        )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]


def classify_chat_route(
    payload: dict[str, Any],
    *,
    mode_name: str,
    user_text: str,
    request_text: str,
    is_report_request: bool,
    greeting_fastpath: bool,
    tool_fastpath: bool,
    intent_mode: str = "",
) -> RuntimeRoute:
    """Segment chat requests into explicit runtime families."""
    text = user_text or request_text

    # FASE 30B.1: qwen escalation check — runs BEFORE report/greeting/observe checks
    qwen_reason = get_qwen_escalation_reason(text)
    if qwen_reason in ("multi_gpu", "architecture_scaling", "report_technical", "reasoning_deep", "architecture_deep"):
        return RuntimeRoute(family="report", variant="qwen_escalated", reason=f"qwen_escalation:{qwen_reason}")

    if _is_reasoning_request(text):
        return RuntimeRoute(family="cognitive", variant="reasoning", reason="reasoning keywords")
    if is_report_request_heavy(text):
        return RuntimeRoute(family="report", variant="heavy", reason="heavy report request")
    if is_report_request:
        return RuntimeRoute(family="minimal", variant="report", reason="light report request")
    if _is_capability_question(text):
        return RuntimeRoute(family="minimal", variant="capability", reason="capability question")
    if is_creative_request(text):
        return RuntimeRoute(family="minimal", variant="creative", reason="creative writing")
    if is_casual_request(text):
        return RuntimeRoute(family="minimal", variant="casual", reason="casual request")
    if greeting_fastpath:
        return RuntimeRoute(family="minimal", variant="greeting", reason="greeting fastpath")
    if mode_name == "observe" or intent_mode == "observe":
        return RuntimeRoute(family="observe", variant="observe", reason="observe mode")
    if _is_reasoning_request(text):
        return RuntimeRoute(family="cognitive", variant="reasoning", reason="reasoning keywords")
    if tool_fastpath:
        return RuntimeRoute(family="tool_fastpath", variant="tool", reason="tool fastpath")
    if text.strip():
        return RuntimeRoute(family="cognitive", variant="default", reason="general cognitive routing")
    return RuntimeRoute(family="minimal", variant="empty", reason="empty input")


def classify_api_route(path: str) -> RuntimeRoute:
    """Segment internal API endpoints by runtime family."""
    if path.startswith("/api/learning/"):
        return RuntimeRoute(family="learning", variant=path.rsplit("/", 1)[-1], reason="learning api")
    if path.startswith("/api/control/"):
        return RuntimeRoute(family="cognitive", variant="control", reason="control plane")
    if path.startswith("/api/memory/") or path.startswith("/api/incidents/"):
        return RuntimeRoute(family="cognitive", variant="memory", reason="memory api")
    return RuntimeRoute(family="minimal", variant="default", reason="unclassified api")
