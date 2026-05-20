"""FASE 28.0.1 — Action Intent Layer.

Translates LLM responses into structured ACTION INTENTS.
The LLM generates intents (abstract goals), NEVER tool_calls or bash commands.
The planner later normalizes intents into real actions.

CRITICAL: This layer REJECTS direct tool_calls, bash commands, or arbitrary paths.
"""

from __future__ import annotations

import json
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Any


class RiskHint(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


KNOWN_INTENTS: dict[str, dict] = {
    "read_config": {
        "description": "Leer archivo de configuracion",
        "tools": ["read", "glob"],
        "risk": RiskHint.LOW,
        "path_required": True,
    },
    "read_state": {
        "description": "Leer estado del runtime",
        "tools": ["read", "grep"],
        "risk": RiskHint.LOW,
        "path_required": True,
    },
    "read_logs": {
        "description": "Leer logs del sistema",
        "tools": ["read", "grep"],
        "risk": RiskHint.LOW,
        "path_required": True,
    },
    "observe_runtime": {
        "description": "Consultar metricas y estado vivo",
        "tools": ["read", "grep", "bash"],
        "risk": RiskHint.LOW,
        "path_required": False,
    },
    "modify_config": {
        "description": "Modificar archivo de configuracion",
        "tools": ["read", "edit", "write", "bash"],
        "risk": RiskHint.MEDIUM,
        "path_required": True,
    },
    "create_file": {
        "description": "Crear nuevo archivo",
        "tools": ["write"],
        "risk": RiskHint.MEDIUM,
        "path_required": True,
    },
    "restart_service": {
        "description": "Reiniciar servicio systemd",
        "tools": ["bash"],
        "risk": RiskHint.HIGH,
        "path_required": False,
    },
    "install_package": {
        "description": "Instalar paquete del sistema",
        "tools": ["bash"],
        "risk": RiskHint.CRITICAL,
        "path_required": False,
    },
    "run_command": {
        "description": "Ejecutar comando shell generico",
        "tools": ["bash"],
        "risk": RiskHint.MEDIUM,
        "path_required": False,
    },
    "validate_syntax": {
        "description": "Validar sintaxis de archivo",
        "tools": ["read", "bash"],
        "risk": RiskHint.LOW,
        "path_required": True,
    },
    "check_gateway_health": {
        "description": "Verificar estado del gateway",
        "tools": ["read", "check"],
        "risk": RiskHint.LOW,
        "path_required": False,
    },
    "check_runtime_status": {
        "description": "Verificar estado general del runtime",
        "tools": ["read", "check"],
        "risk": RiskHint.LOW,
        "path_required": False,
    },
    "inspect_streams": {
        "description": "Inspeccionar estado de streams",
        "tools": ["read", "check"],
        "risk": RiskHint.LOW,
        "path_required": False,
    },
    "check_gpu_status": {
        "description": "Verificar estado de GPU",
        "tools": ["read", "check"],
        "risk": RiskHint.LOW,
        "path_required": False,
    },
    "analyze_timeouts": {
        "description": "Analizar timeouts y latencia",
        "tools": ["read"],
        "risk": RiskHint.LOW,
        "path_required": False,
    },
    "check_models": {
        "description": "Verificar modelos cargados",
        "tools": ["read", "check"],
        "risk": RiskHint.LOW,
        "path_required": False,
    },
    "inspect_slo_state": {
        "description": "Inspeccionar estado SLO",
        "tools": ["read"],
        "risk": RiskHint.LOW,
        "path_required": False,
    },
    "check_services": {
        "description": "Verificar servicios del sistema",
        "tools": ["check"],
        "risk": RiskHint.LOW,
        "path_required": False,
    },
}


FORBIDDEN_INTENT_PATTERNS: list[str] = [
    "rm -rf",
    "mkfs",
    "shutdown",
    "reboot",
    "dd if=",
    "chmod 777",
    "sudo",
    "delete_all",
    "format_disk",
    "kernel",
    "/dev/sda",
    "/etc/passwd",
    "/etc/shadow",
    "docker stop",
    "docker rm",
    "docker kill",
    "systemctl stop",
    "systemctl disable",
    "curl | bash",
    "curl | sh",
    "ignore previous",
    "override instructions",
    "planner",
    "self-modify",
    "self-heal",
]


@dataclass
class ActionIntent:
    intent_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    intent: str = ""
    goal: str = ""
    target: str = ""
    risk_hint: str = RiskHint.MEDIUM.value
    requested_by: str = "user"
    raw_llm_output: dict | None = None

    def validate(self) -> tuple[bool, list[str]]:
        errors: list[str] = []
        if self.intent not in KNOWN_INTENTS:
            errors.append(f"unknown_intent: {self.intent}")
        if not self.goal:
            errors.append("missing_goal")
        if len(self.goal) > 500:
            errors.append("goal_too_long")
        for pattern in FORBIDDEN_INTENT_PATTERNS:
            if pattern.lower() in self.goal.lower():
                errors.append(f"forbidden_pattern_in_goal: {pattern}")
            if pattern.lower() in self.target.lower():
                errors.append(f"forbidden_pattern_in_target: {pattern}")
        return len(errors) == 0, errors

    def to_dict(self) -> dict:
        return {
            "intent_id": self.intent_id,
            "intent": self.intent,
            "goal": self.goal,
            "target": self.target,
            "risk_hint": self.risk_hint,
            "requested_by": self.requested_by,
        }


class IntentParser:
    """Extracts and validates action intents from LLM responses."""

    @staticmethod
    def from_llm_response(content: str) -> list[ActionIntent]:
        """Parse LLM response text into validated ActionIntents.

        The LLM is prompted to return JSON with an 'intents' array.
        Each intent has: intent, goal, target, risk_hint.

        Falls back gracefully: if no JSON found, returns empty list.
        If JSON malformed, returns empty list.
        """
        intents: list[ActionIntent] = []

        content = content or ""
        json_str = IntentParser._extract_json(content)
        if not json_str:
            return intents

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return intents

        raw_intents = data.get("intents", [])
        if not isinstance(raw_intents, list):
            raw_intents = [raw_intents] if isinstance(raw_intents, dict) else []

        for raw in raw_intents:
            if not isinstance(raw, dict):
                continue
            intent = ActionIntent(
                intent=str(raw.get("intent", "")).strip(),
                goal=str(raw.get("goal", "")).strip(),
                target=str(raw.get("target", "")).strip(),
                risk_hint=str(raw.get("risk_hint", RiskHint.MEDIUM.value)).strip(),
                requested_by=str(raw.get("requested_by", "user")).strip(),
                raw_llm_output=raw,
            )

            valid, errors = intent.validate()
            if valid and intent.intent:
                intents.append(intent)

        return intents

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON block from text (handles markdown fences)."""
        if not text:
            return ""

        text = text.strip()

        # Try raw JSON first
        if text.startswith("{"):
            return text

        # Try markdown code fence ```json ... ```
        import re
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Try inline code `{...}`
        match = re.search(r"`(\{.*?\})`", text, re.DOTALL)
        if match:
            return match.group(1).strip()

        return ""

    @staticmethod
    def reject_direct_tool_calls(payload: dict) -> bool:
        """Returns True if the LLM tried to use direct tool_calls instead of intents."""
        tools = payload.get("tools")
        tool_choice = payload.get("tool_choice")
        if tools or tool_choice:
            return True
        messages = payload.get("messages", [])
        for msg in messages:
            if isinstance(msg, dict):
                if msg.get("tool_calls") or msg.get("tool_choice"):
                    return True
                content = msg.get("content", "")
                if isinstance(content, str):
                    if "<tool_call>" in content.lower():
                        return True
                    if "tool_calls" in content.lower() and '"function"' in content.lower():
                        return True
        return False
