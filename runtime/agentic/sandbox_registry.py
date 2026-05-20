"""FASE 28.3 — Sandbox Operation Registry.

Catalogo de 11 operaciones sandbox con extensiones permitidas,
limites de tamaño, nivel de riesgo y governance obligatorio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from runtime.agentic.sandbox_fs import ALLOWED_EXTENSIONS, BLOCKED_EXTENSIONS


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MutationClass(str, Enum):
    CREATE = "create"
    APPEND = "append"
    REPLACE = "replace"
    TRANSFORM = "transform"
    GENERATE = "generate"
    ROLLBACK = "rollback"


@dataclass
class SandboxOperationSpec:
    name: str
    allowed_extensions: set[str] | None = None
    max_size_bytes: int = 1_048_576
    risk_level: RiskLevel = RiskLevel.LOW
    requires_governance: bool = False
    mutation_class: MutationClass = MutationClass.CREATE

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "allowed_extensions": list(self.allowed_extensions) if self.allowed_extensions else None,
            "max_size_bytes": self.max_size_bytes,
            "risk_level": self.risk_level.value,
            "requires_governance": self.requires_governance,
            "mutation_class": self.mutation_class.value,
        }


SANDBOX_OPERATIONS: dict[str, SandboxOperationSpec] = {
    "create_file": SandboxOperationSpec(
        name="create_file",
        allowed_extensions=ALLOWED_EXTENSIONS,
        max_size_bytes=1_048_576,
        risk_level=RiskLevel.MEDIUM,
        mutation_class=MutationClass.CREATE,
    ),
    "append_file": SandboxOperationSpec(
        name="append_file",
        allowed_extensions=ALLOWED_EXTENSIONS,
        max_size_bytes=1_048_576,
        risk_level=RiskLevel.MEDIUM,
        mutation_class=MutationClass.APPEND,
    ),
    "replace_file": SandboxOperationSpec(
        name="replace_file",
        allowed_extensions=ALLOWED_EXTENSIONS,
        max_size_bytes=1_048_576,
        risk_level=RiskLevel.MEDIUM,
        mutation_class=MutationClass.REPLACE,
    ),
    "create_directory": SandboxOperationSpec(
        name="create_directory",
        allowed_extensions=None,
        max_size_bytes=0,
        risk_level=RiskLevel.LOW,
        mutation_class=MutationClass.CREATE,
    ),
    "write_json": SandboxOperationSpec(
        name="write_json",
        allowed_extensions={".json"},
        max_size_bytes=2_097_152,
        risk_level=RiskLevel.LOW,
        mutation_class=MutationClass.GENERATE,
    ),
    "write_yaml": SandboxOperationSpec(
        name="write_yaml",
        allowed_extensions={".yaml", ".yml"},
        max_size_bytes=1_048_576,
        risk_level=RiskLevel.LOW,
        mutation_class=MutationClass.GENERATE,
    ),
    "write_markdown": SandboxOperationSpec(
        name="write_markdown",
        allowed_extensions={".md"},
        max_size_bytes=2_097_152,
        risk_level=RiskLevel.LOW,
        mutation_class=MutationClass.GENERATE,
    ),
    "generate_report": SandboxOperationSpec(
        name="generate_report",
        allowed_extensions={".md"},
        max_size_bytes=5_242_880,
        risk_level=RiskLevel.LOW,
        mutation_class=MutationClass.GENERATE,
    ),
    "generate_config": SandboxOperationSpec(
        name="generate_config",
        allowed_extensions={".json", ".yaml", ".yml", ".toml", ".ini"},
        max_size_bytes=524_288,
        risk_level=RiskLevel.LOW,
        mutation_class=MutationClass.GENERATE,
    ),
    "generate_script": SandboxOperationSpec(
        name="generate_script",
        allowed_extensions={".py", ".sh"},
        max_size_bytes=1_048_576,
        risk_level=RiskLevel.MEDIUM,
        requires_governance=True,
        mutation_class=MutationClass.GENERATE,
    ),
    "sandbox_transform": SandboxOperationSpec(
        name="sandbox_transform",
        allowed_extensions=None,
        max_size_bytes=5_242_880,
        risk_level=RiskLevel.LOW,
        mutation_class=MutationClass.TRANSFORM,
    ),
}

_INTENT_TO_OP: dict[str, str] = {
    "create_file": "create_file",
    "append_file": "append_file",
    "replace_file": "replace_file",
    "create_directory": "create_directory",
    "write_json": "write_json",
    "write_yaml": "write_yaml",
    "write_markdown": "write_markdown",
    "generate_report": "generate_report",
    "generate_config": "generate_config",
    "generate_script": "generate_script",
    "sandbox_transform": "sandbox_transform",
}

SANDBOX_WRITE_INTENTS = frozenset(_INTENT_TO_OP.keys())


@dataclass
class OperationVerdict:
    allowed: bool
    reason: str = ""
    spec: SandboxOperationSpec | None = None

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "spec": self.spec.to_dict() if self.spec else None,
        }


def is_allowed_operation(
    name: str,
    extension: str | None,
    size_bytes: int = 0,
) -> OperationVerdict:
    spec = SANDBOX_OPERATIONS.get(name)
    if spec is None:
        return OperationVerdict(False, f"unknown operation: {name}")

    if extension:
        ext_lower = extension.lower()
        if ext_lower in BLOCKED_EXTENSIONS:
            return OperationVerdict(False, f"blocked extension: {extension}")
        if spec.allowed_extensions and ext_lower not in spec.allowed_extensions:
            return OperationVerdict(False, f"extension {extension} not allowed for {name}")

    if spec.max_size_bytes > 0 and size_bytes > spec.max_size_bytes:
        return OperationVerdict(
            False,
            f"size {size_bytes} exceeds max {spec.max_size_bytes} for {name}",
        )

    return OperationVerdict(True, spec=spec)


def op_for_intent(intent: str) -> str | None:
    return _INTENT_TO_OP.get(intent)
