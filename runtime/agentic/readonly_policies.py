from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GovernanceResult:
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


def check_governance(intent: str, command: str, phase: str) -> GovernanceResult:
    if phase != "28.2":
        return GovernanceResult(allowed=False, reason=f"phase {phase} not supported")

    if intent == "restart_service":
        return GovernanceResult(
            allowed=False, reason="restart_service blocked in readonly phase",
            risk_level="high", scope_check="blocked_by_readonly_phase",
        )

    if intent == "install_package":
        return GovernanceResult(
            allowed=False, reason="install_package blocked in readonly phase",
            risk_level="high", scope_check="blocked_by_readonly_phase",
        )

    if intent == "run_command":
        from runtime.agentic.safe_runner import validate_command
        valid, reason = validate_command(command)
        if not valid:
            return GovernanceResult(
                allowed=False, reason=reason,
                risk_level="medium", scope_check="command_validation_failed",
            )
        return GovernanceResult(allowed=True, scope_check="command_validated")

    return GovernanceResult(allowed=True, scope_check="no_governance_check")


def assess_risk(intent: str, tool: str, target: str) -> str:
    if tool == "bash" and intent in ("restart_service", "install_package", "modify_config"):
        return "high"
    if tool in ("bash", "write", "edit"):
        return "medium"
    return "low"


def check_scope(target: str, allowed_scopes: set[str]) -> bool:
    if "/opt/ai-lab" in target:
        return "filesystem" in allowed_scopes
    if target.startswith("http://") or target.startswith("https://"):
        return "network" in allowed_scopes
    return "system" in allowed_scopes
