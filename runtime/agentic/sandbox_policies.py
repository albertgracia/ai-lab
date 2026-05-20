"""FASE 28.3 — Sandbox Governance Policies.

Governance sandbox-only: verifica intents, paths, symlinks,
traversal, extensiones, chmod prohibition, profundidad y fase.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from runtime.agentic.sandbox_fs import (
    SANDBOX_ROOTS,
    MAX_PATH_DEPTH,
    resolve_sandbox_path,
    is_within_sandbox,
    detect_symlink_escape,
    detect_path_traversal,
    check_path_depth,
    is_extension_allowed,
    is_extension_blocked,
)
from runtime.agentic.sandbox_registry import (
    SANDBOX_WRITE_INTENTS,
    op_for_intent,
    is_allowed_operation,
    RiskLevel,
)


CHMOD_PATTERNS = frozenset({
    "chmod +x", "chmod 755", "chmod 744", "chmod 777",
    "chmod a+x", "chmod u+x", "chmod 555", "chmod 111",
    "+x",
})


@dataclass
class SandboxGovernanceResult:
    allowed: bool
    reason: str = ""
    risk_level: str = "low"
    scope_check: str = "pass"

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "risk_level": self.risk_level,
            "scope_check": self.scope_check,
        }


def check_sandbox_governance(
    intent: str,
    target_path: str,
    phase: str,
    sandbox_root: str | None = None,
) -> SandboxGovernanceResult:
    if phase not in ("28.3", "28.4", "28.5", "28.6", "28.7", "28.8"):
        return SandboxGovernanceResult(
            allowed=False, reason=f"phase {phase} does not support sandbox write",
            risk_level="high", scope_check="unsupported_phase",
        )

    if intent not in SANDBOX_WRITE_INTENTS:
        return SandboxGovernanceResult(
            allowed=False, reason=f"intent '{intent}' is not a sandbox write operation",
            risk_level="medium", scope_check="intent_not_sandbox_write",
        )

    op_name = op_for_intent(intent)
    if op_name is None:
        return SandboxGovernanceResult(
            allowed=False, reason=f"no operation registered for intent '{intent}'",
            risk_level="high", scope_check="no_operation_registered",
        )

    if detect_path_traversal(target_path):
        return SandboxGovernanceResult(
            allowed=False, reason="path traversal detected",
            risk_level="high", scope_check="path_traversal_detected",
        )

    if not check_path_depth(target_path, MAX_PATH_DEPTH):
        return SandboxGovernanceResult(
            allowed=False, reason=f"path depth exceeds max {MAX_PATH_DEPTH}",
            risk_level="medium", scope_check="path_depth_exceeded",
        )

    ext = os.path.splitext(target_path)[1].lower()
    if ext and is_extension_blocked(ext):
        return SandboxGovernanceResult(
            allowed=False, reason=f"blocked extension: {ext}",
            risk_level="high", scope_check="blocked_extension",
        )

    if sandbox_root:
        resolved = resolve_sandbox_path(target_path, sandbox_root)
        if not is_within_sandbox(resolved, [sandbox_root]):
            return SandboxGovernanceResult(
                allowed=False, reason="target path outside sandbox boundary",
                risk_level="high", scope_check="outside_sandbox_boundary",
            )

        if detect_symlink_escape(resolved, sandbox_root):
            return SandboxGovernanceResult(
                allowed=False, reason="symlink escape detected",
                risk_level="high", scope_check="symlink_escape_detected",
            )

    op_verdict = is_allowed_operation(op_name, ext)
    if not op_verdict.allowed:
        return SandboxGovernanceResult(
            allowed=False, reason=op_verdict.reason,
            risk_level="medium", scope_check="operation_not_allowed",
        )

    return SandboxGovernanceResult(
        allowed=True,
        risk_level=op_verdict.spec.risk_level.value if op_verdict.spec else "low",
        scope_check="governance_passed",
    )


def assess_sandbox_risk(intent: str, target_path: str) -> str:
    if intent == "generate_script":
        return RiskLevel.MEDIUM.value
    ext = os.path.splitext(target_path)[1].lower()
    if ext in (".py", ".sh"):
        return RiskLevel.MEDIUM.value
    if intent in ("create_file", "append_file", "replace_file"):
        return RiskLevel.MEDIUM.value
    return RiskLevel.LOW.value


def detect_chmod_intent(description: str) -> bool:
    desc_lower = description.lower()
    for pattern in CHMOD_PATTERNS:
        if pattern in desc_lower:
            return True
    return False


FORBIDDEN_SYSTEM_PATTERNS = frozenset({
    "chown", "sudo", "systemctl", "docker exec",
})


def detect_forbidden_operation(description: str) -> bool:
    if detect_chmod_intent(description):
        return True
    desc_lower = description.lower()
    for pattern in FORBIDDEN_SYSTEM_PATTERNS:
        if pattern in desc_lower:
            return True
    return False


def check_sandbox_scope(target_path: str, allowed_scopes: set[str]) -> bool:
    for root in SANDBOX_ROOTS:
        if target_path.startswith(root):
            return "workspace_write_reserved" in allowed_scopes
    return "readonly" in allowed_scopes
