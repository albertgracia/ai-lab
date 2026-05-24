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

import os
import time
from collections import Counter, deque
from threading import Lock

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

# ─────────────────────────────────────────────────────────────────────────────
# FEDERATION-COGNITIVE-GUARDS-01: bounded cognitive runtime protection layer
#
# Hard rules:
# - In-memory only (NO persistence, NO distributed sync).
# - Deterministic, bounded, fail-safe.
# - No routing decisions: guards only classify, constrain metadata, and expose observability.
# - No imports from routing/gateway to avoid loops.
#
# This layer complements CORE-HARDENING-FEDERATION-GUARDS-01.


class FederationGuardRuntimeState(str, Enum):
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    CONSTRAINED = "CONSTRAINED"
    SAFE_MODE = "SAFE_MODE"


class FederationGuardEventType(str, Enum):
    replay_detected = "replay_detected"
    lineage_depth_exceeded = "lineage_depth_exceeded"
    propagation_cap_applied = "propagation_cap_applied"
    authority_escalation_detected = "authority_escalation_detected"
    safe_mode_transition = "safe_mode_transition"
    constrained_mode_transition = "constrained_mode_transition"


@dataclass(frozen=True)
class FederationPropagationCaps:
    # All caps are small, bounded, and interpreted defensively.
    max_lineage_depth: int = 3
    max_replay_reuse: int = 6
    max_propagation_fanout: int = 8
    max_authority_escalation: int = 3
    # Max number of reuses of a single evidence_id within a short window.
    max_evidence_reuse_rate: int = 8

    # Heuristic windows/cooldowns (seconds) for bounded detection.
    reuse_window_seconds: int = 30
    event_window_seconds: int = 60
    constrained_cooldown_seconds: int = 60
    safe_mode_cooldown_seconds: int = 120


COGNITIVE_GUARDS_CONTRACT_VERSION = "CG-01"

_cg_lock = Lock()
_cg_state: FederationGuardRuntimeState = FederationGuardRuntimeState.NORMAL
_cg_state_until_ts: float = 0.0

_CG_EVENTS_MAX = 256
_cg_events: deque[dict[str, Any]] = deque(maxlen=_CG_EVENTS_MAX)

# Bounded sliding windows for replay/storm heuristics.
_CG_GLOBAL_OBS_MAX = 512
_cg_global_observations: deque[tuple[float, str]] = deque(maxlen=_CG_GLOBAL_OBS_MAX)  # (ts, evidence_id)
_cg_evidence_recent: dict[str, deque[float]] = {}
_cg_evidence_recent_max_per_id = 32
_cg_evidence_recent_max_keys = 256

_cg_authority_escalation_ts: deque[float] = deque(maxlen=256)

# Counters for explainability (in-memory; exported via /runtime/guards/summary).
_cg_event_counters: Counter[str] = Counter()
_cg_state_transitions_total = 0
_cg_caps_applied_total = 0
_cg_replay_detections_total = 0
_cg_storm_detections_total = 0
_cg_authority_escalations_total = 0


def _clamp_int(val: Any, *, default: int, lo: int, hi: int) -> int:
    try:
        i = int(val)
        return max(int(lo), min(int(hi), i))
    except Exception:
        return int(default)


def load_propagation_caps_from_env() -> FederationPropagationCaps:
    """Load caps from env vars with tight clamping.

    This keeps behavior configurable without persistence or heavy config plumbing.
    """

    return FederationPropagationCaps(
        max_lineage_depth=_clamp_int(os.getenv("AI_LAB_GUARD_MAX_LINEAGE_DEPTH"), default=3, lo=1, hi=16),
        max_replay_reuse=_clamp_int(os.getenv("AI_LAB_GUARD_MAX_REPLAY_REUSE"), default=6, lo=0, hi=128),
        max_propagation_fanout=_clamp_int(os.getenv("AI_LAB_GUARD_MAX_PROPAGATION_FANOUT"), default=8, lo=1, hi=128),
        max_authority_escalation=_clamp_int(os.getenv("AI_LAB_GUARD_MAX_AUTHORITY_ESCALATION"), default=3, lo=0, hi=64),
        max_evidence_reuse_rate=_clamp_int(os.getenv("AI_LAB_GUARD_MAX_EVIDENCE_REUSE_RATE"), default=8, lo=1, hi=256),
        reuse_window_seconds=_clamp_int(os.getenv("AI_LAB_GUARD_REUSE_WINDOW_SECONDS"), default=30, lo=5, hi=600),
        event_window_seconds=_clamp_int(os.getenv("AI_LAB_GUARD_EVENT_WINDOW_SECONDS"), default=60, lo=10, hi=1800),
        constrained_cooldown_seconds=_clamp_int(os.getenv("AI_LAB_GUARD_CONSTRAINED_COOLDOWN_SECONDS"), default=60, lo=5, hi=1800),
        safe_mode_cooldown_seconds=_clamp_int(os.getenv("AI_LAB_GUARD_SAFE_MODE_COOLDOWN_SECONDS"), default=120, lo=10, hi=3600),
    )


def reset_federation_cognitive_guards_state() -> None:
    """Test helper: resets in-memory cognitive guard state."""

    global _cg_state, _cg_state_until_ts
    global _cg_state_transitions_total, _cg_caps_applied_total, _cg_replay_detections_total
    global _cg_storm_detections_total, _cg_authority_escalations_total
    with _cg_lock:
        _cg_state = FederationGuardRuntimeState.NORMAL
        _cg_state_until_ts = 0.0
        _cg_events.clear()
        _cg_global_observations.clear()
        _cg_evidence_recent.clear()
        _cg_authority_escalation_ts.clear()
        _cg_event_counters.clear()
        _cg_state_transitions_total = 0
        _cg_caps_applied_total = 0
        _cg_replay_detections_total = 0
        _cg_storm_detections_total = 0
        _cg_authority_escalations_total = 0


def _now_ts(now: float | None) -> float:
    # We use wall-clock seconds only for bounded windows; this is not part of deterministic IDs.
    if now is not None:
        try:
            return float(now)
        except Exception:
            return float(time.time())
    return float(time.time())


def _push_event(*, now: float, event_type: FederationGuardEventType, severity: str, details: dict[str, Any]) -> None:
    # Always bounded; deterministic eviction via deque(maxlen).
    evt = {
        "ts": float(now),
        "type": event_type.value,
        "severity": str(severity or "info"),
        "details": dict(details or {}),
    }
    _cg_events.append(evt)
    _cg_event_counters[event_type.value] += 1


def _transition_state(*, now: float, new_state: FederationGuardRuntimeState, reason: str, cooldown_seconds: int) -> None:
    global _cg_state, _cg_state_until_ts, _cg_state_transitions_total
    if _cg_state == new_state and now <= _cg_state_until_ts:
        return
    _cg_state = new_state
    _cg_state_until_ts = float(now) + max(0, int(cooldown_seconds))
    _cg_state_transitions_total += 1
    if new_state == FederationGuardRuntimeState.SAFE_MODE:
        _push_event(
            now=now,
            event_type=FederationGuardEventType.safe_mode_transition,
            severity="critical",
            details={"reason": reason, "until_ts": float(_cg_state_until_ts)},
        )
    if new_state == FederationGuardRuntimeState.CONSTRAINED:
        _push_event(
            now=now,
            event_type=FederationGuardEventType.constrained_mode_transition,
            severity="warning",
            details={"reason": reason, "until_ts": float(_cg_state_until_ts)},
        )


def get_federation_guard_runtime_state(*, now: float | None = None) -> dict[str, Any]:
    global _cg_state, _cg_state_until_ts
    ts = _now_ts(now)
    with _cg_lock:
        # Auto-recover when cooldown expires.
        if _cg_state != FederationGuardRuntimeState.NORMAL and ts > float(_cg_state_until_ts or 0.0):
            _cg_state = FederationGuardRuntimeState.NORMAL
            _cg_state_until_ts = 0.0
        return {
            "contract_version": COGNITIVE_GUARDS_CONTRACT_VERSION,
            "state": _cg_state.value,
            "state_until_ts": float(_cg_state_until_ts or 0.0),
        }


def get_federation_guard_events(*, limit: int = 50) -> dict[str, Any]:
    lim = _clamp_int(limit, default=50, lo=1, hi=_CG_EVENTS_MAX)
    with _cg_lock:
        # Return most recent first, deterministic slice.
        items = list(_cg_events)[-lim:]
    items.reverse()
    return {
        "contract_version": COGNITIVE_GUARDS_CONTRACT_VERSION,
        "limit": int(lim),
        "events": items,
        "events_total": int(len(_cg_events)),
    }


def get_federation_guard_summary(*, now: float | None = None) -> dict[str, Any]:
    ts = _now_ts(now)
    st = get_federation_guard_runtime_state(now=ts)
    with _cg_lock:
        return {
            "contract_version": COGNITIVE_GUARDS_CONTRACT_VERSION,
            "timestamp": float(ts),
            "state": dict(st),
            "counters": {
                "state_transitions_total": int(_cg_state_transitions_total),
                "caps_applied_total": int(_cg_caps_applied_total),
                "replay_detections_total": int(_cg_replay_detections_total),
                "storm_detections_total": int(_cg_storm_detections_total),
                "authority_escalations_total": int(_cg_authority_escalations_total),
            },
            "event_counters": dict(_cg_event_counters),
        }


def _trim_window(dq: deque[float], *, now: float, window_seconds: int) -> None:
    cutoff = float(now) - float(window_seconds)
    while dq and float(dq[0]) < cutoff:
        dq.popleft()


def observe_federation_metadata_for_cognitive_guards(
    meta: dict[str, Any],
    *,
    caps: FederationPropagationCaps | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    """Observe federation metadata and return bounded cognitive guard annotations.

    This function NEVER raises. It also NEVER blocks routing.
    """

    global _cg_caps_applied_total, _cg_replay_detections_total, _cg_storm_detections_total, _cg_authority_escalations_total
    global _cg_state, _cg_state_until_ts

    ts = _now_ts(now)
    caps = caps or load_propagation_caps_from_env()
    annotations: dict[str, Any] = {
        "contract_version": COGNITIVE_GUARDS_CONTRACT_VERSION,
        "state": "NORMAL",
        "degraded": False,
        "caps_applied": [],
        "signals": {},
    }

    try:
        evidence_id = str(meta.get("_evidence_id") or "").strip()
        lineage_depth = _clamp_int(meta.get("_evidence_lineage_depth"), default=0, lo=0, hi=1024)
        reuse_count = _clamp_int(meta.get("_evidence_reuse_count"), default=0, lo=0, hi=10**9)

        fed = meta.get("_federation") if isinstance(meta.get("_federation"), dict) else {}
        domain = str(meta.get("_domain") or fed.get("domain") or "unknown")
        authority_weight = str(fed.get("authority_weight") or "")

        path = []
        try:
            p = fed.get("path")
            if isinstance(p, list):
                path = [str(x) for x in p if isinstance(x, str)]
        except Exception:
            path = []

        # Optional caller-provided signals (future-proof without coupling).
        propagation_fanout = _clamp_int(meta.get("_propagation_fanout"), default=1, lo=1, hi=10**6)
        authority_escalations = 0
        if authority_weight.lower() == "high" and str(domain).lower() != "authority":
            authority_escalations = 1

        annotations["signals"] = {
            "domain": domain,
            "authority_weight": authority_weight,
            "lineage_depth": int(lineage_depth),
            "reuse_count": int(reuse_count),
            "propagation_fanout": int(propagation_fanout),
            "path_depth": int(len(path)),
        }

        with _cg_lock:
            # Auto recover state if cooldown expired.
            if _cg_state != FederationGuardRuntimeState.NORMAL and ts > float(_cg_state_until_ts or 0.0):
                _cg_state = FederationGuardRuntimeState.NORMAL
                _cg_state_until_ts = 0.0

            # 1) Propagation caps (soft degradation: annotate only).
            if lineage_depth > int(caps.max_lineage_depth):
                annotations["degraded"] = True
                annotations["caps_applied"].append("max_lineage_depth")
                _cg_caps_applied_total += 1
                _push_event(
                    now=ts,
                    event_type=FederationGuardEventType.lineage_depth_exceeded,
                    severity="warning",
                    details={
                        "domain": domain,
                        "evidence_id": evidence_id,
                        "lineage_depth": int(lineage_depth),
                        "max": int(caps.max_lineage_depth),
                    },
                )

            if reuse_count > int(caps.max_replay_reuse):
                annotations["degraded"] = True
                annotations["caps_applied"].append("max_replay_reuse")
                _cg_caps_applied_total += 1
                _push_event(
                    now=ts,
                    event_type=FederationGuardEventType.propagation_cap_applied,
                    severity="warning",
                    details={
                        "cap": "max_replay_reuse",
                        "domain": domain,
                        "evidence_id": evidence_id,
                        "reuse_count": int(reuse_count),
                        "max": int(caps.max_replay_reuse),
                    },
                )

            if propagation_fanout > int(caps.max_propagation_fanout):
                annotations["degraded"] = True
                annotations["caps_applied"].append("max_propagation_fanout")
                _cg_caps_applied_total += 1
                _push_event(
                    now=ts,
                    event_type=FederationGuardEventType.propagation_cap_applied,
                    severity="warning",
                    details={
                        "cap": "max_propagation_fanout",
                        "domain": domain,
                        "fanout": int(propagation_fanout),
                        "max": int(caps.max_propagation_fanout),
                    },
                )

            if authority_escalations > 0:
                _cg_authority_escalations_total += 1
                _cg_authority_escalation_ts.append(float(ts))
                _push_event(
                    now=ts,
                    event_type=FederationGuardEventType.authority_escalation_detected,
                    severity="warning",
                    details={
                        "domain": domain,
                        "authority_weight": authority_weight,
                        "evidence_id": evidence_id,
                    },
                )

                # Cap repeated authority escalation pressure within window.
                _trim_window(_cg_authority_escalation_ts, now=ts, window_seconds=int(caps.event_window_seconds))
                if int(caps.max_authority_escalation) >= 0 and len(_cg_authority_escalation_ts) > int(caps.max_authority_escalation):
                    annotations["degraded"] = True
                    annotations["caps_applied"].append("max_authority_escalation")
                    _cg_caps_applied_total += 1
                    _push_event(
                        now=ts,
                        event_type=FederationGuardEventType.propagation_cap_applied,
                        severity="warning",
                        details={
                            "cap": "max_authority_escalation",
                            "count": int(len(_cg_authority_escalation_ts)),
                            "max": int(caps.max_authority_escalation),
                            "window_seconds": int(caps.event_window_seconds),
                        },
                    )
                    _transition_state(
                        now=ts,
                        new_state=FederationGuardRuntimeState.CONSTRAINED,
                        reason="authority_escalation_pressure",
                        cooldown_seconds=int(caps.constrained_cooldown_seconds),
                    )

            # 2) Replay amplification protection (bounded rate within window).
            if evidence_id:
                dq = _cg_evidence_recent.get(evidence_id)
                if dq is None:
                    dq = deque(maxlen=_cg_evidence_recent_max_per_id)
                    _cg_evidence_recent[evidence_id] = dq
                dq.append(float(ts))
                _trim_window(dq, now=ts, window_seconds=int(caps.reuse_window_seconds))
                reuse_rate = int(len(dq))

                # Bound the number of keys we keep to avoid unbounded growth.
                if len(_cg_evidence_recent) > int(_cg_evidence_recent_max_keys):
                    # Evict oldest-by-last-seen deterministically.
                    items = []
                    for k, v in _cg_evidence_recent.items():
                        last = float(v[-1]) if v else 0.0
                        items.append((last, k))
                    items.sort(key=lambda t: (t[0], t[1]))
                    while len(_cg_evidence_recent) > int(_cg_evidence_recent_max_keys) and items:
                        _, victim = items.pop(0)
                        if victim != evidence_id:
                            _cg_evidence_recent.pop(victim, None)

                _cg_global_observations.append((float(ts), evidence_id))
                # Trim global window.
                cutoff = float(ts) - float(int(caps.event_window_seconds))
                while _cg_global_observations and float(_cg_global_observations[0][0]) < cutoff:
                    _cg_global_observations.popleft()

                if reuse_rate > int(caps.max_evidence_reuse_rate):
                    _cg_replay_detections_total += 1
                    annotations["degraded"] = True
                    _push_event(
                        now=ts,
                        event_type=FederationGuardEventType.replay_detected,
                        severity="warning",
                        details={
                            "domain": domain,
                            "evidence_id": evidence_id,
                            "reuse_rate": int(reuse_rate),
                            "window_seconds": int(caps.reuse_window_seconds),
                            "max": int(caps.max_evidence_reuse_rate),
                        },
                    )
                    _transition_state(
                        now=ts,
                        new_state=FederationGuardRuntimeState.CONSTRAINED,
                        reason="replay_amplification",
                        cooldown_seconds=int(caps.constrained_cooldown_seconds),
                    )

                # 3) Cognitive storm detection (light heuristics, no scans).
                # Heuristic A: evidence concentration spike in event window.
                counts: Counter[str] = Counter(eid for _, eid in _cg_global_observations)
                total = int(sum(counts.values()))
                top_eid, top_count = ("", 0)
                if counts:
                    top_eid, top_count = max(counts.items(), key=lambda kv: (kv[1], kv[0]))

                concentration = 0.0
                if total > 0:
                    concentration = float(top_count) / float(total)

                # Trigger storm when volume is high and concentration is high.
                if total >= 24 and concentration >= 0.7:
                    _cg_storm_detections_total += 1
                    annotations["degraded"] = True
                    _push_event(
                        now=ts,
                        event_type=FederationGuardEventType.replay_detected,
                        severity="error",
                        details={
                            "domain": domain,
                            "pattern": "evidence_concentration_spike",
                            "top_evidence_id": top_eid,
                            "top_count": int(top_count),
                            "total": int(total),
                            "concentration": float(round(concentration, 4)),
                            "window_seconds": int(caps.event_window_seconds),
                        },
                    )
                    _transition_state(
                        now=ts,
                        new_state=FederationGuardRuntimeState.SAFE_MODE,
                        reason="cognitive_storm",
                        cooldown_seconds=int(caps.safe_mode_cooldown_seconds),
                    )

            # Export effective state (avoid re-entrant lock usage).
            annotations["state"] = _cg_state.value

        # Bounded, deterministic list ordering.
        annotations["caps_applied"] = sorted(set(annotations["caps_applied"]), key=lambda s: str(s))

    except Exception as exc:
        # Fail-safe.
        with _cg_lock:
            _push_event(
                now=ts,
                event_type=FederationGuardEventType.propagation_cap_applied,
                severity="critical",
                details={"error": str(exc)[:200]},
            )
        annotations["degraded"] = True
        annotations["state"] = "DEGRADED"

    return {
        "_cognitive_guard": annotations,
        "_guard_state": annotations.get("state", "NORMAL"),
        "_guard_degraded": bool(annotations.get("degraded")),
    }


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
