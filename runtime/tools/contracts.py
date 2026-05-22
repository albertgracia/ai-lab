from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any


TOOL_CONTRACT_VERSION = "28.4"


@dataclass
class ToolArtifactContract:
    artifact_type: str
    paths: list[str] = field(default_factory=list)
    lifecycle: str = "historical"  # active|historical|stale|archived|protected|gc_candidate|deprecated
    protected: bool = False
    retention_days: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ToolAuthorityContract:
    authority: str
    authority_domain: str
    source_of_truth: str
    confidence: str = "unknown"
    explainable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ToolSafetyContract:
    safe_to_execute: bool
    safe_to_delete: bool = False
    safe_to_archive: bool = False
    safe_to_rotate: bool = False
    safe_to_expire: bool = False
    deterministic: bool = True
    explainable: bool = True
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ToolLifecycleContract:
    execution_state: str  # enabled|disabled|dry_run|unknown
    lifecycle: str  # active|historical|stale|archived|protected|gc_candidate|deprecated
    created_at: float = field(default_factory=time.time)
    last_used_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ToolExecutionContract:
    tool_id: str
    tool_type: str
    contract_version: str = TOOL_CONTRACT_VERSION
    deterministic: bool = True
    max_duration_seconds: int = 30
    produces_artifacts: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ToolContract:
    tool_id: str
    tool_type: str
    authority: ToolAuthorityContract
    execution: ToolExecutionContract
    lifecycle: ToolLifecycleContract
    safety: ToolSafetyContract
    artifacts: list[ToolArtifactContract] = field(default_factory=list)
    artifact_policy: str = "none"
    deterministic: bool = True

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Expand nested contracts deterministically
        d["authority"] = self.authority.to_dict()
        d["execution"] = self.execution.to_dict()
        d["lifecycle"] = self.lifecycle.to_dict()
        d["safety"] = self.safety.to_dict()
        d["artifacts"] = [a.to_dict() for a in self.artifacts]
        return d


@dataclass
class ToolGovernanceContract:
    tool_governance_score: float
    invalid_tool_contracts_total: int
    orphan_tools_total: int
    deterministic: bool = True
    explainable: bool = True
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
