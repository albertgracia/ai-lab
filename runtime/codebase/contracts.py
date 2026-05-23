from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any


CODEBASE_CONTRACT_VERSION = "DEV-36X"

GITNEXUS_CONFIG_PATH = os.environ.get("AI_LAB_GITNEXUS_PATH", "/opt/ai-lab/.gitnexus")
GITNEXUS_META_PATH = os.path.join(GITNEXUS_CONFIG_PATH, "meta.json")

RUNTIME_ROOT = os.environ.get("AI_LAB_RUNTIME_ROOT", "/opt/ai-lab/runtime")

OWNERSHIP_DOMAINS: dict[str, list[str]] = {
    "authority": ["runtime/authority"],
    "governance": ["runtime/governance"],
    "validation": ["runtime/validation"],
    "observability": ["runtime/observability"],
    "fastpath": ["runtime/fastpath"],
    "incidents": ["runtime/incidents"],
    "infrastructure": ["runtime/infrastructure"],
    "semantic": ["runtime/semantic"],
    "gateway": ["runtime/gateway"],
    "reporting": ["runtime/reporting"],
    "telemetry": ["runtime/telemetry"],
    "performance": ["runtime/performance"],
    "context": ["runtime/context"],
    "topology": ["runtime/topology"],
    "entities": ["runtime/entities"],
    "memory": ["runtime/memory"],
    "codebase": ["runtime/codebase"],
    "policies": ["runtime/policies"],
    "control": ["runtime/control"],
    "health": ["runtime/health"],
    "tools": ["runtime/tools"],
    "state": ["runtime/state"],
    "slo": ["runtime/slo"],
    "replay": ["runtime/replay"],
    "llm": ["runtime/llm"],
}

EXCLUDED_DIRS = {"__pycache__", ".git", "__init__.py"}


def _hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _now() -> float:
    strict = os.environ.get("STRICT_VALIDATION_MODE", "false").lower() in ("true", "1", "yes")
    return 0.0 if strict else time.time()


def _strict_mode() -> bool:
    return os.environ.get("STRICT_VALIDATION_MODE", "false").lower() in ("true", "1", "yes")


@dataclass(frozen=True)
class CodebaseModule:
    path: str
    module_name: str
    domain: str
    file_count: int
    import_edges: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "module_name": self.module_name,
            "domain": self.domain,
            "file_count": self.file_count,
            "import_edges": sorted(self.import_edges or []),
        }


@dataclass(frozen=True)
class DependencyEdge:
    source: str
    target: str
    edge_type: str

    def to_dict(self) -> dict[str, str]:
        return {"source": self.source, "target": self.target, "edge_type": self.edge_type}


@dataclass(frozen=True)
class OwnershipEntry:
    domain: str
    paths: list[str]
    file_count: int

    def to_dict(self) -> dict[str, Any]:
        return {"domain": self.domain, "paths": sorted(self.paths), "file_count": self.file_count}


@dataclass(frozen=True)
class BlastRadiusResult:
    module_path: str
    affected_domains: list[str]
    affected_modules: list[str]
    total_impacted: int
    severity: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "module_path": self.module_path,
            "affected_domains": sorted(self.affected_domains),
            "affected_modules": sorted(self.affected_modules),
            "total_impacted": self.total_impacted,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class StructuralRisk:
    risk_type: str
    domain: str
    description: str
    severity: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_type": self.risk_type,
            "domain": self.domain,
            "description": self.description,
            "severity": self.severity,
            "details": dict(self.details or {}),
        }


@dataclass(frozen=True)
class CodebaseMemory:
    contract_version: str
    modules: list[dict[str, Any]]
    dependency_edges: list[dict[str, str]]
    ownership: list[dict[str, Any]]
    blast_radius: list[dict[str, Any]]
    structural_risks: list[dict[str, Any]]
    summary: dict[str, Any]
    score: dict[str, Any]
    determinant_signature: str
    freshness: dict[str, Any]
    gitnexus_stats: dict[str, Any]
    generated_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "modules": list(self.modules or []),
            "dependency_edges": list(self.dependency_edges or []),
            "ownership": list(self.ownership or []),
            "blast_radius": list(self.blast_radius or []),
            "structural_risks": list(self.structural_risks or []),
            "summary": dict(self.summary or {}),
            "score": dict(self.score or {}),
            "determinant_signature": self.determinant_signature,
            "freshness": dict(self.freshness or {}),
            "gitnexus_stats": dict(self.gitnexus_stats or {}),
            "generated_at": self.generated_at,
        }


@dataclass(frozen=True)
class CodebaseTopology:
    modules_total: int
    domains_total: int
    edges_total: int
    hotspots: list[str]
    domain_dependency_matrix: dict[str, list[str]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "modules_total": self.modules_total,
            "domains_total": self.domains_total,
            "edges_total": self.edges_total,
            "hotspots": sorted(self.hotspots),
            "domain_dependency_matrix": {k: sorted(v) for k, v in (self.domain_dependency_matrix or {}).items()},
        }
