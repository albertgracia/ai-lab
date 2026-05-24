"""COGNITIVE-SLO-01: bounded cognitive runtime SLO framework.

Purpose: formalise what "runtime healthy" means for AI-LAB as a federated
cognitive platform. This is governance + observability — NOT adaptive cognition.

Hard rules:
- Deterministic, bounded, fail-safe.
- No persistence, no databases, no background threads.
- No routing decisions; SLOs only observe, classify, and expose.
- No imports from gateway or routing modules (avoids circular coupling).
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import Any


SLO_CONTRACT_VERSION = "SLO-01"


class SLOStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    DEGRADED = "degraded"
    CRITICAL = "critical"


class SLOSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SLOEvaluation(str, Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


@dataclass(frozen=True)
class SLODefinition:
    """Immutable SLO definition — single source of truth for a threshold."""

    name: str
    category: str
    description: str
    warning_threshold: float
    critical_threshold: float
    severity: SLOSeverity
    recovery_window_seconds: int
    higher_is_better: bool = False
    unit: str = ""


@dataclass(frozen=True)
class SLOViolation:
    """A single SLO violation event — immutable, bounded."""

    slo_name: str
    category: str
    status: SLOStatus
    current_value: float
    threshold: float
    timestamp: float
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "slo_name": self.slo_name,
            "category": self.category,
            "status": self.status.value,
            "current_value": float(self.current_value),
            "threshold": float(self.threshold),
            "timestamp": float(self.timestamp),
            "description": str(self.description),
        }


@dataclass(frozen=True)
class SLOSnapshot:
    """Point-in-time snapshot of all SLO evaluations + violations."""

    timestamp: float
    contract_version: str
    slos: list[dict[str, Any]]
    overall_status: SLOStatus
    violations_total: int
    violations_recent: list[dict[str, Any]]
    last_updated: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": float(self.timestamp),
            "contract_version": self.contract_version,
            "slos": list(self.slos),
            "overall_status": self.overall_status.value,
            "violations_total": int(self.violations_total),
            "violations_recent": list(self.violations_recent),
            "last_updated": float(self.last_updated),
        }


# ── SLO definitions ──────────────────────────────────────────────────────

SLO_DEFINITIONS: list[SLODefinition] = [
    # A) Federation SLOs (absolute counter values, no time-window rates)
    SLODefinition(
        name="federation_caps_applied",
        category="federation",
        description="Propagation caps applied (total)",
        warning_threshold=50.0,
        critical_threshold=200.0,
        severity=SLOSeverity.WARNING,
        recovery_window_seconds=120,
    ),
    SLODefinition(
        name="federation_replay_detections",
        category="federation",
        description="Evidence replay detections (total)",
        warning_threshold=10.0,
        critical_threshold=30.0,
        severity=SLOSeverity.WARNING,
        recovery_window_seconds=120,
    ),
    SLODefinition(
        name="federation_storm_detections",
        category="federation",
        description="Storm detections (total)",
        warning_threshold=3.0,
        critical_threshold=8.0,
        severity=SLOSeverity.ERROR,
        recovery_window_seconds=300,
    ),
    SLODefinition(
        name="federation_safe_mode_transitions",
        category="federation",
        description="SAFE_MODE transitions (total)",
        warning_threshold=2.0,
        critical_threshold=5.0,
        severity=SLOSeverity.CRITICAL,
        recovery_window_seconds=600,
    ),
    SLODefinition(
        name="federation_lineage_depth",
        category="federation",
        description="Max evidence lineage depth",
        warning_threshold=6.0,
        critical_threshold=12.0,
        severity=SLOSeverity.WARNING,
        recovery_window_seconds=120,
    ),
    # B) Latency SLOs
    SLODefinition(
        name="latency_completion_p50",
        category="latency",
        description="P50 completion latency in ms",
        warning_threshold=2000.0,
        critical_threshold=5000.0,
        severity=SLOSeverity.WARNING,
        recovery_window_seconds=120,
        unit="ms",
    ),
    SLODefinition(
        name="latency_completion_p95",
        category="latency",
        description="P95 completion latency in ms",
        warning_threshold=8000.0,
        critical_threshold=15000.0,
        severity=SLOSeverity.ERROR,
        recovery_window_seconds=300,
        unit="ms",
    ),
    SLODefinition(
        name="latency_streaming_ttfb",
        category="latency",
        description="TTFB for streaming completions in ms",
        warning_threshold=3000.0,
        critical_threshold=8000.0,
        severity=SLOSeverity.WARNING,
        recovery_window_seconds=120,
        unit="ms",
    ),
    SLODefinition(
        name="latency_registry_endpoint",
        category="latency",
        description="Registry endpoint response time in ms",
        warning_threshold=500.0,
        critical_threshold=2000.0,
        severity=SLOSeverity.WARNING,
        recovery_window_seconds=60,
        unit="ms",
    ),
    # C) Availability SLOs
    SLODefinition(
        name="availability_gateway",
        category="availability",
        description="Gateway health check success (1=up)",
        warning_threshold=0.95,
        critical_threshold=0.80,
        severity=SLOSeverity.CRITICAL,
        recovery_window_seconds=60,
        higher_is_better=True,
    ),
    SLODefinition(
        name="availability_lmstudio",
        category="availability",
        description="LM Studio reachability (1=up)",
        warning_threshold=0.90,
        critical_threshold=0.70,
        severity=SLOSeverity.CRITICAL,
        recovery_window_seconds=120,
        higher_is_better=True,
    ),
    SLODefinition(
        name="availability_prometheus",
        category="availability",
        description="Prometheus scrape success rate",
        warning_threshold=0.90,
        critical_threshold=0.70,
        severity=SLOSeverity.ERROR,
        recovery_window_seconds=120,
        higher_is_better=True,
    ),
    # D) Cognitive integrity SLOs
    SLODefinition(
        name="integrity_invalid_lineage_ratio",
        category="cognitive_integrity",
        description="Ratio of invalid lineage to total propagations",
        warning_threshold=0.10,
        critical_threshold=0.25,
        severity=SLOSeverity.ERROR,
        recovery_window_seconds=300,
    ),
    SLODefinition(
        name="integrity_stale_evidence_ratio",
        category="cognitive_integrity",
        description="Ratio of stale evidence to total propagations",
        warning_threshold=0.15,
        critical_threshold=0.30,
        severity=SLOSeverity.WARNING,
        recovery_window_seconds=300,
    ),
    SLODefinition(
        name="integrity_registry_consistency",
        category="cognitive_integrity",
        description="Registry canonical count (expected >= 2 routable models)",
        warning_threshold=2.0,
        critical_threshold=1.0,
        severity=SLOSeverity.ERROR,
        recovery_window_seconds=60,
        higher_is_better=True,
    ),
    SLODefinition(
        name="integrity_deprecated_alias",
        category="cognitive_integrity",
        description="Deprecated alias detected in LM Studio (0 = clean)",
        warning_threshold=0.0,
        critical_threshold=0.0,
        severity=SLOSeverity.CRITICAL,
        recovery_window_seconds=300,
    ),
    # E) Recovery SLOs
    SLODefinition(
        name="recovery_degraded_to_normal",
        category="recovery",
        description="Time to recover from DEGRADED to NORMAL in seconds",
        warning_threshold=120.0,
        critical_threshold=300.0,
        severity=SLOSeverity.WARNING,
        recovery_window_seconds=600,
        unit="s",
    ),
    SLODefinition(
        name="recovery_safe_mode_max_duration",
        category="recovery",
        description="Max duration in SAFE_MODE before auto-recovery in seconds",
        warning_threshold=180.0,
        critical_threshold=360.0,
        severity=SLOSeverity.CRITICAL,
        recovery_window_seconds=600,
        unit="s",
    ),
    SLODefinition(
        name="recovery_cooldown_success",
        category="recovery",
        description="Cooldown recovery success rate",
        warning_threshold=0.90,
        critical_threshold=0.75,
        severity=SLOSeverity.ERROR,
        recovery_window_seconds=300,
        higher_is_better=True,
    ),
]

# ── In-memory state — bounded, thread-safe ──────────────────────────────

_slo_lock = Lock()
_slo_violations: deque[SLOViolation] = deque(maxlen=256)
_slo_violations_total = 0
_slo_degraded_total = 0
_slo_safe_mode_total = 0
_slo_last_evaluation_ts: float = 0.0
_slo_current_status: SLOStatus = SLOStatus.HEALTHY

# Latency tracking (bounded sliding windows for SLO evaluation)
_latency_window: deque[float] = deque(maxlen=512)
_streaming_latency_window: deque[float] = deque(maxlen=128)
_registry_latency_window: deque[float] = deque(maxlen=64)


def _clamp_int(val: Any, *, default: int, lo: int, hi: int) -> int:
    try:
        i = int(val)
        return max(int(lo), min(int(hi), i))
    except Exception:
        return int(default)


def _now_ts(now: float | None) -> float:
    return float(now) if now is not None else float(time.time())


def _prune_window(dq: deque[float], *, now: float, window_seconds: int) -> None:
    cutoff = float(now) - float(window_seconds)
    while dq and float(dq[0]) < cutoff:
        dq.popleft()


def _percentile(data: list[float], pct: float) -> float:
    if not data:
        return 0.0
    idx = max(0, min(len(data) - 1, int(len(data) * pct / 100.0)))
    return float(data[idx])


def _overall_status_from_slos(evaluations: list[dict[str, Any]]) -> SLOStatus:
    levels = [SLOStatus.HEALTHY, SLOStatus.WARNING, SLOStatus.DEGRADED, SLOStatus.CRITICAL]
    rank = {s: i for i, s in enumerate(levels)}
    worst = SLOStatus.HEALTHY
    for ev in evaluations:
        try:
            s = SLOStatus(ev.get("status", "healthy"))
            if rank.get(s, 0) > rank.get(worst, 0):
                worst = s
        except Exception:
            pass
    return worst


def _record_violation(v: SLOViolation) -> None:
    global _slo_violations_total, _slo_degraded_total, _slo_safe_mode_total
    _slo_violations.append(v)
    _slo_violations_total += 1
    if v.status in (SLOStatus.DEGRADED, SLOStatus.CRITICAL):
        _slo_degraded_total += 1
    if v.status == SLOStatus.CRITICAL:
        _slo_safe_mode_total += 1


# ── Public API ───────────────────────────────────────────────────────────

def reset_slo_state() -> None:
    """Test helper: resets all SLO state."""

    global _slo_violations_total, _slo_degraded_total, _slo_safe_mode_total
    global _slo_last_evaluation_ts, _slo_current_status
    with _slo_lock:
        _slo_violations.clear()
        _slo_violations_total = 0
        _slo_degraded_total = 0
        _slo_safe_mode_total = 0
        _slo_last_evaluation_ts = 0.0
        _slo_current_status = SLOStatus.HEALTHY
        _latency_window.clear()
        _streaming_latency_window.clear()
        _registry_latency_window.clear()


def record_latency(latency_ms: float, *, stream: bool = False, endpoint: str = "") -> None:
    """Record a latency sample for SLO evaluation windows."""

    with _slo_lock:
        _latency_window.append(float(latency_ms))
        if stream:
            _streaming_latency_window.append(float(latency_ms))
        if "registry" in endpoint.lower() or "models" in endpoint.lower():
            _registry_latency_window.append(float(latency_ms))


def _evaluate_one(
    slo: SLODefinition,
    current_value: float,
    now: float,
) -> dict[str, Any]:
    """Evaluate a single SLO and record violations if thresholds exceeded.

    Returns a dict with name, category, status, current_value, violated.
    """
    violated = False
    status = SLOStatus.HEALTHY
    warning_exceeded = False
    critical_exceeded = False

    if slo.higher_is_better:
        if current_value < slo.critical_threshold:
            critical_exceeded = True
        elif current_value < slo.warning_threshold:
            warning_exceeded = True
    else:
        if current_value > slo.critical_threshold:
            critical_exceeded = True
        elif current_value > slo.warning_threshold:
            warning_exceeded = True

    if critical_exceeded:
        status = SLOStatus.CRITICAL
        violated = True
    elif warning_exceeded:
        status = SLOStatus.WARNING
        violated = True

    if violated:
        threshold = slo.critical_threshold if critical_exceeded else slo.warning_threshold
        sev = slo.severity
        if status == SLOStatus.CRITICAL:
            sev = SLOSeverity.CRITICAL
        elif status == SLOStatus.WARNING:
            sev = slo.severity
        v = SLOViolation(
            slo_name=slo.name,
            category=slo.category,
            status=status,
            current_value=float(current_value),
            threshold=float(threshold),
            timestamp=now,
            description=f"{slo.description}: {current_value}{slo.unit} (threshold: {threshold}{slo.unit})",
        )
        _record_violation(v)

    return {
        "name": slo.name,
        "category": slo.category,
        "status": status.value,
        "current_value": float(current_value),
        "warning_threshold": float(slo.warning_threshold),
        "critical_threshold": float(slo.critical_threshold),
        "violated": violated,
        "severity": sev.value if violated else "info",
        "unit": slo.unit,
        "description": slo.description,
    }


def evaluate_slos(
    *,
    now: float | None = None,
    guard_summary: dict[str, Any] | None = None,
    evidence_summary: dict[str, Any] | None = None,
    registry_snapshot: dict[str, Any] | None = None,
    lmstudio_up: float = 1.0,
    gateway_up: float = 1.0,
    prometheus_up: float = 1.0,
) -> dict[str, Any]:
    """Evaluate all SLOs against current runtime state.

    All parameters optional — missing values use defaults (healthy).
    Always returns a deterministic, bounded snapshot.
    """
    global _slo_last_evaluation_ts, _slo_current_status

    ts = _now_ts(now)
    evaluations: list[dict[str, Any]] = []

    # Extract guard counters (fail-safe defaults)
    guard_counters = {}
    guard_state = ""
    if isinstance(guard_summary, dict):
        guard_counters = guard_summary.get("counters") or {}
        state_obj = guard_summary.get("state") or {}
        guard_state = str(state_obj.get("state", "")) if isinstance(state_obj, dict) else ""

    replay_total = float(guard_counters.get("replay_detections_total", 0) or 0)
    storm_total = float(guard_counters.get("storm_detections_total", 0) or 0)
    safe_mode_total = float(guard_counters.get("authority_escalations_total", 0) or 0)
    caps_total = float(guard_counters.get("caps_applied_total", 0) or 0)

    # Extract evidence counters
    evidence_props = 0.0
    stale_total = 0.0
    invalid_total = 0.0
    lineage_depth = 0.0
    if isinstance(evidence_summary, dict):
        evidence_props = float(evidence_summary.get("evidence_propagations_total", 0) or 0)
        stale_total = float(evidence_summary.get("stale_evidence_total", 0) or 0)
        invalid_total = float(evidence_summary.get("invalid_lineage_total", 0) or 0)
        lineage_depth = float(evidence_summary.get("lineage_depth_max", 0) or 0)

    # Extract registry data
    registry_models = 0.0
    if isinstance(registry_snapshot, dict):
        registry_models = float(registry_snapshot.get("routable_total", 0) or 0)

    # Compute ratios safely
    stale_ratio = stale_total / max(1.0, evidence_props)
    invalid_ratio = invalid_total / max(1.0, evidence_props)

    # Latency percentiles from sliding windows
    with _slo_lock:
        lat_list = sorted(_latency_window)
        stream_list = sorted(_streaming_latency_window)
        reg_list = sorted(_registry_latency_window)
    latency_p50 = _percentile(lat_list, 50)
    latency_p95 = _percentile(lat_list, 95)
    streaming_p50 = _percentile(stream_list, 50)
    registry_p50 = _percentile(reg_list, 50)

    # Evaluate each SLO definition (uses absolute counter values, not rates)
    for slo in SLO_DEFINITIONS:
        if slo.name == "federation_caps_applied":
            ev = _evaluate_one(slo, caps_total, ts)
        elif slo.name == "federation_replay_detections":
            ev = _evaluate_one(slo, replay_total, ts)
        elif slo.name == "federation_storm_detections":
            ev = _evaluate_one(slo, storm_total, ts)
        elif slo.name == "federation_safe_mode_transitions":
            ev = _evaluate_one(slo, safe_mode_total, ts)
        elif slo.name == "federation_lineage_depth":
            ev = _evaluate_one(slo, lineage_depth, ts)
        elif slo.name == "latency_completion_p50":
            ev = _evaluate_one(slo, latency_p50, ts)
        elif slo.name == "latency_completion_p95":
            ev = _evaluate_one(slo, latency_p95, ts)
        elif slo.name == "latency_streaming_ttfb":
            ev = _evaluate_one(slo, streaming_p50, ts)
        elif slo.name == "latency_registry_endpoint":
            ev = _evaluate_one(slo, registry_p50, ts)
        elif slo.name == "availability_gateway":
            ev = _evaluate_one(slo, gateway_up, ts)
        elif slo.name == "availability_lmstudio":
            ev = _evaluate_one(slo, lmstudio_up, ts)
        elif slo.name == "availability_prometheus":
            ev = _evaluate_one(slo, prometheus_up, ts)
        elif slo.name == "integrity_invalid_lineage_ratio":
            ev = _evaluate_one(slo, invalid_ratio, ts)
        elif slo.name == "integrity_stale_evidence_ratio":
            ev = _evaluate_one(slo, stale_ratio, ts)
        elif slo.name == "integrity_registry_consistency":
            ev = _evaluate_one(slo, registry_models, ts)
        elif slo.name == "integrity_deprecated_alias":
            ev = _evaluate_one(slo, 0.0, ts)
        elif slo.name == "recovery_degraded_to_normal":
            ev = _evaluate_one(slo, 0.0, ts)
        elif slo.name == "recovery_safe_mode_max_duration":
            ev = _evaluate_one(slo, 0.0, ts)
        elif slo.name == "recovery_cooldown_success":
            ev = _evaluate_one(slo, 1.0, ts)
        else:
            ev = {
                "name": slo.name,
                "category": slo.category,
                "status": "healthy",
                "current_value": 0.0,
                "warning_threshold": float(slo.warning_threshold),
                "critical_threshold": float(slo.critical_threshold),
                "violated": False,
                "severity": "info",
                "unit": slo.unit,
                "description": slo.description,
            }
        evaluations.append(ev)

    with _slo_lock:
        overall = _overall_status_from_slos(evaluations)
        _slo_current_status = overall
        _slo_last_evaluation_ts = ts
        violations_recent = [v.to_dict() for v in list(_slo_violations)[-50:]]
        violations_recent.reverse()
        violations_total = int(_slo_violations_total)

    return SLOSnapshot(
        timestamp=ts,
        contract_version=SLO_CONTRACT_VERSION,
        slos=evaluations,
        overall_status=overall,
        violations_total=violations_total,
        violations_recent=violations_recent,
        last_updated=ts,
    ).to_dict()


def get_slo_summary(*, now: float | None = None) -> dict[str, Any]:
    """Return current SLO summary (read-only, fail-safe)."""

    return evaluate_slos(now=now)


def get_slo_status(*, now: float | None = None) -> dict[str, Any]:
    """Return compact SLO status (read-only, fail-safe)."""

    ts = _now_ts(now)
    with _slo_lock:
        violations_total = int(_slo_violations_total)
        degraded_total = int(_slo_degraded_total)
        safe_mode_total = int(_slo_safe_mode_total)
        status = _slo_current_status.value

    return {
        "contract_version": SLO_CONTRACT_VERSION,
        "timestamp": float(ts),
        "overall_status": status,
        "violations_total": violations_total,
        "degraded_total": degraded_total,
        "safe_mode_total": safe_mode_total,
    }


def get_slo_violations(*, limit: int = 50) -> dict[str, Any]:
    """Return recent SLO violations (read-only, FIFO bounded)."""

    lim = max(1, min(256, int(limit)))
    with _slo_lock:
        items = [v.to_dict() for v in list(_slo_violations)[-lim:]]
        items.reverse()
        total = int(_slo_violations_total)

    return {
        "contract_version": SLO_CONTRACT_VERSION,
        "limit": int(lim),
        "violations_total": total,
        "violations": items,
    }


def build_slo_prometheus_metrics(
    guard_summary: dict[str, Any] | None = None,
    evidence_summary: dict[str, Any] | None = None,
    registry_snapshot: dict[str, Any] | None = None,
    lmstudio_up: float = 1.0,
    gateway_up: float = 1.0,
) -> str:
    """Render SLO metrics as Prometheus text format (fail-safe)."""

    try:
        snap = evaluate_slos(
            guard_summary=guard_summary,
            evidence_summary=evidence_summary,
            registry_snapshot=registry_snapshot,
            lmstudio_up=lmstudio_up,
            gateway_up=gateway_up,
        )
        violations_total = float(snap.get("violations_total", 0) or 0)
        slos = snap.get("slos", [])
        degraded_count = 0
        safe_mode_count = 0
        for ev in slos:
            if ev.get("status") in ("degraded", "critical"):
                degraded_count += 1
            if ev.get("status") == "critical":
                safe_mode_count += 1

        registry_ok = 1.0
        for ev in slos:
            if ev.get("name") == "integrity_registry_consistency" and ev.get("status") == "healthy":
                registry_ok = 1.0
                break

        gw_ok = 1.0
        for ev in slos:
            if ev.get("name") == "availability_gateway" and ev.get("status") == "healthy":
                gw_ok = 1.0
                break

        lm_ok = 1.0
        for ev in slos:
            if ev.get("name") == "availability_lmstudio" and ev.get("status") == "healthy":
                lm_ok = 1.0
                break

        return (
            f"ailab_slo_violations_total {violations_total}\n"
            f"ailab_slo_degraded_total {float(degraded_count)}\n"
            f"ailab_slo_safe_mode_total {float(safe_mode_count)}\n"
            f"ailab_slo_registry_consistency {float(registry_ok)}\n"
            f"ailab_slo_gateway_health {float(gw_ok)}\n"
            f"ailab_slo_lmstudio_health {float(lm_ok)}\n"
        )
    except Exception:
        return (
            "ailab_slo_violations_total 0\n"
            "ailab_slo_degraded_total 0\n"
            "ailab_slo_safe_mode_total 0\n"
            "ailab_slo_registry_consistency 1\n"
            "ailab_slo_gateway_health 1\n"
            "ailab_slo_lmstudio_health 1\n"
        )
