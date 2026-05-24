"""FEDERATION-OBSERVABILITY-01: in-memory observability for federation propagation.

Purpose: make cognitive propagation cost visible BEFORE adding autonomy/orchestration.

Hard rules:
- Deterministic, metadata-only.
- No endpoints here.
- No cross-domain mutation.
- No loops/recursion.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass(frozen=True)
class FederationPropagationTrace:
    source_domain: str
    target_domain: str
    authority_weight: str
    budget_consumed: dict[str, int]
    overflow: bool
    truncated: bool
    degraded: bool
    rejected: bool
    path_depth: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "authority_weight": self.authority_weight,
            "budget_consumed": dict(self.budget_consumed),
            "overflow": bool(self.overflow),
            "truncated": bool(self.truncated),
            "degraded": bool(self.degraded),
            "rejected": bool(self.rejected),
            "path_depth": int(self.path_depth),
        }


@dataclass(frozen=True)
class BudgetOverflowEvent:
    domain: str
    overflow: dict[str, int]
    rejected: bool
    truncated: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "overflow": dict(self.overflow),
            "rejected": bool(self.rejected),
            "truncated": bool(self.truncated),
        }


@dataclass(frozen=True)
class DelegationPath:
    source_domain: str
    target_domain: str
    depth: int

    def key(self) -> str:
        return f"{self.source_domain}->{self.target_domain}@{self.depth}"


@dataclass(frozen=True)
class DomainPropagationStats:
    domain: str
    delegated_requests_total: int
    budget_overflows_total: int
    truncations_total: int
    rejected_total: int
    degraded_total: int
    avg_consumed_chars: float
    avg_consumed_items: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "delegated_requests_total": int(self.delegated_requests_total),
            "budget_overflows_total": int(self.budget_overflows_total),
            "truncations_total": int(self.truncations_total),
            "rejected_total": int(self.rejected_total),
            "degraded_total": int(self.degraded_total),
            "avg_consumed_chars": float(self.avg_consumed_chars),
            "avg_consumed_items": float(self.avg_consumed_items),
        }


@dataclass(frozen=True)
class PropagationHotspot:
    domain: str
    hotspot_type: str
    severity: str
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "hotspot_type": self.hotspot_type,
            "severity": self.severity,
            "evidence": dict(self.evidence),
        }


@dataclass(frozen=True)
class FederationObservabilitySnapshot:
    contract_version: str
    domain_calls_total: int
    delegated_requests_total: int
    budget_overflows_total: int
    truncations_total: int
    degraded_propagations_total: int
    rejected_domains_total: int
    propagation_depth_max: int
    overflow_by_domain: dict[str, int]
    cross_domain_paths: dict[str, int]
    per_domain: list[dict[str, Any]]
    hotspots: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "domain_calls_total": int(self.domain_calls_total),
            "delegated_requests_total": int(self.delegated_requests_total),
            "budget_overflows_total": int(self.budget_overflows_total),
            "truncations_total": int(self.truncations_total),
            "degraded_propagations_total": int(self.degraded_propagations_total),
            "rejected_domains_total": int(self.rejected_domains_total),
            "propagation_depth_max": int(self.propagation_depth_max),
            "overflow_by_domain": dict(self.overflow_by_domain),
            "cross_domain_paths": dict(self.cross_domain_paths),
            "per_domain": list(self.per_domain or []),
            "hotspots": list(self.hotspots or []),
        }


FEDERATION_OBSERVABILITY_CONTRACT_VERSION = "OBS-01"

# Keep a small ring-buffer of traces to bound memory.
_TRACE_MAX = 512
_lock = Lock()
_traces: deque[FederationPropagationTrace] = deque(maxlen=_TRACE_MAX)

_domain_calls_total = 0
_delegated_requests_total = 0
_budget_overflows_total = 0
_truncations_total = 0
_degraded_propagations_total = 0
_rejected_domains_total = 0
_depth_max = 0

# Trust propagation tracking (FEDERATION-TRUST-PROPAGATION-01)
_trust_degradations_total = 0
_recursive_risk_total = 0
_stale_propagations_total = 0
_ttl_expirations_total = 0

_trust_sum_by_domain: Counter[str] = Counter()
_trust_count_by_domain: Counter[str] = Counter()
_attenuation_sum_by_domain: Counter[str] = Counter()

# Evidence lineage tracking (FEDERATION-EVIDENCE-LINEAGE-01)
_evidence_propagations_total = 0
_stale_evidence_total = 0
_replay_risk_total = 0
_invalid_lineage_total = 0
_evidence_reuse_total = 0
_lineage_depth_max = 0

_evidence_seen_counts: dict[str, int] = {}


def observe_evidence_id(evidence_id: str) -> int:
    """Atomically increments and returns previous seen count for evidence_id."""

    with _lock:
        prev = int(_evidence_seen_counts.get(evidence_id) or 0)
        _evidence_seen_counts[evidence_id] = prev + 1
        return prev

_overflow_by_domain: Counter[str] = Counter()
_cross_domain_paths: Counter[str] = Counter()

# For averages.
_consumed_chars_sum: Counter[str] = Counter()
_consumed_items_sum: Counter[str] = Counter()
_consumed_count: Counter[str] = Counter()

_truncations_by_domain: Counter[str] = Counter()
_rejected_by_domain: Counter[str] = Counter()
_degraded_by_domain: Counter[str] = Counter()


def reset_federation_observability_state() -> None:
    """Test/support helper: resets in-memory counters and traces."""

    global _domain_calls_total, _delegated_requests_total, _budget_overflows_total
    global _truncations_total, _degraded_propagations_total, _rejected_domains_total, _depth_max
    global _trust_degradations_total, _recursive_risk_total, _stale_propagations_total, _ttl_expirations_total
    global _evidence_propagations_total, _stale_evidence_total, _replay_risk_total, _invalid_lineage_total, _evidence_reuse_total, _lineage_depth_max
    with _lock:
        _traces.clear()
        _domain_calls_total = 0
        _delegated_requests_total = 0
        _budget_overflows_total = 0
        _truncations_total = 0
        _degraded_propagations_total = 0
        _rejected_domains_total = 0
        _depth_max = 0
        _trust_degradations_total = 0
        _recursive_risk_total = 0
        _stale_propagations_total = 0
        _ttl_expirations_total = 0
        _evidence_propagations_total = 0
        _stale_evidence_total = 0
        _replay_risk_total = 0
        _invalid_lineage_total = 0
        _evidence_reuse_total = 0
        _lineage_depth_max = 0
        _overflow_by_domain.clear()
        _cross_domain_paths.clear()
        _consumed_chars_sum.clear()
        _consumed_items_sum.clear()
        _consumed_count.clear()
        _truncations_by_domain.clear()
        _rejected_by_domain.clear()
        _degraded_by_domain.clear()
        _trust_sum_by_domain.clear()
        _trust_count_by_domain.clear()
        _attenuation_sum_by_domain.clear()
        _evidence_seen_counts.clear()


def record_evidence_lineage(*, evidence_summary: dict[str, Any]) -> None:
    """Record evidence lineage propagation (metadata-only, in-memory)."""

    global _evidence_propagations_total, _stale_evidence_total, _replay_risk_total, _invalid_lineage_total
    global _evidence_reuse_total, _lineage_depth_max
    with _lock:
        _evidence_propagations_total += 1

        reuse_count = int(evidence_summary.get("reuse_count") or 0)
        if reuse_count > 0:
            _evidence_reuse_total += 1

        freshness = evidence_summary.get("freshness")
        freshness_state = ""
        if isinstance(freshness, dict):
            freshness_state = str(freshness.get("state") or "")
        if freshness_state in {"stale", "expired"}:
            _stale_evidence_total += 1

        replay = evidence_summary.get("replay_risk")
        replay_level = ""
        if isinstance(replay, dict):
            replay_level = str(replay.get("level") or "")
        if replay_level in {"low", "medium", "high"}:
            _replay_risk_total += 1

        validation = str(evidence_summary.get("validation") or "")
        if validation and validation != "ok":
            _invalid_lineage_total += 1

        depth = int(evidence_summary.get("lineage_depth") or 0)
        _lineage_depth_max = max(_lineage_depth_max, depth)


def get_evidence_summary() -> dict[str, Any]:
    with _lock:
        return {
            "contract_version": FEDERATION_OBSERVABILITY_CONTRACT_VERSION,
            "evidence_propagations_total": int(_evidence_propagations_total),
            "stale_evidence_total": int(_stale_evidence_total),
            "replay_risk_total": int(_replay_risk_total),
            "invalid_lineage_total": int(_invalid_lineage_total),
            "lineage_depth_max": int(_lineage_depth_max),
            "evidence_reuse_total": int(_evidence_reuse_total),
        }


def get_lineage_hotspots(*, min_events: int = 3) -> list[dict[str, Any]]:
    """Deterministic hotspots (coarse) from evidence counters."""

    with _lock:
        events = int(_evidence_propagations_total)
        if events < int(min_events):
            return []
        hotspots: list[dict[str, Any]] = []
        if _invalid_lineage_total > 0:
            hotspots.append({"hotspot_type": "invalid_lineage", "severity": "critical", "events": events, "total": int(_invalid_lineage_total)})
        if _replay_risk_total > 0 and (_replay_risk_total / max(1, events)) >= 0.5:
            hotspots.append({"hotspot_type": "frequent_replay_risk", "severity": "high", "events": events, "total": int(_replay_risk_total)})
        if _stale_evidence_total > 0 and (_stale_evidence_total / max(1, events)) >= 0.5:
            hotspots.append({"hotspot_type": "frequent_stale_evidence", "severity": "high", "events": events, "total": int(_stale_evidence_total)})
        # Deterministic ordering
        hotspots.sort(key=lambda h: (h["severity"], h["hotspot_type"]))
        return hotspots


def record_trust_propagation(
    *,
    target_domain: str,
    trust_score: float,
    attenuation_factor: float,
    degraded: bool,
    recursive_risk: bool,
    stale: bool,
    ttl_expired: bool,
) -> None:
    """Record trust propagation metrics (metadata-only)."""

    global _trust_degradations_total, _recursive_risk_total, _stale_propagations_total, _ttl_expirations_total
    with _lock:
        d = target_domain or "unknown"
        _trust_sum_by_domain[d] += float(trust_score)
        _attenuation_sum_by_domain[d] += float(attenuation_factor)
        _trust_count_by_domain[d] += 1
        if degraded:
            _trust_degradations_total += 1
        if recursive_risk:
            _recursive_risk_total += 1
        if stale:
            _stale_propagations_total += 1
        if ttl_expired:
            _ttl_expirations_total += 1


def record_propagation_trace(trace: FederationPropagationTrace) -> None:
    """Record a propagation trace (metadata-only)."""

    global _domain_calls_total, _delegated_requests_total, _budget_overflows_total
    global _truncations_total, _degraded_propagations_total, _rejected_domains_total, _depth_max

    with _lock:
        _traces.append(trace)

        _domain_calls_total += 1
        _delegated_requests_total += 1

        if trace.overflow:
            _budget_overflows_total += 1
            _overflow_by_domain[trace.target_domain] += 1
        if trace.truncated:
            _truncations_total += 1
            _truncations_by_domain[trace.target_domain] += 1
        if trace.rejected:
            _rejected_domains_total += 1
            _rejected_by_domain[trace.target_domain] += 1
        if trace.degraded:
            _degraded_propagations_total += 1
            _degraded_by_domain[trace.target_domain] += 1

        _depth_max = max(_depth_max, int(trace.path_depth))

        chars = int((trace.budget_consumed or {}).get("chars") or 0)
        items = int((trace.budget_consumed or {}).get("items") or 0)
        _consumed_chars_sum[trace.target_domain] += chars
        _consumed_items_sum[trace.target_domain] += items
        _consumed_count[trace.target_domain] += 1

        path_key = DelegationPath(source_domain=trace.source_domain, target_domain=trace.target_domain, depth=int(trace.path_depth)).key()
        _cross_domain_paths[path_key] += 1


def get_overflow_summary() -> dict[str, Any]:
    with _lock:
        return {
            "contract_version": FEDERATION_OBSERVABILITY_CONTRACT_VERSION,
            "budget_overflows_total": int(_budget_overflows_total),
            "overflow_by_domain": dict(_overflow_by_domain),
            "truncations_total": int(_truncations_total),
            "rejected_domains_total": int(_rejected_domains_total),
            "trust_degradations_total": int(_trust_degradations_total),
            "recursive_risk_total": int(_recursive_risk_total),
            "stale_propagations_total": int(_stale_propagations_total),
            "ttl_expirations_total": int(_ttl_expirations_total),
        }


def _build_per_domain_stats() -> list[DomainPropagationStats]:
    domains = sorted(set(list(_consumed_count.keys()) + list(_overflow_by_domain.keys()) + list(_truncations_by_domain.keys())))
    out: list[DomainPropagationStats] = []
    for d in domains:
        n = int(_consumed_count.get(d) or 0)
        avg_chars = float(_consumed_chars_sum.get(d) or 0) / float(n) if n else 0.0
        avg_items = float(_consumed_items_sum.get(d) or 0) / float(n) if n else 0.0
        out.append(
            DomainPropagationStats(
                domain=d,
                delegated_requests_total=n,
                budget_overflows_total=int(_overflow_by_domain.get(d) or 0),
                truncations_total=int(_truncations_by_domain.get(d) or 0),
                rejected_total=int(_rejected_by_domain.get(d) or 0),
                degraded_total=int(_degraded_by_domain.get(d) or 0),
                avg_consumed_chars=avg_chars,
                avg_consumed_items=avg_items,
            )
        )
    return out


def get_domain_hotspots(*, min_events: int = 3) -> list[PropagationHotspot]:
    """Deterministic hotspot detection.

    Rules (simple, deterministic):
    - overflow_rate >= 0.5 with n>=min_events => high
    - reject_rate > 0 with n>=min_events => critical
    - degraded_rate >= 0.7 with n>=min_events => high
    """

    hotspots: list[PropagationHotspot] = []
    for stats in _build_per_domain_stats():
        n = int(stats.delegated_requests_total)
        if n < int(min_events):
            continue
        overflow_rate = float(stats.budget_overflows_total) / float(n) if n else 0.0
        reject_rate = float(stats.rejected_total) / float(n) if n else 0.0
        degraded_rate = float(stats.degraded_total) / float(n) if n else 0.0

        if stats.rejected_total > 0:
            hotspots.append(
                PropagationHotspot(
                    domain=stats.domain,
                    hotspot_type="reject_overflow",
                    severity="critical",
                    evidence={"events": n, "rejected": int(stats.rejected_total), "reject_rate": reject_rate},
                )
            )
        if overflow_rate >= 0.5 and stats.budget_overflows_total > 0:
            hotspots.append(
                PropagationHotspot(
                    domain=stats.domain,
                    hotspot_type="frequent_overflow",
                    severity="high",
                    evidence={"events": n, "overflows": int(stats.budget_overflows_total), "overflow_rate": overflow_rate},
                )
            )
        if degraded_rate >= 0.7 and stats.degraded_total > 0:
            hotspots.append(
                PropagationHotspot(
                    domain=stats.domain,
                    hotspot_type="frequent_degraded",
                    severity="high",
                    evidence={"events": n, "degraded": int(stats.degraded_total), "degraded_rate": degraded_rate},
                )
            )
    # Deterministic ordering.
    hotspots.sort(key=lambda h: (h.severity, h.domain, h.hotspot_type))
    return hotspots


def get_federation_observability_snapshot() -> FederationObservabilitySnapshot:
    with _lock:
        per_domain_stats = _build_per_domain_stats()
        hotspots = get_domain_hotspots(min_events=3)
        # Extend snapshot with trust aggregates in overflow_by_domain/cross_domain_paths only via existing fields.
        snap = FederationObservabilitySnapshot(
            contract_version=FEDERATION_OBSERVABILITY_CONTRACT_VERSION,
            domain_calls_total=int(_domain_calls_total),
            delegated_requests_total=int(_delegated_requests_total),
            budget_overflows_total=int(_budget_overflows_total),
            truncations_total=int(_truncations_total),
            degraded_propagations_total=int(_degraded_propagations_total),
            rejected_domains_total=int(_rejected_domains_total),
            propagation_depth_max=int(_depth_max),
            overflow_by_domain=dict(_overflow_by_domain),
            cross_domain_paths=dict(_cross_domain_paths),
            per_domain=[s.to_dict() for s in per_domain_stats],
            hotspots=[h.to_dict() for h in hotspots],
        )
        return snap


def get_trust_summary() -> dict[str, Any]:
    """Return deterministic trust aggregates (no endpoints)."""

    with _lock:
        avg_trust: dict[str, float] = {}
        avg_att: dict[str, float] = {}
        for d, n in _trust_count_by_domain.items():
            if int(n) <= 0:
                continue
            avg_trust[d] = float(_trust_sum_by_domain.get(d) or 0.0) / float(n)
            avg_att[d] = float(_attenuation_sum_by_domain.get(d) or 0.0) / float(n)
        return {
            "contract_version": FEDERATION_OBSERVABILITY_CONTRACT_VERSION,
            "trust_degradations_total": int(_trust_degradations_total),
            "recursive_risk_total": int(_recursive_risk_total),
            "stale_propagations_total": int(_stale_propagations_total),
            "ttl_expirations_total": int(_ttl_expirations_total),
            "average_trust_by_domain": dict(avg_trust),
            "average_attenuation_by_domain": dict(avg_att),
        }
