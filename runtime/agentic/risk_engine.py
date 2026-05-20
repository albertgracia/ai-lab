"""FASE 28.0.3 — Deterministic Risk Engine.

RISK IS ALWAYS DECIDED BY THE RUNTIME, NEVER BY THE LLM.

Uses fixed rules across 4 dimensions:
  1. Intent type (e.g., read_config=LOW, restart_service=HIGH)
  2. Tool used (e.g., read=LOW, bash=MEDIUM, edit=MEDIUM)
  3. Target path (e.g., /etc/=CRITICAL, /opt/ai-lab/config/=LOW)
  4. Bash tokens (e.g., cat=LOW, systemctl=HIGH, apt=CRITICAL)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

from runtime.agentic.planner import WorkflowAction, AgenticPlan


class RiskLevel(IntEnum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3

    @property
    def label(self) -> str:
        return self.name


RISK_RULES: dict[str, dict[str, RiskLevel]] = {
    "intent": {
        "read_config": RiskLevel.LOW,
        "read_state": RiskLevel.LOW,
        "read_logs": RiskLevel.LOW,
        "observe_runtime": RiskLevel.LOW,
        "validate_syntax": RiskLevel.LOW,
        "modify_config": RiskLevel.MEDIUM,
        "create_file": RiskLevel.MEDIUM,
        "run_command": RiskLevel.MEDIUM,
        "restart_service": RiskLevel.HIGH,
        "install_package": RiskLevel.CRITICAL,
    },
    "tool": {
        "read": RiskLevel.LOW,
        "glob": RiskLevel.LOW,
        "grep": RiskLevel.LOW,
        "write": RiskLevel.MEDIUM,
        "edit": RiskLevel.MEDIUM,
        "bash": RiskLevel.MEDIUM,
    },
    "path": {
        "/etc/": RiskLevel.CRITICAL,
        "/home/": RiskLevel.HIGH,
        "/opt/ai-lab/runtime/gateway/": RiskLevel.CRITICAL,
        "/opt/ai-lab/runtime/llm/": RiskLevel.CRITICAL,
        "/opt/ai-lab/.venv/": RiskLevel.HIGH,
        "/opt/ai-lab/config/": RiskLevel.LOW,
        "/opt/ai-lab/runtime/prompts/": RiskLevel.LOW,
        "/opt/ai-lab/runtime/profiles/": RiskLevel.LOW,
        "/opt/ai-lab/runtime/policies/": RiskLevel.LOW,
        "/opt/ai-lab/runtime/state/": RiskLevel.LOW,
        "/opt/ai-lab/apps/ialab-docs/": RiskLevel.LOW,
        "/tmp/opencode/": RiskLevel.LOW,
    },
    "bash_token": {
        "cat": RiskLevel.LOW,
        "ls": RiskLevel.LOW,
        "head": RiskLevel.LOW,
        "tail": RiskLevel.LOW,
        "grep": RiskLevel.LOW,
        "find": RiskLevel.LOW,
        "wc": RiskLevel.LOW,
        "echo": RiskLevel.LOW,
        "mkdir": RiskLevel.LOW,
        "cp": RiskLevel.MEDIUM,
        "mv": RiskLevel.MEDIUM,
        "rm": RiskLevel.HIGH,
        "chmod": RiskLevel.HIGH,
        "chown": RiskLevel.HIGH,
        "systemctl": RiskLevel.HIGH,
        "apt": RiskLevel.CRITICAL,
        "pip": RiskLevel.CRITICAL,
        "curl": RiskLevel.MEDIUM,
        "wget": RiskLevel.MEDIUM,
        "shutdown": RiskLevel.CRITICAL,
        "reboot": RiskLevel.CRITICAL,
        "mkfs": RiskLevel.CRITICAL,
        "dd": RiskLevel.CRITICAL,
        "sudo": RiskLevel.CRITICAL,
    },
}

FORBIDDEN_TOOLS: set[str] = {
    "rm -rf", "mkfs", "shutdown", "reboot", "dd if=",
    "chmod 777", "> /dev/sda", "sudo rm", "sudo shutdown",
    "sudo reboot", ":(){ :|:& };:", "shell_exec", "sudo", "kernel_write",
}


@dataclass
class RiskAssessment:
    overall_risk: str = RiskLevel.LOW.label
    risk_score: int = 0
    risk_reasons: list[str] = field(default_factory=list)
    per_action: list[dict] = field(default_factory=list)
    requires_approval: bool = False
    approval_type: str = ""
    forbidden_actions: list[str] = field(default_factory=list)
    blocked: bool = False


class RiskEngine:
    """Deterministic risk scoring with fixed rules."""

    @staticmethod
    def assess(plan: AgenticPlan) -> RiskAssessment:
        risks: list[RiskLevel] = []
        reasons: list[str] = []
        per_action: list[dict] = []
        forbidden: list[str] = []

        for action in plan.actions:
            action_risks: list[RiskLevel] = []
            action_reasons: list[str] = []

            # 1. Intent-based risk
            intent_risk = RISK_RULES["intent"].get(action.intent, RiskLevel.MEDIUM)
            action_risks.append(intent_risk)

            # 2. Tool-based risk
            tool_risk = RISK_RULES["tool"].get(action.tool, RiskLevel.MEDIUM)
            action_risks.append(tool_risk)

            # 3. Path-based risk
            target = action.target or ""
            for path_pattern, path_risk in RISK_RULES["path"].items():
                if path_pattern in target:
                    action_risks.append(path_risk)
                    action_reasons.append(f"path_match:{path_pattern}")

            # 4. Bash token risk
            if action.tool == "bash" and action.command:
                cmd = action.command.lower()
                for token, token_risk in RISK_RULES["bash_token"].items():
                    if token in cmd.split():
                        action_risks.append(token_risk)
                        action_reasons.append(f"bash_token:{token}")

            # 5. Forbidden tools check
            cmd = action.command or ""
            for fb in FORBIDDEN_TOOLS:
                if fb.lower() in cmd.lower():
                    action_reasons.append(f"forbidden_tool:{fb}")
                    if action.action_id not in forbidden:
                        forbidden.append(action.action_id)

            action_risk = max(action_risks) if action_risks else RiskLevel.LOW
            risks.append(action_risk)
            reasons.extend(action_reasons)

            per_action.append({
                "action_id": action.action_id,
                "step": action.step,
                "intent": action.intent,
                "tool": action.tool,
                "risk": action_risk.label,
                "reasons": action_reasons,
            })

        # Overall risk = max of all action risks
        overall = max(risks) if risks else RiskLevel.LOW

        # Bump if many actions
        if len(plan.actions) > 5:
            overall = max(overall, RiskLevel.MEDIUM)
            reasons.append("action_count>5")

        # Determine approval requirements
        requires_approval = overall >= RiskLevel.MEDIUM
        approval_type = RiskEngine._approval_type(overall)

        # Check for forbidden
        for action in plan.actions:
            cmd = (action.command or "").lower()
            for fb in FORBIDDEN_TOOLS:
                if fb.lower() in cmd:
                    forbidden.append(action.action_id)

        blocked = len(forbidden) > 0

        return RiskAssessment(
            overall_risk=overall.label,
            risk_score=int(overall),
            risk_reasons=list(dict.fromkeys(reasons)),
            per_action=per_action,
            requires_approval=requires_approval,
            approval_type=approval_type,
            forbidden_actions=forbidden,
            blocked=blocked,
        )

    @staticmethod
    def _approval_type(risk: RiskLevel) -> str:
        if risk >= RiskLevel.CRITICAL:
            return "privileged"
        if risk >= RiskLevel.HIGH:
            return "runtime_write"
        if risk >= RiskLevel.MEDIUM:
            return "workspace_write"
        return "none"
