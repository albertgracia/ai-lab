"""FASE 28.3 — Mutation Execution Context.

Extiende RuntimeExecutionContext para operaciones sandbox write.
Incluye MutationClass, budget counters y dry_run_only_write flag.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from runtime.agentic.execution_context import (
    RuntimeExecutionContext,
    ExecutionMode,
    CURRENT_EXECUTION_MODE,
)
from runtime.agentic.sandbox_registry import MutationClass


@dataclass
class MutationExecutionContext(RuntimeExecutionContext):
    sandbox_root: str = "/tmp/opencode/sandbox/"
    mutation_class: MutationClass | None = None
    mutation_type: str = ""
    dry_run_only_write: bool = True
    current_workflow_artifacts: int = 0
    current_workflow_bytes: int = 0

    def __post_init__(self) -> None:
        if not self.mode:
            self.mode = CURRENT_EXECUTION_MODE
        self.phase = "28.3"

    def is_executable(self) -> bool:
        if self.dry_run:
            return False
        return self.mode in (ExecutionMode.READONLY, ExecutionMode.SANDBOX_WRITE)

    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({
            "sandbox_root": self.sandbox_root,
            "mutation_class": self.mutation_class.value if self.mutation_class else None,
            "mutation_type": self.mutation_type,
            "dry_run_only_write": self.dry_run_only_write,
            "current_workflow_artifacts": self.current_workflow_artifacts,
            "current_workflow_bytes": self.current_workflow_bytes,
        })
        return base
