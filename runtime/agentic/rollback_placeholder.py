from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from runtime.agentic.planner import AgenticPlan


@dataclass
class RollbackResult:
    success: bool = False
    reason: str = "not_implemented"
    steps_rolled_back: int = 0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "reason": self.reason,
            "steps_rolled_back": self.steps_rolled_back,
            "details": self.details,
        }


class RollbackPlaceholder:
    @staticmethod
    def rollback(plan: AgenticPlan) -> RollbackResult:
        return RollbackResult(
            success=False,
            reason="rollback_not_implemented_before_FASE_28.3",
        )
