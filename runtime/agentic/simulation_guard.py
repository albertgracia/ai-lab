"""FASE 28.0.11 — Simulation-Only Guards.

CRITICAL: This module prevents ANY real execution during FASE 28.0.

When AGENTIC_EXECUTION_ENABLED=false (the default and ONLY allowed value):
  - All execution is simulated
  - No real bash, subprocess, file writes, or service restarts
  - Any attempt at real execution is blocked and logged

This guard sits between the agentic pipeline and the real system.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


FEATURE_FLAG = "AGENTIC_EXECUTION_ENABLED"

BLOCKED_COMMANDS: list[str] = [
    "rm",
    "rmdir",
    "shutdown",
    "reboot",
    "systemctl",
    "docker",
    "mkfs",
    "dd",
    "chmod",
    "chown",
    "sudo",
    "su",
    "apt",
    "apt-get",
    "pip install",
    "pip3 install",
    "kill",
    "killall",
    "pkill",
]

BLOCKED_PATHS: list[str] = [
    "/etc/",
    "/home/",
    "/opt/ai-lab/runtime/gateway/",
    "/opt/ai-lab/runtime/llm/",
    "/opt/ai-lab/.venv/bin/",
    "/dev/",
    "/proc/",
    "/sys/",
]

BLOCKED_TOOLS_IN_SIMULATION: list[str] = [
    "write",
    "edit",
    "bash",
    "task",
]


@dataclass
class SimulationGuardResult:
    execution_allowed: bool = False
    execution_mode: str = "simulation_only"
    reason: str = ""
    blocked_command: str = ""
    blocked_path: str = ""

    def to_dict(self) -> dict:
        return {
            "execution_allowed": self.execution_allowed,
            "execution_mode": self.execution_mode,
            "reason": self.reason,
            "blocked_command": self.blocked_command,
            "blocked_path": self.blocked_path,
        }


class SimulationGuard:
    """Global safety guard for the agentic runtime."""

    _checked_any_real: bool = False
    _blocked_attempts: int = 0

    @staticmethod
    def is_simulation_only() -> bool:
        """Returns True if we're in simulation-only mode (always during FASE 28.0)."""
        value = os.environ.get(FEATURE_FLAG, "false").lower()
        if value in ("true", "1", "yes"):
            SimulationGuard._checked_any_real = True
            return False
        return True

    @staticmethod
    def check_action(action_tool: str, action_target: str = "", action_command: str = "") -> SimulationGuardResult:
        """Check if an action is allowed to execute for real."""

        # In simulation mode, block write/bash/task tools
        if SimulationGuard.is_simulation_only():
            if action_tool in BLOCKED_TOOLS_IN_SIMULATION:
                SimulationGuard._blocked_attempts += 1
                return SimulationGuardResult(
                    execution_allowed=False,
                    execution_mode="simulation_only",
                    reason=f"Tool '{action_tool}' blocked in simulation mode",
                )

        # Always block forbidden commands
        cmd = (action_command or "").lower()
        for blocked in BLOCKED_COMMANDS:
            if blocked in cmd.split():
                SimulationGuard._blocked_attempts += 1
                return SimulationGuardResult(
                    execution_allowed=False,
                    execution_mode="simulation_only",
                    reason=f"Command contains blocked token: {blocked}",
                    blocked_command=blocked,
                )

        # Always block forbidden paths
        target = action_target or ""
        for blocked in BLOCKED_PATHS:
            if blocked in target:
                SimulationGuard._blocked_attempts += 1
                return SimulationGuardResult(
                    execution_allowed=False,
                    execution_mode="simulation_only",
                    reason=f"Path matches blocked pattern: {blocked}",
                    blocked_path=blocked,
                )

        # In simulation mode, never allow real execution
        if SimulationGuard.is_simulation_only():
            if action_tool in ("write", "edit", "bash", "task"):
                return SimulationGuardResult(
                    execution_allowed=False,
                    execution_mode="simulation_only",
                    reason="Simulation mode: no real execution permitted",
                )

        # Read-only tools are always allowed (they don't modify the system)
        if action_tool in ("read", "glob", "grep"):
            return SimulationGuardResult(
                execution_allowed=True,
                execution_mode=EXECUTION_MODE,
                reason="Read-only tool, always safe",
            )

        return SimulationGuardResult(
            execution_allowed=False,
            execution_mode="simulation_only",
            reason="Simulation mode active",
        )

    @staticmethod
    def get_stats() -> dict:
        return {
            "simulation_only": SimulationGuard.is_simulation_only(),
            "checked_any_real": SimulationGuard._checked_any_real,
            "blocked_attempts": SimulationGuard._blocked_attempts,
            "blocked_tools": BLOCKED_TOOLS_IN_SIMULATION,
            "blocked_commands": BLOCKED_COMMANDS[:5],
            "blocked_paths": BLOCKED_PATHS[:5],
        }


EXECUTION_MODE = "simulation_only"
