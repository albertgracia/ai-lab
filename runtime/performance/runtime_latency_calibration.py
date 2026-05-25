from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable

from runtime.performance.contracts import (
    RuntimeLatencyContract,
    GovernanceLatencyContract,
    ValidationLatencyContract,
)


PERFORMANCE_CONTRACT_VERSION = "34C"

_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, dict[str, Any]] = {}
_CACHE_HITS = 0
_CACHE_MISSES = 0

_ASYNC_LOCK = threading.Lock()
_ASYNC_STARTED = False


def _strict_mode() -> bool:
    return os.environ.get("STRICT_VALIDATION_MODE", "false").lower() in ("true", "1", "yes")


def _now() -> float:
    # Determinism: no clock influence.
    return 0.0 if _strict_mode() else time.time()


def _hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _artifact_enabled() -> bool:
    # Safe to leave enabled in prod: these are small, local /tmp files.
    return os.environ.get("AI_LAB_ENABLE_PERFORMANCE_ARTIFACTS", "true").lower() in ("true", "1", "yes")


def _write_artifact(path: str, payload: dict[str, Any]) -> None:
    if not _artifact_enabled():
        return
    try:
        p = Path(path)
        # Avoid huge dumps.
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str)
        if len(raw) > 200_000:
            raw = raw[:200_000] + "\n"  # truncate
        p.write_text(raw + "\n", encoding="utf-8")
    except Exception:
        pass


def _get_cached(key: str, builder: Callable[[], Any], *, ttl_s: int = 5) -> tuple[Any, bool]:
    """Small deterministic cache with TTL.

    In STRICT mode, time is frozen => TTL never expires within the same process,
    preserving deterministic fast execution.
    """
    global _CACHE_HITS, _CACHE_MISSES
    now = _now()
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry is not None:
            age = now - float(entry.get("ts", 0.0))
            if age <= float(entry.get("ttl_s", ttl_s)):
                _CACHE_HITS += 1
                try:
                    from runtime.telemetry.prometheus_metrics import record_cache_event
                    record_cache_event("performance_cache", hit=True)
                except Exception:
                    pass
                return entry.get("value"), True

    _CACHE_MISSES += 1
    try:
        from runtime.telemetry.prometheus_metrics import record_cache_event
        record_cache_event("performance_cache", hit=False)
    except Exception:
        pass
    value = builder()
    with _CACHE_LOCK:
        _CACHE[key] = {"value": value, "ts": now, "ttl_s": int(ttl_s)}
    return value, False


def get_performance_cache_state() -> dict[str, Any]:
    with _CACHE_LOCK:
        entries = len(_CACHE)
    return {
        "contract_version": PERFORMANCE_CONTRACT_VERSION,
        "cache_entries": entries,
        "cache_hits": _CACHE_HITS,
        "cache_misses": _CACHE_MISSES,
        "freshness": "fresh" if entries > 0 else "unknown",
        "generated_at": _now(),
    }


def compress_operational_noise(text: str | None, *, level: str = "operational") -> str:
    """Reduce repeated warnings/disclaimers in operational outputs."""
    t = (text or "").strip()
    if not t:
        return ""
    lines = [ln.rstrip() for ln in t.splitlines() if ln.strip()]
    # De-dup exact lines while preserving order.
    seen = set()
    uniq = []
    for ln in lines:
        if ln in seen:
            continue
        seen.add(ln)
        uniq.append(ln)

    max_lines = 12 if level in ("minimal", "operational") else 40
    max_chars = 900 if level in ("minimal", "operational") else 4000
    out = "\n".join(uniq[:max_lines]).strip()
    truncated = False
    if len(out) > max_chars:
        out = out[:max_chars].rstrip()
        truncated = True
    try:
        if out != t or truncated:
            from runtime.telemetry.prometheus_metrics import record_semantic_noise_event
            record_semantic_noise_event("dedup" if out != t else "truncate")
    except Exception:
        pass
    return out


def build_latency_breakdown(samples: dict[str, float]) -> dict[str, Any]:
    ordered = {k: float(samples[k]) for k in sorted(samples)}
    total_ms = round(sum(ordered.values()), 2)
    return {
        "contract_version": PERFORMANCE_CONTRACT_VERSION,
        "total_ms": total_ms,
        "breakdown_ms": ordered,
        "generated_at": _now(),
        "deterministic_signature": _hash({"total_ms": total_ms, "breakdown_ms": ordered}),
    }


def detect_governance_friction(governance_ms: float) -> dict[str, Any]:
    # Heuristic threshold: governance should be cheap.
    friction = float(governance_ms) > 60.0
    return {
        "contract_version": PERFORMANCE_CONTRACT_VERSION,
        "governance_ms": float(governance_ms),
        "friction_detected": bool(friction),
        "generated_at": _now(),
    }


def detect_validation_overhead(validation_ms: float) -> dict[str, Any]:
    overhead = float(validation_ms) > 120.0
    return {
        "contract_version": PERFORMANCE_CONTRACT_VERSION,
        "validation_ms": float(validation_ms),
        "overhead_detected": bool(overhead),
        "generated_at": _now(),
    }


def calculate_runtime_performance_score(breakdown: dict[str, Any]) -> dict[str, Any]:
    total_ms = float(breakdown.get("total_ms", 0.0) or 0.0)
    # Score: 100 at 0ms, 50 at 500ms, clamp.
    score = 100.0
    if total_ms > 0:
        score = max(0.0, min(100.0, 100.0 - (total_ms / 10.0)))
    level = "high" if score >= 80 else "medium" if score >= 55 else "low" if score >= 35 else "critical"
    return {
        "contract_version": PERFORMANCE_CONTRACT_VERSION,
        "runtime_performance_score": round(score, 1),
        "runtime_performance_level": level,
        "total_ms": round(total_ms, 2),
        "generated_at": _now(),
        "deterministic_signature": _hash({"score": round(score, 1), "total_ms": round(total_ms, 2)}),
    }


def profile_governance_latency(extra_ctx: dict[str, Any] | None = None, sensor_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}
    # FASE 34C: default to fastpath governance for latency calibration.
    extra_ctx = {**extra_ctx, "fastpath": bool(extra_ctx.get("fastpath", True))}
    sensor_snapshot = sensor_snapshot or {}

    def _build():
        start = time.perf_counter()
        try:
            from runtime.governance import build_runtime_governance_registry
            build_runtime_governance_registry(extra_ctx=extra_ctx, sensor_snapshot=sensor_snapshot)
        except Exception:
            pass
        return round((time.perf_counter() - start) * 1000.0, 2)

    ms, used_cache = _get_cached("latency:governance", _build, ttl_s=3)
    try:
        from runtime.telemetry.prometheus_metrics import record_governance_latency_ms
        record_governance_latency_ms(float(ms))
    except Exception:
        pass
    friction = detect_governance_friction(float(ms))
    contract = GovernanceLatencyContract(
        contract_version=PERFORMANCE_CONTRACT_VERSION,
        governance_ms=float(ms),
        friction_detected=bool(friction.get("friction_detected")),
        generated_at=_now(),
    ).to_dict()
    contract["used_cache"] = used_cache
    _write_artifact("/tmp/34c-governance-pressure.json", {"governance": contract, "friction": friction})
    return contract


def profile_validation_latency(extra_ctx: dict[str, Any] | None = None, sensor_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}
    extra_ctx = {**extra_ctx, "fastpath": bool(extra_ctx.get("fastpath", True))}
    sensor_snapshot = sensor_snapshot or {}

    def _build():
        start = time.perf_counter()
        try:
            from runtime.validation.runtime_validation_framework import build_runtime_validation_report
            build_runtime_validation_report(sensor_snapshot=sensor_snapshot, extra_ctx=extra_ctx)
        except Exception:
            pass
        return round((time.perf_counter() - start) * 1000.0, 2)

    ms, used_cache = _get_cached("latency:validation", _build, ttl_s=3)
    try:
        from runtime.telemetry.prometheus_metrics import record_validation_latency_ms
        record_validation_latency_ms(float(ms))
    except Exception:
        pass
    overhead = detect_validation_overhead(float(ms))
    contract = ValidationLatencyContract(
        contract_version=PERFORMANCE_CONTRACT_VERSION,
        validation_ms=float(ms),
        overhead_detected=bool(overhead.get("overhead_detected")),
        generated_at=_now(),
    ).to_dict()
    contract["used_cache"] = used_cache
    _write_artifact("/tmp/34c-validation-overhead.json", {"validation": contract, "overhead": overhead})
    return contract


def profile_reporting_latency(extra_ctx: dict[str, Any] | None = None, sensor_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}
    sensor_snapshot = sensor_snapshot or {}

    def _build():
        start = time.perf_counter()
        # Reporting is a consumer of performance facts. Do not import reporting
        # here; keep the key for contract stability and mark it decoupled.
        _ = (extra_ctx, sensor_snapshot)
        return round((time.perf_counter() - start) * 1000.0, 2)

    ms, used_cache = _get_cached("latency:reporting", _build, ttl_s=3)
    return {
        "contract_version": PERFORMANCE_CONTRACT_VERSION,
        "reporting_ms": float(ms),
        "used_cache": used_cache,
        "measurement": "decoupled",
        "generated_at": _now(),
    }


def profile_observability_latency(extra_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}

    def _build():
        start = time.perf_counter()
        try:
            from runtime.observability import run_live_observability_diagnostics
            run_live_observability_diagnostics(extra_ctx=extra_ctx)
        except Exception:
            pass
        return round((time.perf_counter() - start) * 1000.0, 2)

    ms, used_cache = _get_cached("latency:observability", _build, ttl_s=3)
    return {
        "contract_version": PERFORMANCE_CONTRACT_VERSION,
        "observability_ms": float(ms),
        "used_cache": used_cache,
        "generated_at": _now(),
    }


def profile_grounding_latency(extra_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}

    def _build():
        start = time.perf_counter()
        try:
            from runtime.context.runtime_grounding import build_grounding_envelope
            build_grounding_envelope()
        except Exception:
            pass
        return round((time.perf_counter() - start) * 1000.0, 2)

    ms, used_cache = _get_cached("latency:grounding", _build, ttl_s=3)
    return {
        "contract_version": PERFORMANCE_CONTRACT_VERSION,
        "grounding_ms": float(ms),
        "used_cache": used_cache,
        "generated_at": _now(),
    }


def profile_runtime_latency(extra_ctx: dict[str, Any] | None = None, sensor_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}
    sensor_snapshot = sensor_snapshot or {}

    samples: dict[str, float] = {}

    start_total = time.perf_counter()

    g = profile_governance_latency(extra_ctx, sensor_snapshot)
    samples["governance_ms"] = float(g.get("governance_ms", 0.0) or 0.0)

    v = profile_validation_latency(extra_ctx, sensor_snapshot)
    samples["validation_ms"] = float(v.get("validation_ms", 0.0) or 0.0)

    r = profile_reporting_latency(extra_ctx, sensor_snapshot)
    samples["reporting_ms"] = float(r.get("reporting_ms", 0.0) or 0.0)

    o = profile_observability_latency(extra_ctx)
    samples["observability_ms"] = float(o.get("observability_ms", 0.0) or 0.0)

    gr = profile_grounding_latency(extra_ctx)
    samples["grounding_ms"] = float(gr.get("grounding_ms", 0.0) or 0.0)

    total_ms = round((time.perf_counter() - start_total) * 1000.0, 2)

    breakdown = build_latency_breakdown(samples)
    contract = RuntimeLatencyContract(
        contract_version=PERFORMANCE_CONTRACT_VERSION,
        total_ms=total_ms,
        breakdown_ms=breakdown.get("breakdown_ms", {}),
        generated_at=_now(),
    ).to_dict()
    contract["deterministic_signature"] = breakdown.get("deterministic_signature")

    perf = calculate_runtime_performance_score(breakdown)
    try:
        from runtime.telemetry.prometheus_metrics import record_runtime_performance_score
        record_runtime_performance_score(float(perf.get("runtime_performance_score", 0.0) or 0.0))
    except Exception:
        pass
    _write_artifact("/tmp/34c-latency-profile.json", {"latency": contract, "score": perf})
    _write_artifact("/tmp/34c-performance-score.json", perf)
    return {
        "contract_version": PERFORMANCE_CONTRACT_VERSION,
        "latency": contract,
        "breakdown": breakdown,
        "performance": perf,
        "generated_at": _now(),
    }


def build_fast_operational_summary(intent: str, *, extra_ctx: dict[str, Any] | None = None, sensor_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    """Authority-first operational fast-path summary.

    This function is intentionally non-LLM and read-only.
    """
    extra_ctx = extra_ctx or {}
    extra_ctx = {**extra_ctx, "fastpath": True}
    sensor_snapshot = sensor_snapshot or {}

    def _runtime_snap():
        try:
            # Avoid expensive node rebuilds in runtime_snapshot().
            from runtime.state.runtime_state import RUNTIME_STATE, _current_runtime_mode
            snap = dict(RUNTIME_STATE)
            snap["mode"] = _current_runtime_mode()
            # Fast-path intentionally does NOT rebuild model inventory.
            snap["model_state"] = None
            if _strict_mode():
                snap.pop("started_at", None)
            return {"runtime": snap}
        except Exception:
            return {"status": "unknown"}

    runtime_state, used_cache = _get_cached("fastpath:runtime_snapshot", _runtime_snap, ttl_s=2)

    try:
        from runtime.telemetry.prometheus_metrics import record_fastpath_request
        record_fastpath_request(intent)
    except Exception:
        pass

    result: dict[str, Any] = {
        "contract_version": PERFORMANCE_CONTRACT_VERSION,
        "fastpath": {
            "active": True,
            "intent": intent,
            "model": "qwen3-vl-8b-instruct",
            "used_cache": used_cache,
        },
        "authority_first": True,
        "runtime": runtime_state,
        "generated_at": _now(),
    }

    if intent == "governance":
        def _gov():
            try:
                from runtime.governance import build_runtime_governance_registry
                return build_runtime_governance_registry(extra_ctx=extra_ctx, sensor_snapshot=sensor_snapshot)
            except Exception:
                return {}
        gov, _ = _get_cached("fastpath:governance", _gov, ttl_s=5)
        score = (gov.get("governance_score_info", {}) or {}).get("score")
        level = (gov.get("governance_score_info", {}) or {}).get("level")
        result["governance"] = {
            "score": score,
            "level": level,
            "degraded_domains": sorted(gov.get("degraded_domains", []) or []),
        }
    elif intent == "validation":
        def _val():
            try:
                from runtime.validation.runtime_validation_framework import build_runtime_validation_report
                return build_runtime_validation_report(sensor_snapshot=sensor_snapshot, extra_ctx=extra_ctx)
            except Exception as exc:
                return {"validation_level": "unknown", "validation_score": 0.0, "error": str(exc)}
        val, _ = _get_cached("fastpath:validation", _val, ttl_s=5)
        comp = (val.get("components", {}) or {})
        result["validation"] = {
            "validation_score": val.get("validation_score"),
            "validation_level": val.get("validation_level"),
            "failed_invariants": comp.get("failed_invariants"),
            "failed_gates": comp.get("failed_gates"),
        }
    elif intent == "observability":
        def _obs():
            try:
                from runtime.observability.live_observability_summary import build_live_observability_summary
                return build_live_observability_summary(extra_ctx=extra_ctx)
            except Exception:
                return {}
        obs, _ = _get_cached("fastpath:observability", _obs, ttl_s=5)
        result["observability_live"] = obs

    # Artifact for burn-in.
    _write_artifact("/tmp/34c-fastpath-summary.json", result)
    return result


def prime_async_diagnostics(*, extra_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    """Start background diagnostics once per process.

    This is intentionally lightweight and safe; deep scans remain opt-in.
    """
    global _ASYNC_STARTED
    extra_ctx = extra_ctx or {}
    enabled = os.environ.get("AI_LAB_ENABLE_ASYNC_DIAGNOSTICS", "true").lower() in ("true", "1", "yes")
    if not enabled:
        return {"contract_version": PERFORMANCE_CONTRACT_VERSION, "async_enabled": False, "started": False}

    with _ASYNC_LOCK:
        if _ASYNC_STARTED:
            return {"contract_version": PERFORMANCE_CONTRACT_VERSION, "async_enabled": True, "started": True, "already_running": True}

        _ASYNC_STARTED = True

    def _runner():
        try:
            # Only refresh safe cached summaries.
            build_fast_operational_summary("observability", extra_ctx=extra_ctx, sensor_snapshot={})
            build_fast_operational_summary("governance", extra_ctx=extra_ctx, sensor_snapshot={})
            build_fast_operational_summary("validation", extra_ctx=extra_ctx, sensor_snapshot={})
            try:
                from runtime.telemetry.prometheus_metrics import record_async_diagnostics
                record_async_diagnostics("refresh_fastpath_caches")
            except Exception:
                pass
        finally:
            pass

    t = threading.Thread(target=_runner, name="ailab-async-diagnostics", daemon=True)
    t.start()
    return {"contract_version": PERFORMANCE_CONTRACT_VERSION, "async_enabled": True, "started": True}
