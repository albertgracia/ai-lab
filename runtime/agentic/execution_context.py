from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExecutionMode(str, Enum):
    SIMULATION = "simulation"
    READONLY = "readonly"
    SANDBOX_WRITE = "sandbox_write"
    AUTONOMOUS = "autonomous"


CURRENT_EXECUTION_MODE = ExecutionMode.READONLY


class DryRunReason(str, Enum):
    FEATURE_FLAG = "feature_flag"
    GOVERNANCE_BLOCK = "governance_block"
    RISK_BLOCK = "risk_block"
    READONLY_PHASE = "readonly_phase"
    SANDBOX_DISABLED = "sandbox_disabled"


@dataclass
class RuntimeExecutionContext:
    execution_id: str = ""
    mode: ExecutionMode = ExecutionMode.READONLY
    phase: str = "28.2"
    dry_run: bool = True
    dry_run_reason: str | None = None
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_executable(self) -> bool:
        return not self.dry_run and self.mode in (ExecutionMode.READONLY, ExecutionMode.SANDBOX_WRITE)

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "mode": self.mode.value,
            "phase": self.phase,
            "dry_run": self.dry_run,
            "dry_run_reason": self.dry_run_reason,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }
