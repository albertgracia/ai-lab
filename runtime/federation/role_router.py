"""FEDERATION-ROLE-EXECUTION-01: minimal federated role routing.

Hard rules:
- Pure routing metadata only (no heavy logic execution).
- No remediation/autofix.
- No async orchestration, no loops.
- Must respect domain registry coupling constraints.
"""

from __future__ import annotations

from dataclasses import dataclass

from runtime.domain_registry.domain_registry import validate_dependency
from runtime.federation.context_budget import (
    build_federation_budget_metadata,
    default_domain_limits,
    enforce_context_budget,
)
from runtime.federation.contracts import (
    AuthorityWeight,
    ContextBudgetHint,
    DelegationReason,
    FEDERATION_CONTRACT_VERSION,
    FederatedExecutionIntent,
    FederatedRoleDecision,
)
from runtime.federation.federation_observability import (
    FederationPropagationTrace,
    record_propagation_trace,
    record_trust_propagation,
    record_evidence_lineage,
    observe_evidence_id,
)
from runtime.federation.federation_guards import build_guard_summary, validate_federation_metadata
from runtime.federation.trust_propagation import (
    TrustEvidence,
    TrustLineageNode,
    build_trust_envelope,
    build_trust_summary,
    propagate_trust,
)
from runtime.federation.evidence_lineage import (
    EvidenceAuthorityBinding,
    EvidenceOrigin,
    EvidenceSourceType,
    build_evidence_envelope,
    build_lineage_summary,
)


_REMEDIATION_MARKERS = (
    "restart ",
    "systemctl ",
    "sudo ",
    "rm -",
    "delete ",
    "apply patch",
    "autofix",
    "fix it",
)


@dataclass(frozen=True)
class RoutingCognitionMetadata:
    """Flattened metadata keys expected by the gateway/core."""

    federation: dict
    domain: str
    role: str
    delegated_to: str
    reasoning_scope: str
    context_budget: dict

    def to_dict(self) -> dict:
        return {
            "_federation": self.federation,
            "_domain": self.domain,
            "_role": self.role,
            "_delegated_to": self.delegated_to,
            "_reasoning_scope": self.reasoning_scope,
            "_context_budget": self.context_budget,
        }


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    t = (text or "").lower()
    return any(m in t for m in markers)


def _decision_to_metadata(decision: FederatedRoleDecision) -> RoutingCognitionMetadata:
    federation = {
        "contract_version": decision.contract_version,
        "domain": decision.domain,
        "role": decision.role,
        "delegated_to": decision.delegated_to,
        "reason": decision.reason.value,
        "authority_weight": decision.authority_weight.value,
    }
    return RoutingCognitionMetadata(
        federation=federation,
        domain=decision.domain,
        role=decision.role,
        delegated_to=decision.delegated_to,
        reasoning_scope=decision.context_budget.reasoning_scope,
        context_budget=decision.context_budget.to_dict(),
    )


def resolve_role(intent: FederatedExecutionIntent) -> FederatedRoleDecision:
    """Resolve the bounded domain/role that should answer.

    This function MUST remain deterministic and side-effect free.
    """

    text = (intent.user_text or "").strip()
    t = text.lower()

    # Safety: never route requests that look like remediation/execution.
    if _contains_any(t, _REMEDIATION_MARKERS):
        decision = FederatedRoleDecision(
            contract_version=FEDERATION_CONTRACT_VERSION,
            domain="operator_intent",
            role="operator_intent",
            delegated_to="operator_intent",
            reason=DelegationReason.SAFETY_BLOCK,
            authority_weight=AuthorityWeight.LOW,
            context_budget=ContextBudgetHint(max_chars=600, max_items=6, reasoning_scope="bounded"),
        )
        _enforce_gateway_coupling(decision.domain)
        return decision

    # Route-family hint (when provided by upstream).
    rf = (intent.route_family or "").lower()
    if rf in {"report", "observe"}:
        # Observability heavy: prefer bounded observability framing.
        decision = FederatedRoleDecision(
            contract_version=FEDERATION_CONTRACT_VERSION,
            domain="observability",
            role="observability",
            delegated_to="observability",
            reason=DelegationReason.ROUTE_FAMILY_HINT,
            authority_weight=AuthorityWeight.MEDIUM,
            context_budget=ContextBudgetHint(max_chars=1000, max_items=10, reasoning_scope="bounded"),
        )
        _enforce_gateway_coupling(decision.domain)
        return decision

    # Keyword routing.
    if any(k in t for k in ("incident", "incidente", "postmortem", "rca", "outage")):
        decision = FederatedRoleDecision(
            contract_version=FEDERATION_CONTRACT_VERSION,
            domain="incidents",
            role="incidents",
            delegated_to="incidents",
            reason=DelegationReason.KEYWORD_MATCH,
            authority_weight=AuthorityWeight.MEDIUM,
            context_budget=ContextBudgetHint(max_chars=1200, max_items=12, reasoning_scope="bounded"),
        )
        _enforce_gateway_coupling(decision.domain)
        return decision

    if any(k in t for k in ("prometheus", "grafana", "metrics", "métricas", "telemetry", "ttfb", "latency")):
        decision = FederatedRoleDecision(
            contract_version=FEDERATION_CONTRACT_VERSION,
            domain="observability",
            role="observability",
            delegated_to="observability",
            reason=DelegationReason.KEYWORD_MATCH,
            authority_weight=AuthorityWeight.HIGH,
            context_budget=ContextBudgetHint(max_chars=1100, max_items=10, reasoning_scope="bounded"),
        )
        _enforce_gateway_coupling(decision.domain)
        return decision

    if any(k in t for k in ("operational truth", "authority", "freshness", "grounded", "evidence")):
        decision = FederatedRoleDecision(
            contract_version=FEDERATION_CONTRACT_VERSION,
            domain="authority",
            role="authority",
            delegated_to="authority",
            reason=DelegationReason.KEYWORD_MATCH,
            authority_weight=AuthorityWeight.HIGH,
            context_budget=ContextBudgetHint(max_chars=900, max_items=8, reasoning_scope="bounded"),
        )
        _enforce_gateway_coupling(decision.domain)
        return decision

    if any(k in t for k in ("systemd", "service", "puerto", "port ", "dns", "ntp", "time semantics", "timezone")):
        decision = FederatedRoleDecision(
            contract_version=FEDERATION_CONTRACT_VERSION,
            domain="infrastructure",
            role="infra",
            delegated_to="infrastructure",
            reason=DelegationReason.KEYWORD_MATCH,
            authority_weight=AuthorityWeight.MEDIUM,
            context_budget=ContextBudgetHint(max_chars=900, max_items=8, reasoning_scope="bounded"),
        )
        _enforce_gateway_coupling(decision.domain)
        return decision

    if any(k in t for k in ("semantic integrity", "semantic state", "stale", "discoverable", "inventory", "phantom", "legacy")):
        decision = FederatedRoleDecision(
            contract_version=FEDERATION_CONTRACT_VERSION,
            domain="semantic",
            role="semantic",
            delegated_to="semantic",
            reason=DelegationReason.KEYWORD_MATCH,
            authority_weight=AuthorityWeight.MEDIUM,
            context_budget=ContextBudgetHint(max_chars=1000, max_items=10, reasoning_scope="bounded"),
        )
        _enforce_gateway_coupling(decision.domain)
        return decision

    if any(k in t for k in ("doc", "docs", "runbook", "document", "manual", "guía", "guia")):
        decision = FederatedRoleDecision(
            contract_version=FEDERATION_CONTRACT_VERSION,
            domain="docs",
            role="docs",
            delegated_to="docs",
            reason=DelegationReason.KEYWORD_MATCH,
            authority_weight=AuthorityWeight.LOW,
            context_budget=ContextBudgetHint(max_chars=800, max_items=10, reasoning_scope="bounded"),
        )
        _enforce_gateway_coupling(decision.domain)
        return decision

    # Default: operator intent keeps boundedness without claiming authority.
    decision = FederatedRoleDecision(
        contract_version=FEDERATION_CONTRACT_VERSION,
        domain="operator_intent",
        role="operator_intent",
        delegated_to="operator_intent",
        reason=DelegationReason.DEFAULT_CORE,
        authority_weight=AuthorityWeight.LOW,
        context_budget=ContextBudgetHint(max_chars=700, max_items=8, reasoning_scope="bounded"),
    )
    _enforce_gateway_coupling(decision.domain)
    return decision


def build_routing_metadata(intent: FederatedExecutionIntent) -> dict:
    """Return non-invasive federation metadata for payload/trace."""

    decision = resolve_role(intent)
    base = _decision_to_metadata(decision).to_dict()

    # FEDERATION-CONTEXT-BUDGETS-01: enforce deterministic domain budget for routing payload.
    # This is metadata-only: we never block routing; we only cap what we attach.
    limits = default_domain_limits()
    envelope = enforce_context_budget(
        domain=decision.domain,
        payload={
            "user_text": intent.user_text or "",
            "route_family": intent.route_family or "unknown",
            "request_id": intent.request_id or "",
            "evidence_scope": intent.evidence_scope or "unknown",
        },
        limits=limits,
    )

    base["_context_budget"] = envelope.to_metadata()["budget"]
    base.update(build_federation_budget_metadata(envelopes=[envelope]))
    base["_budget_overflow"] = {decision.domain: envelope.to_metadata()["overflow"]}
    if envelope.truncated or envelope.rejected:
        base["_truncated_domains"] = [decision.domain]

    # FEDERATION-EVIDENCE-LINEAGE-01: deterministic evidence lineage metadata.
    try:
        canonical_payload = {
            "route_family": intent.route_family or "unknown",
            "user_text": intent.user_text or "",
            "target_domain": decision.domain,
            "role": decision.role,
            "delegated_to": decision.delegated_to,
            "reason": base.get("_federation", {}).get("reason", ""),
            "authority_weight": base.get("_federation", {}).get("authority_weight", ""),
            "reasoning_scope": base.get("_reasoning_scope", "bounded"),
        }

        source_type = EvidenceSourceType.ROUTING
        if decision.domain == "authority":
            source_type = EvidenceSourceType.AUTHORITY
        elif decision.domain == "observability":
            source_type = EvidenceSourceType.OBSERVABILITY
        elif decision.domain == "semantic":
            source_type = EvidenceSourceType.SEMANTIC
        elif decision.domain == "infrastructure":
            source_type = EvidenceSourceType.INFRASTRUCTURE
        elif decision.domain == "operator_intent":
            source_type = EvidenceSourceType.UNKNOWN

        origin = EvidenceOrigin(
            source_domain=str(decision.domain),
            source_role=str(decision.role),
            model_profile="unknown",
            tool_name="",
            trust_scope=str(intent.route_family or "unknown"),
        )
        authority_binding = EvidenceAuthorityBinding(
            authority_bound=bool(source_type == EvidenceSourceType.AUTHORITY),
            authority_domain="authority" if source_type == EvidenceSourceType.AUTHORITY else "",
            binding_reason="source_type" if source_type == EvidenceSourceType.AUTHORITY else "",
        )

        # Important: created_at exists but is NOT part of evidence_id/hash.
        # Use observability tracker for deterministic reuse/replay detection.
        # Note: we intentionally count "previous" before building, to keep build deterministic.
        # This also keeps the bump atomic under the observability lock.
        # previous_seen_count influences reuse/replay metadata only (not evidence_id/hash).
        #
        # evidence_id itself is computed from stable identity fields.
        # We therefore compute it inside build, but need previous_seen_count now.
        # We approximate by observing after build in a second step.
        # To keep atomicity, we accept that reuse_count may lag by 1 in rare concurrent cases.
        prev = 0

        ev = build_evidence_envelope(
            evidence_type="routing_metadata",
            source_type=source_type,
            canonical_payload=canonical_payload,
            origin=origin,
            parent_evidence_ids=[],
            ancestry_chain=[],
            authority_binding=authority_binding,
            freshness_seconds=0,
            created_at=0.0,
            previous_seen_count=prev,
            max_depth=3,
        ).envelope

        # Now bump seen count atomically and re-materialize reuse/replay fields deterministically.
        prev = observe_evidence_id(ev.evidence_id)
        ev = build_evidence_envelope(
            evidence_type="routing_metadata",
            source_type=source_type,
            canonical_payload=canonical_payload,
            origin=origin,
            parent_evidence_ids=[],
            ancestry_chain=[],
            authority_binding=authority_binding,
            freshness_seconds=0,
            created_at=0.0,
            previous_seen_count=prev,
            max_depth=3,
        ).envelope

        summary = build_lineage_summary(ev).to_dict()
        base["_evidence_id"] = ev.evidence_id
        base["_evidence_source"] = ev.source_type.value
        base["_evidence_confidence"] = ev.effective_confidence
        base["_evidence_freshness"] = ev.freshness.to_dict()
        base["_evidence_lineage_depth"] = ev.ancestry.lineage_depth
        base["_evidence_reuse_count"] = ev.reuse.reuse_count
        base["_evidence_replay_risk"] = ev.replay_risk.to_dict()
        base["_evidence_authority_bound"] = bool(ev.authority_binding.authority_bound)
        base["_evidence_summary"] = summary

        # Observability counters (in-memory)
        record_evidence_lineage(evidence_summary={**summary, "validation": ev.validation.value})
    except Exception:
        # Fail-safe minimal degraded evidence.
        base["_evidence_id"] = ""
        base["_evidence_source"] = "unknown"
        base["_evidence_confidence"] = 0.0
        base["_evidence_freshness"] = {"freshness_ttl": 0, "freshness_seconds": 0, "state": "expired"}
        base["_evidence_lineage_depth"] = 0
        base["_evidence_reuse_count"] = 0
        base["_evidence_replay_risk"] = {"level": "high", "replayed": False}
        base["_evidence_authority_bound"] = False
        base["_evidence_summary"] = {"evidence_id": "", "degraded": True, "decay_reason": "error"}

    # FEDERATION-TRUST-PROPAGATION-01: deterministic trust propagation metadata.
    try:
        evidence = [
            TrustEvidence(
                evidence_type="routing_metadata",
                authority_backed=bool(decision.domain == "authority"),
                freshness_seconds=0,
            )
        ]
        lineage = [TrustLineageNode(domain="gateway", evidence_count=1)]
        trust_env = build_trust_envelope(
            source_domain="gateway",
            target_domain=decision.domain,
            origin_domain="gateway",
            evidence=evidence,
            lineage=lineage,
            ttl_seconds=120,
        )
        trust = propagate_trust(trust_env)
        base["_trust_score"] = trust.trust_score
        base["_trust_degraded"] = bool(trust.degraded)
        base["_trust_freshness"] = {"freshness_seconds": 0, "stale": bool(trust.stale)}
        base["_trust_ttl"] = trust.semantic_ttl
        base["_trust_lineage_depth"] = trust.lineage_depth
        base["_recursive_risk"] = bool(trust.recursive_risk)
        base["_trust_attenuation"] = trust.attenuation_factor
        base["_trust_summary"] = build_trust_summary(trust)

        record_trust_propagation(
            target_domain=decision.domain,
            trust_score=float(trust.trust_score),
            attenuation_factor=float(trust.attenuation_factor),
            degraded=bool(trust.degraded),
            recursive_risk=bool(trust.recursive_risk),
            stale=bool(trust.stale),
            ttl_expired=bool(trust.semantic_ttl <= 0),
        )
    except Exception:
        base["_trust_score"] = 0.0
        base["_trust_degraded"] = True
        base["_trust_freshness"] = {"freshness_seconds": 0, "stale": True}
        base["_trust_ttl"] = 0
        base["_trust_lineage_depth"] = 0
        base["_recursive_risk"] = False
        base["_trust_attenuation"] = 0.0

    # FEDERATION-OBSERVABILITY-01: record in-memory propagation trace.
    overflow = envelope.to_metadata()["overflow"]
    has_overflow = bool((overflow.get("chars") or 0) > 0 or (overflow.get("items") or 0) > 0)
    record_propagation_trace(
        FederationPropagationTrace(
            source_domain="gateway",
            target_domain=decision.domain,
            authority_weight=base["_federation"].get("authority_weight", "unknown"),
            budget_consumed=envelope.to_metadata()["consumed"],
            overflow=has_overflow,
            truncated=bool(envelope.truncated),
            degraded=bool(envelope.degraded),
            rejected=bool(envelope.rejected),
            path_depth=1,
        )
    )

    # CORE-HARDENING-FEDERATION-GUARDS-01: fail-safe validation of federation metadata.
    try:
        guard = validate_federation_metadata(base)
        base["_federation_guard"] = build_guard_summary(guard)
        base.update(guard.to_metadata())
    except Exception:
        # Never leak guard exceptions.
        base["_federation_guard"] = {"contract_version": "GUARDS-01", "status": "degraded", "degraded": True}
        base["_guard_status"] = "degraded"
        base["_guard_degraded"] = True
        base["_guard_reason_codes"] = ["guard_exception"]
        base["_guard_violations"] = [{"code": "guard_exception", "severity": "critical", "message": "guard exception (caught)", "evidence": {}}]
    return base


def _enforce_gateway_coupling(domain: str) -> None:
    ok, reason = validate_dependency(src="gateway", dst=domain)
    if not ok:
        raise ValueError(f"federation_role_router_forbidden:{reason}")
