"""FASE 28.3 — Permission Scopes.

Define los scopes de permiso que un plan puede requerir.
FASE 28.3 habilita 'workspace_write_reserved' para sandbox write.
Los demas son reservados para fases futuras.
"""

from __future__ import annotations

from enum import Enum


class PermissionScope(str, Enum):
    READONLY = "readonly"
    WORKSPACE_WRITE_RESERVED = "workspace_write_reserved"
    RUNTIME_WRITE_RESERVED = "runtime_write_reserved"
    PRIVILEGED_RESERVED = "privileged_reserved"
    FORBIDDEN = "forbidden"


SCOPE_HIERARCHY: list[PermissionScope] = [
    PermissionScope.READONLY,
    PermissionScope.WORKSPACE_WRITE_RESERVED,
    PermissionScope.RUNTIME_WRITE_RESERVED,
    PermissionScope.PRIVILEGED_RESERVED,
    PermissionScope.FORBIDDEN,
]

_CURRENT_PHASE = "28.3"

_SCOPE_ALLOWED_IN_PHASE: dict[str, set[str]] = {
    "28.1": {"readonly"},
    "28.2": {"readonly"},
    "28.3": {"readonly", "workspace_write_reserved"},
    "28.4": {"readonly"},
    "28.5": {"readonly", "workspace_write_reserved"},
    "28.6": {"readonly", "workspace_write_reserved", "runtime_write_reserved"},
    "28.7": {"readonly", "workspace_write_reserved", "runtime_write_reserved", "privileged_reserved"},
    "28.8": {"readonly", "workspace_write_reserved", "runtime_write_reserved", "privileged_reserved"},
}

_SANDBOX_WRITE_INTENTS = {
    "create_file", "append_file", "replace_file", "create_directory",
    "write_json", "write_yaml", "write_markdown",
    "generate_report", "generate_config", "generate_script",
    "sandbox_transform",
}

_READONLY_INTENTS = {
    "read_config", "read_state", "read_logs", "observe_runtime",
    "validate_syntax",
    "check_gateway_health", "check_runtime_status", "inspect_streams",
    "check_gpu_status", "analyze_timeouts", "check_models",
    "inspect_slo_state", "check_services",
}

_FORBIDDEN_INTENTS = {
    "restart_service", "install_package", "run_command",
    "modify_config",
}

_READ_TOOLS = {"read", "glob", "grep", "check", "list", "inspect"}

_WRITE_TOOLS = {"write", "edit", "bash", "task"}


def classify_permission_scope(intent: str, tool: str, target: str = "") -> PermissionScope:
    if intent in _FORBIDDEN_INTENTS:
        return PermissionScope.FORBIDDEN
    if intent in _SANDBOX_WRITE_INTENTS:
        return PermissionScope.WORKSPACE_WRITE_RESERVED
    if intent in _READONLY_INTENTS and tool in _READ_TOOLS:
        return PermissionScope.READONLY
    if tool in _WRITE_TOOLS:
        return PermissionScope.FORBIDDEN
    if intent in _READONLY_INTENTS:
        return PermissionScope.READONLY
    return PermissionScope.READONLY


def is_scope_allowed_in_phase(scope: PermissionScope, phase: str = _CURRENT_PHASE) -> bool:
    allowed = _SCOPE_ALLOWED_IN_PHASE.get(phase, {"readonly"})
    return scope.value in allowed
