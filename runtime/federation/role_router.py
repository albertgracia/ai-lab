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
)
from runtime.federation.federation_guards import build_guard_summary, validate_federation_metadata


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
