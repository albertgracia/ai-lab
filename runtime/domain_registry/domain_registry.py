"""FEDERATION-GOVERNANCE-BOOTSTRAP-01: Domain registry.

Pure governance metadata.

Rules:
- Do not import runtime heavy modules here.
- Do not enforce at runtime yet; this is for tooling/tests/docs.
"""

from __future__ import annotations

from dataclasses import dataclass, field


DOMAIN_REGISTRY_VERSION = "BOOTSTRAP-01"


@dataclass(frozen=True)
class DomainSpec:
    name: str
    purpose: str
    owns: list[str] = field(default_factory=list)
    authority_scope: str = "none"  # none | reads_authority | defines_authority
    allowed_dependencies: list[str] = field(default_factory=list)
    forbidden_dependencies: list[str] = field(default_factory=list)
    operational_role: str = "domain"  # orchestrator | domain | contract | tooling


DOMAIN_SPECS: dict[str, DomainSpec] = {
    "gateway": DomainSpec(
        name="gateway",
        purpose="Core orchestrator / OpenAI-compatible entrypoint.",
        owns=["request entry", "routing selection", "profile application", "stream relay", "sanitization"],
        authority_scope="reads_authority",
        allowed_dependencies=[
            "routing",
            "profiles",
            "fastpath",
            "authority",
            "precision",
            "validation",
            "governance",
            "observability",
            "incidents",
            "semantic",
            "infrastructure",
            "docs",
            "telemetry",
            "operator_intent",
            "codebase",
        ],
        forbidden_dependencies=["remediation"],
        operational_role="orchestrator",
    ),
    "authority": DomainSpec(
        name="authority",
        purpose="Authority-backed cognition: freshness/gaps/confidence from authoritative sources.",
        owns=["truth", "evidence", "freshness", "gaps"],
        authority_scope="defines_authority",
        allowed_dependencies=["telemetry", "observability", "validation"],
        forbidden_dependencies=["routing", "reporting", "remediation", "tools"],
    ),
    "precision": DomainSpec(
        name="precision",
        purpose="Precision semantics: partial evidence/conflicts/stale markers.",
        owns=["precision markers", "confidence integrity"],
        authority_scope="reads_authority",
        allowed_dependencies=["authority", "observability", "validation"],
        forbidden_dependencies=["routing", "remediation"],
    ),
    "observability": DomainSpec(
        name="observability",
        purpose="Sensor fusion, diagnostics, observability audits.",
        owns=["telemetry interpretation", "sensor fusion", "diagnostics"],
        authority_scope="reads_authority",
        allowed_dependencies=["telemetry"],
        forbidden_dependencies=["operational_truth", "routing"],
    ),
    "semantic": DomainSpec(
        name="semantic",
        purpose="Semantic integrity and sterilization: discoverable vs operational, identity hygiene.",
        owns=["semantic state", "identity hygiene", "discoverable contamination detection"],
        authority_scope="reads_authority",
        allowed_dependencies=["authority", "observability", "validation", "telemetry", "infrastructure"],
        forbidden_dependencies=["routing", "remediation"],
    ),
    "infrastructure": DomainSpec(
        name="infrastructure",
        purpose="Infrastructure identity registry, authority roots, dependency maps (metadata + summaries).",
        owns=["infra identity", "authority roots map", "dependency graph"],
        authority_scope="defines_authority",
        allowed_dependencies=["telemetry", "validation"],
        forbidden_dependencies=["routing", "remediation"],
    ),
    "incidents": DomainSpec(
        name="incidents",
        purpose="Operational incident intelligence and summaries.",
        owns=["incident detection", "incident taxonomy usage"],
        authority_scope="reads_authority",
        allowed_dependencies=["observability", "telemetry", "codebase"],
        forbidden_dependencies=["routing"],
    ),
    "docs": DomainSpec(
        name="docs",
        purpose="Documentation/runbook domain (contracts + doctrine). No runtime behavior.",
        owns=["runbooks", "doctrine", "architecture notes"],
        authority_scope="none",
        allowed_dependencies=["contracts", "domain_registry"],
        forbidden_dependencies=["gateway", "routing", "remediation"],
        operational_role="tooling",
    ),
    "codebase": DomainSpec(
        name="codebase",
        purpose="Structural cognition (GitNexus-backed): blast radius, coupling, drift.",
        owns=["structural truth", "blast radius", "coupling analysis"],
        authority_scope="none",
        allowed_dependencies=[],
        forbidden_dependencies=["authority"],
        operational_role="tooling",
    ),
    "operator_intent": DomainSpec(
        name="operator_intent",
        purpose="Deterministic operator intent classification metadata.",
        owns=["intent categories", "safety envelope"],
        authority_scope="none",
        allowed_dependencies=[],
        forbidden_dependencies=["routing", "remediation"],
    ),
    "contracts": DomainSpec(
        name="contracts",
        purpose="Contracts-first types/interfaces and domain boundaries.",
        owns=["domain IO expectations", "invariants"],
        authority_scope="none",
        allowed_dependencies=[],
        forbidden_dependencies=["gateway"],
        operational_role="contract",
    ),
}


def get_domain_spec(name: str) -> DomainSpec | None:
    return DOMAIN_SPECS.get(name)


def validate_dependency(*, src: str, dst: str) -> tuple[bool, str]:
    """Validate a dependency between domains.

    Returns (ok, reason). This is metadata-only and not enforced in runtime.
    """

    if src == dst:
        return True, "self"
    spec = DOMAIN_SPECS.get(src)
    if not spec:
        return False, f"unknown_src_domain:{src}"
    if dst in spec.forbidden_dependencies:
        return False, f"forbidden:{src}->{dst}"
    if spec.allowed_dependencies and dst not in spec.allowed_dependencies:
        return False, f"not_allowed:{src}->{dst}"
    return True, "allowed"
