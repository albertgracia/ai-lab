"""Tool request detection and fastpath helpers."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
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
    "hola",
    "hello",
    "hi",
    "buenas",
    "buenos dias",
    "buenas tardes",
    "buenas noches",
    "hey",
    "gracias",
    "thanks",
    "ok",
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


def is_report_request(text_or_payload: Any) -> bool:
    if isinstance(text_or_payload, dict):
        text = _last_user_text(text_or_payload)
    else:
        text = str(text_or_payload or "")

    t = text.lower()
    if not t:
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

    greeting_words = {"hi", "hello", "hola", "hey", "buenas", "gracias", "thanks", "ok"}

    if len(tokens) <= 2 and tokens[0] in greeting_words:
        return True

    return False


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


def build_minimal_report_messages(user_text: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "Responde en espanol, directo y util. "
                "Genera un informe breve en 5-8 lineas. "
                "No uses HARD_FACTS, no uses herramientas y no inventes datos. "
                "Si falta algo, marca NO DISPONIBLE."
            ),
        },
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

    if is_report_request:
        return RuntimeRoute(family="minimal", variant="report", reason="report request")
    if is_casual_request(text):
        return RuntimeRoute(family="minimal", variant="casual", reason="casual request")
    if greeting_fastpath:
        return RuntimeRoute(family="minimal", variant="greeting", reason="greeting fastpath")
    if mode_name == "observe" or intent_mode == "observe":
        return RuntimeRoute(family="observe", variant="observe", reason="observe mode")
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
