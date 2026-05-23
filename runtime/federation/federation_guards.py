"""CORE-HARDENING-FEDERATION-GUARDS-01: deterministic federation safety guards.

Goal: ensure federation metadata cannot degrade the runtime core.

Hard rules:
- Deterministic, metadata-only.
- Fail-safe: never raise into gateway/core.
- No routing behavior change; guards only annotate metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from runtime.domain_registry.domain_registry import get_domain_spec, validate_dependency


class FederationGuardSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True)
class FederationGuardViolation:
    code: str
    severity: FederationGuardSeverity
    message: str
    evidence: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "evidence": dict(self.evidence or {}),
        }


@dataclass(frozen=True)
class FederationGuardPolicy:
    """Guard policy configuration (small, deterministic)."""

    strict: bool = True


@dataclass(frozen=True)
class FederationGuardResult:
    ok: bool
    degraded: bool
    status: str  # ok | degraded
    reason_codes: list[str]
    violations: list[FederationGuardViolation]

    def to_metadata(self) -> dict[str, Any]:
        return {
            "_guard_status": self.status,
            "_guard_degraded": bool(self.degraded),
            "_guard_reason_codes": list(self.reason_codes or []),
            "_guard_violations": [v.to_dict() for v in (self.violations or [])],
        }


GUARDS_CONTRACT_VERSION = "GUARDS-01"


def validate_no_recursive_delegation(meta: dict[str, Any]) -> list[FederationGuardViolation]:
    """Detect recursive delegation if a path is present."""

    violations: list[FederationGuardViolation] = []
    path = None
    try:
        path = (meta.get("_federation") or {}).get("path")
    except Exception:
        path = None

    if path is None:
        return violations
    if not isinstance(path, list):
        violations.append(
            FederationGuardViolation(
                code="federation_path_malformed",
                severity=FederationGuardSeverity.ERROR,
                message="_federation.path must be a list when present",
            )
        )
        return violations

    seen: set[str] = set()
    for d in path:
        if not isinstance(d, str):
            continue
        if d in seen:
            violations.append(
                FederationGuardViolation(
                    code="recursive_delegation_detected",
                    severity=FederationGuardSeverity.CRITICAL,
                    message="recursive delegation detected in federation path",
                    evidence={"domain": d, "path": list(path)},
                )
            )
            break
        seen.add(d)
    return violations


def validate_domain_registry_compliance(meta: dict[str, Any]) -> list[FederationGuardViolation]:
    violations: list[FederationGuardViolation] = []
    domain = str(meta.get("_domain") or "").strip()
    if not domain:
        violations.append(
            FederationGuardViolation(
                code="missing_domain",
                severity=FederationGuardSeverity.ERROR,
                message="missing _domain",
            )
        )
        return violations

    if not get_domain_spec(domain):
        violations.append(
            FederationGuardViolation(
                code="unknown_domain",
                severity=FederationGuardSeverity.ERROR,
                message="unknown domain in federation metadata",
                evidence={"domain": domain},
            )
        )
        return violations

    ok, reason = validate_dependency(src="gateway", dst=domain)
    if not ok:
        violations.append(
            FederationGuardViolation(
                code="forbidden_coupling",
                severity=FederationGuardSeverity.CRITICAL,
                message="domain registry forbids gateway dependency",
                evidence={"reason": reason, "domain": domain},
            )
        )
    return violations


def validate_budget_consistency(meta: dict[str, Any]) -> list[FederationGuardViolation]:
    """Detect budget bypass and overflow mismatch."""

    violations: list[FederationGuardViolation] = []
    domain = str(meta.get("_domain") or "").strip() or "unknown"

    if "_context_budget" not in meta:
        violations.append(
            FederationGuardViolation(
                code="missing_context_budget",
                severity=FederationGuardSeverity.ERROR,
                message="missing _context_budget",
                evidence={"domain": domain},
            )
        )

    consumed = meta.get("_budget_consumed")
    remaining = meta.get("_budget_remaining")
    overflow = meta.get("_budget_overflow")
    if not isinstance(consumed, dict) or not isinstance(remaining, dict) or not isinstance(overflow, dict):
        violations.append(
            FederationGuardViolation(
                code="budget_metadata_malformed",
                severity=FederationGuardSeverity.ERROR,
                message="budget metadata must be dicts: _budget_consumed/_budget_remaining/_budget_overflow",
                evidence={"domain": domain},
            )
        )
        return violations

    dom_over = overflow.get(domain)
    if isinstance(dom_over, dict):
        oc = int(dom_over.get("chars") or 0)
        oi = int(dom_over.get("items") or 0)
        has_overflow = (oc > 0) or (oi > 0)
        truncated_domains = meta.get("_truncated_domains")
        if has_overflow:
            if not isinstance(truncated_domains, list) or domain not in truncated_domains:
                violations.append(
                    FederationGuardViolation(
                        code="overflow_not_marked",
                        severity=FederationGuardSeverity.ERROR,
                        message="overflow present but domain not marked in _truncated_domains",
                        evidence={"domain": domain, "overflow": {"chars": oc, "items": oi}},
                    )
                )
    return violations


def validate_delegation_safety(meta: dict[str, Any]) -> list[FederationGuardViolation]:
    violations: list[FederationGuardViolation] = []
    fed = meta.get("_federation")
    if not isinstance(fed, dict):
        violations.append(
            FederationGuardViolation(
                code="missing_federation_block",
                severity=FederationGuardSeverity.ERROR,
                message="missing or malformed _federation block",
            )
        )
        return violations

    domain = str(meta.get("_domain") or "").strip()
    delegated_to = str(meta.get("_delegated_to") or "").strip()
    if not domain or not delegated_to:
        violations.append(
            FederationGuardViolation(
                code="missing_delegation_fields",
                severity=FederationGuardSeverity.ERROR,
                message="missing _domain or _delegated_to",
            )
        )

    # Never allow delegation to remediation.
    if delegated_to.lower() == "remediation":
        violations.append(
            FederationGuardViolation(
                code="delegation_to_remediation_forbidden",
                severity=FederationGuardSeverity.CRITICAL,
                message="delegation to remediation is forbidden",
            )
        )

    # Semantic cannot claim authority override (guard only checks metadata consistency).
    if domain == "semantic" and str(fed.get("authority_weight") or "").lower() == "high":
        violations.append(
            FederationGuardViolation(
                code="semantic_authority_weight_too_high",
                severity=FederationGuardSeverity.WARNING,
                message="semantic domain should not claim high authority weight",
            )
        )

    return violations


def validate_federation_metadata(meta: dict[str, Any], *, policy: FederationGuardPolicy | None = None) -> FederationGuardResult:
    """Validate federation metadata and return a fail-safe result."""

    policy = policy or FederationGuardPolicy(strict=True)
    violations: list[FederationGuardViolation] = []
    reason_codes: list[str] = []

    try:
        violations.extend(validate_domain_registry_compliance(meta))
        violations.extend(validate_delegation_safety(meta))
        violations.extend(validate_budget_consistency(meta))
        violations.extend(validate_no_recursive_delegation(meta))
    except Exception:
        # Fail-safe: never raise.
        violations.append(
            FederationGuardViolation(
                code="guard_exception",
                severity=FederationGuardSeverity.CRITICAL,
                message="guard validation raised an exception (caught)",
            )
        )

    degraded = bool(violations)
    ok = not degraded
    status = "ok" if ok else "degraded"

    for v in violations:
        reason_codes.append(v.code)

    # In strict mode, any violation degrades. (Non-strict reserved for future.)
    if not policy.strict:
        # Still mark degraded for ERROR/CRITICAL.
        degraded = any(v.severity in {FederationGuardSeverity.ERROR, FederationGuardSeverity.CRITICAL} for v in violations)
        ok = not degraded
        status = "ok" if ok else "degraded"

    return FederationGuardResult(
        ok=ok,
        degraded=degraded,
        status=status,
        reason_codes=sorted(set(reason_codes)),
        violations=violations,
    )


def build_guard_summary(result: FederationGuardResult) -> dict[str, Any]:
    """Small summary for embedding in metadata."""

    highest = "info"
    if result.violations:
        order = {
            FederationGuardSeverity.INFO.value: 0,
            FederationGuardSeverity.WARNING.value: 1,
            FederationGuardSeverity.ERROR.value: 2,
            FederationGuardSeverity.CRITICAL.value: 3,
        }
        highest = max((v.severity.value for v in result.violations), key=lambda s: order.get(s, 0))

    return {
        "contract_version": GUARDS_CONTRACT_VERSION,
        "status": result.status,
        "degraded": bool(result.degraded),
        "violations_total": int(len(result.violations or [])),
        "highest_severity": highest,
    }
