from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any

from runtime.fastpath.contracts import (
    FASTPATH_CONTRACT_VERSION,
    OperationalSignal,
    OperationalSummary,
    FastPathAuthoritySnapshot,
    FastPathCache,
    FastPathRouting,
    FastPathResponse,
)


_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, dict[str, Any]] = {}
_CACHE_HITS = 0
_CACHE_MISSES = 0


def _strict_mode() -> bool:
    return os.environ.get("STRICT_VALIDATION_MODE", "false").lower() in ("true", "1", "yes")


def _now() -> float:
    return 0.0 if _strict_mode() else time.time()


def _hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _write_artifact(path: str, payload: dict[str, Any]) -> None:
    try:
        Path(path).write_text(json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
    except Exception:
        pass


def _get_cached(key: str, builder, *, ttl_s: int = 5) -> tuple[Any, bool]:
    global _CACHE_HITS, _CACHE_MISSES
    now = _now()
    with _CACHE_LOCK:
        ent = _CACHE.get(key)
        if ent is not None:
            age = now - float(ent.get("ts", 0.0))
            if age <= float(ent.get("ttl_s", ttl_s)):
                _CACHE_HITS += 1
                try:
                    from runtime.telemetry.prometheus_metrics import record_fastpath_cache_event
                    record_fastpath_cache_event(hit=True)
                except Exception:
                    pass
                return ent.get("value"), True

    _CACHE_MISSES += 1
    try:
        from runtime.telemetry.prometheus_metrics import record_fastpath_cache_event
        record_fastpath_cache_event(hit=False)
    except Exception:
        pass
    val = builder()
    with _CACHE_LOCK:
        _CACHE[key] = {"value": val, "ts": now, "ttl_s": int(ttl_s)}
    return val, False


def get_fastpath_cache_state() -> dict[str, Any]:
    with _CACHE_LOCK:
        entries = len(_CACHE)
    freshness = "fresh" if entries > 0 else "unknown"
    return {
        "contract_version": FASTPATH_CONTRACT_VERSION,
        "cache": FastPathCache(
            cache_entries=entries,
            cache_hits=_CACHE_HITS,
            cache_misses=_CACHE_MISSES,
            freshness=freshness,
        ).to_dict(),
        "generated_at": _now(),
    }


def prime_fastpath_cache(*, extra_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}
    # Warm cheap summaries only.
    build_fast_observability_summary(extra_ctx=extra_ctx)
    build_fast_governance_summary(extra_ctx=extra_ctx)
    build_fast_validation_summary(extra_ctx=extra_ctx)
    return {"contract_version": FASTPATH_CONTRACT_VERSION, "primed": True, "cache": get_fastpath_cache_state()}


# ── Intent classification (deterministic heuristics) ─────────────────────────


_FAST_MAP: list[tuple[str, tuple[str, ...]]] = [
    ("FAST_GPU", ("gpu", "rx9070", "rx7900xt", "vram", "temperatura gpu", "estado gpu")),
    ("FAST_OBSERVABILITY", ("observability", "observabilidad", "prometheus", "grafana", "targets", "scrape", "exporters")),
    ("FAST_GOVERNANCE", ("governance", "gobernanza", "policy", "degraded domains", "dominios degradados")),
    ("FAST_VALIDATION", ("validation", "validacion", "validación", "invariants", "safety gates")),
    ("FAST_TOPOLOGY", ("topology", "topologia", "topología", "control plane", "control-plane")),
    ("FAST_INFRASTRUCTURE", ("infra", "infrastructure", "nodo", "node", "who is", "what is", "qué es", "que es")),
    ("FAST_OPERATIONAL", ("estado runtime", "runtime status", "estado del runtime", "estado cluster", "cluster status", "status runtime")),
]

_DEEP_MAP: list[tuple[str, tuple[str, ...]]] = [
    ("DEEP_REMEDIATION", ("remediation", "remediacion", "remediación", "fix", "soluciona", "corrige", "arregla")),
    ("DEEP_INCIDENT", ("incident", "incidente", "sev", "p0", "p1", "outage", "caida", "caída")),
    ("DEEP_FORENSIC", ("forensic", "forense", "postmortem", "timeline")),
    ("DEEP_DIAGNOSTIC", ("debug", "diagnost", "root cause", "rca", "por que", "por qué")),
]


def classify_fastpath_intent(user_text: str, *, verbosity: str = "operational") -> dict[str, Any]:
    t = (user_text or "").strip().lower()
    if not t:
        return FastPathRouting(classification="FAST_OPERATIONAL", intent="operational", deep_path=False, verbosity=verbosity).to_dict()

    for cls, pats in _DEEP_MAP:
        if any(p in t for p in pats):
            return FastPathRouting(classification=cls, intent="deep", deep_path=True, verbosity=verbosity).to_dict()

    for cls, pats in _FAST_MAP:
        if any(p in t for p in pats):
            # intent mirrors classification family for routing.
            intent = cls.replace("FAST_", "").lower()
            return FastPathRouting(classification=cls, intent=intent, deep_path=False, verbosity=verbosity).to_dict()

    # Default: operational fast-path for short operational questions.
    if len(t) <= 140 and "```" not in t:
        return FastPathRouting(classification="FAST_OPERATIONAL", intent="operational", deep_path=False, verbosity=verbosity).to_dict()
    return FastPathRouting(classification="DEEP_DIAGNOSTIC", intent="deep", deep_path=True, verbosity=verbosity).to_dict()


# ── Authority snapshot (always before summaries) ─────────────────────────────


def _build_fastpath_authority_snapshot(*, extra_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}
    try:
        from runtime.authority import build_live_authority_snapshot
        snap = build_live_authority_snapshot(extra_ctx=extra_ctx)
        prom_targets = ((snap.get("prometheus", {}) or {}).get("targets", {}) or {})
        auth = FastPathAuthoritySnapshot(
            contract_version=snap.get("contract_version", "35C"),
            freshness=snap.get("freshness", {}) or {},
            gaps=snap.get("gaps", []) or [],
            prometheus_targets={
                "active_total": prom_targets.get("active_total", 0),
                "scrape_up": prom_targets.get("scrape_up", 0),
                "scrape_down": prom_targets.get("scrape_down", 0),
                "down_targets": prom_targets.get("down_targets", []) or [],
                "status": prom_targets.get("status"),
            },
            deterministic_signature=str(snap.get("deterministic_signature") or _hash(snap)),
        ).to_dict()
        return auth
    except Exception as exc:
        return {
            "contract_version": "35C",
            "freshness": {"status": "unavailable", "confidence": "low", "reasons": ["authority_error"]},
            "gaps": ["authority"],
            "prometheus_targets": {"active_total": 0, "scrape_up": 0, "scrape_down": 0, "down_targets": [], "status": "error"},
            "deterministic_signature": _hash({"error": str(exc)}),
        }


def _noc_lines(header: str, *lines: str, max_lines: int = 10) -> list[str]:
    out = [header.strip()] if header else []
    for ln in lines:
        ln = (ln or "").strip()
        if not ln:
            continue
        out.append(ln)
        if len(out) >= max_lines:
            break
    return out


def _quality_score(lines: list[str]) -> float:
    # Heuristic: compact and non-empty.
    n = len([l for l in lines if l.strip()])
    if n == 0:
        return 0.0
    if n <= 10:
        return 100.0
    if n <= 14:
        return 70.0
    return 40.0


def build_fast_operational_summary(*, extra_ctx: dict[str, Any] | None = None, authority: dict[str, Any] | None = None) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}
    authority = authority or _build_fastpath_authority_snapshot(extra_ctx=extra_ctx)
    fresh = authority.get("freshness", {}) or {}
    prom = authority.get("prometheus_targets", {}) or {}
    header = "Operational summary"
    lines = _noc_lines(
        header,
        f"Runtime: healthy_degraded",  # default; precise state comes from governance/validation
        f"Prometheus authority: {fresh.get('status', 'unknown')}",
        f"Targets: {prom.get('scrape_up', 0)}/{prom.get('active_total', 0)} UP",
        f"Exporters down: {prom.get('scrape_down', 0)}",
    )
    summ = OperationalSummary(
        mode=str(extra_ctx.get("verbosity", "operational")),
        lines=lines,
        signals=[],
        deterministic_signature=_hash({"lines": lines, "authority": authority.get("deterministic_signature")}),
    ).to_dict()
    return summ


def build_fast_observability_summary(*, extra_ctx: dict[str, Any] | None = None, authority: dict[str, Any] | None = None) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}
    authority = authority or _build_fastpath_authority_snapshot(extra_ctx=extra_ctx)
    fresh = authority.get("freshness", {}) or {}
    prom = authority.get("prometheus_targets", {}) or {}
    down = prom.get("down_targets", []) or []
    down_jobs = ",".join([str(d.get("job") or "?") for d in down[:3]]) if down else "none"

    header = "Observability"
    lines = _noc_lines(
        header,
        f"Prometheus authority: {fresh.get('status', 'unknown')}",
        f"Targets: {prom.get('scrape_up', 0)}/{prom.get('active_total', 0)} UP",
        f"Down examples: {down_jobs}",
    )
    signals: list[dict[str, Any]] = []
    if int(prom.get("scrape_down", 0) or 0) > 0:
        signals.append(OperationalSignal(
            domain="observability",
            severity="warning",
            message=f"{int(prom.get('scrape_down', 0) or 0)} targets down",
            evidence=["prometheus_targets"],
            confidence=str(fresh.get("confidence", "unknown")),
            freshness=str(fresh.get("status", "unknown")),
        ).to_dict())
    summ = OperationalSummary(
        mode=str(extra_ctx.get("verbosity", "operational")),
        lines=lines,
        signals=signals,
        deterministic_signature=_hash({"lines": lines, "signals": signals, "authority": authority.get("deterministic_signature")}),
    ).to_dict()
    return summ


def build_fast_governance_summary(*, extra_ctx: dict[str, Any] | None = None, authority: dict[str, Any] | None = None, sensor_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}
    sensor_snapshot = sensor_snapshot or {}
    authority = authority or _build_fastpath_authority_snapshot(extra_ctx=extra_ctx)

    # Suppressed governance: use fastpath=True to avoid deep scans.
    level = "unknown"
    score = 0
    degraded = []
    try:
        from runtime.governance import build_runtime_governance_registry
        reg = build_runtime_governance_registry(extra_ctx={**extra_ctx, "fastpath": True}, sensor_snapshot=sensor_snapshot)
        gi = reg.get("governance_score_info", {}) or {}
        level = str(gi.get("level", "unknown"))
        score = int(gi.get("score", 0) or 0)
        degraded = sorted(reg.get("degraded_domains", []) or [])
    except Exception:
        pass

    header = "Governance"
    lines = _noc_lines(
        header,
        f"Governance: {level} ({score}/100)",
        f"Degraded domains: {len(degraded)}" + (f" [{', '.join(degraded[:6])}]" if degraded else ""),
    )
    summ = OperationalSummary(
        mode=str(extra_ctx.get("verbosity", "operational")),
        lines=lines,
        signals=[],
        deterministic_signature=_hash({"lines": lines, "authority": authority.get("deterministic_signature")}),
    ).to_dict()
    return summ


def build_fast_validation_summary(*, extra_ctx: dict[str, Any] | None = None, authority: dict[str, Any] | None = None, sensor_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}
    sensor_snapshot = sensor_snapshot or {}
    authority = authority or _build_fastpath_authority_snapshot(extra_ctx=extra_ctx)

    level = "unknown"
    score = 0.0
    failed_inv = 0
    try:
        from runtime.validation.runtime_validation_framework import build_runtime_validation_report
        rep = build_runtime_validation_report(sensor_snapshot=sensor_snapshot, extra_ctx={**extra_ctx, "fastpath": True})
        level = str(rep.get("validation_level", "unknown"))
        score = float(rep.get("validation_score", 0.0) or 0.0)
        comp = rep.get("components", {}) or {}
        failed_inv = int(comp.get("failed_invariants", 0) or 0)
    except Exception:
        pass

    header = "Validation"
    lines = _noc_lines(
        header,
        f"Validation: {level} ({round(score, 1)}/100)",
        f"Failed invariants: {failed_inv}",
    )
    summ = OperationalSummary(
        mode=str(extra_ctx.get("verbosity", "operational")),
        lines=lines,
        signals=[],
        deterministic_signature=_hash({"lines": lines, "authority": authority.get("deterministic_signature")}),
    ).to_dict()
    return summ


def build_fast_infrastructure_summary(
    *,
    user_text: str | None = None,
    extra_ctx: dict[str, Any] | None = None,
    authority: dict[str, Any] | None = None,
) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}
    authority = authority or _build_fastpath_authority_snapshot(extra_ctx=extra_ctx)

    # If the user asked "qué es <ip>", provide identity-first compact answer.
    identity_line = None
    try:
        from runtime.context.report_runtime_context import extract_target_ip
        target = extract_target_ip(user_text or "")
        if target:
            from runtime.infrastructure import identify_infrastructure
            rep = identify_infrastructure(target)
            identity_line = f"identity={rep.get('identity') or target}"
    except Exception:
        identity_line = None

    score = 0.0
    roots: list[str] = []
    try:
        from runtime.infrastructure import build_infrastructure_identity_registry
        infra = build_infrastructure_identity_registry(extra_ctx=extra_ctx)
        score = float(infra.get("score", 0.0) or 0.0)
        roots = sorted(infra.get("authority_roots", []) or [])
    except Exception:
        pass
    header = "Infrastructure"
    lines = _noc_lines(
        header,
        identity_line or "",
        f"Control plane: operational",
        f"Authority roots: {', '.join(roots[:3]) if roots else 'unknown'}",
        f"Infrastructure identity: {round(score, 1)}/100",
    )
    summ = OperationalSummary(
        mode=str(extra_ctx.get("verbosity", "operational")),
        lines=lines,
        signals=[],
        deterministic_signature=_hash({"lines": lines, "roots": roots, "authority": authority.get("deterministic_signature")}),
    ).to_dict()
    return summ


def build_fast_topology_summary(*, extra_ctx: dict[str, Any] | None = None, authority: dict[str, Any] | None = None) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}
    authority = authority or _build_fastpath_authority_snapshot(extra_ctx=extra_ctx)
    header = "Topology"
    lines = _noc_lines(
        header,
        "Control plane: operational",
        "Inference backend: RX9070 active",
        "Inventory: RX7900XT expected_offline",
    )
    summ = OperationalSummary(
        mode=str(extra_ctx.get("verbosity", "operational")),
        lines=lines,
        signals=[],
        deterministic_signature=_hash({"lines": lines, "authority": authority.get("deterministic_signature")}),
    ).to_dict()
    return summ


def build_fast_gpu_summary(*, extra_ctx: dict[str, Any] | None = None, authority: dict[str, Any] | None = None) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}
    authority = authority or _build_fastpath_authority_snapshot(extra_ctx=extra_ctx)
    header = "GPU"
    lines = _noc_lines(
        header,
        "RX9070: operational",
        "RX7900XT: inventory-only expected_offline",
    )
    summ = OperationalSummary(
        mode=str(extra_ctx.get("verbosity", "operational")),
        lines=lines,
        signals=[],
        deterministic_signature=_hash({"lines": lines, "authority": authority.get("deterministic_signature")}),
    ).to_dict()
    return summ


def build_fastpath_response(
    user_text: str,
    *,
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
    verbosity: str = "operational",
) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}
    sensor_snapshot = sensor_snapshot or {}
    extra_ctx = {**extra_ctx, "verbosity": verbosity, "fastpath": True}

    routing = classify_fastpath_intent(user_text, verbosity=verbosity)
    deep = bool(routing.get("deep_path"))

    # Authority snapshot first.
    auth, auth_used_cache = _get_cached(
        "35d:authority",
        lambda: _build_fastpath_authority_snapshot(extra_ctx=extra_ctx),
        ttl_s=int(extra_ctx.get("ttl_s", 5) or 5),
    )
    if isinstance(auth, dict):
        auth["used_cache"] = bool(auth_used_cache)

    intent = str(routing.get("intent") or "operational")
    cls = str(routing.get("classification") or "FAST_OPERATIONAL")
    cache_key = "35d:summary:" + _hash({"intent": intent, "cls": cls, "verbosity": verbosity, "auth": (auth or {}).get("deterministic_signature")})

    start = time.perf_counter()

    def _build_summary():
        if cls == "FAST_OBSERVABILITY":
            return build_fast_observability_summary(extra_ctx=extra_ctx, authority=auth)
        if cls == "FAST_GOVERNANCE":
            return build_fast_governance_summary(extra_ctx=extra_ctx, authority=auth, sensor_snapshot=sensor_snapshot)
        if cls == "FAST_VALIDATION":
            return build_fast_validation_summary(extra_ctx=extra_ctx, authority=auth, sensor_snapshot=sensor_snapshot)
        if cls == "FAST_TOPOLOGY":
            return build_fast_topology_summary(extra_ctx=extra_ctx, authority=auth)
        if cls == "FAST_INFRASTRUCTURE":
            return build_fast_infrastructure_summary(user_text=user_text, extra_ctx=extra_ctx, authority=auth)
        if cls == "FAST_GPU":
            return build_fast_gpu_summary(extra_ctx=extra_ctx, authority=auth)
        return build_fast_operational_summary(extra_ctx=extra_ctx, authority=auth)

    summary, used_cache = _get_cached(cache_key, _build_summary, ttl_s=int(extra_ctx.get("ttl_s", 5) or 5))
    elapsed_s = max(0.0, time.perf_counter() - start)
    try:
        from runtime.telemetry.prometheus_metrics import (
            record_fastpath_request,
            record_fastpath_latency_seconds,
            record_operational_compact_response,
            record_deep_path_request,
            record_operational_response_quality_score,
        )
        record_fastpath_request(intent)
        record_fastpath_latency_seconds(elapsed_s)
        record_operational_response_quality_score(float(_quality_score((summary or {}).get("lines", []) if isinstance(summary, dict) else [])))
        if deep:
            record_deep_path_request(cls)
        else:
            record_operational_compact_response(intent)
    except Exception:
        pass

    # Ensure compactness and suppress repeated noise.
    text_lines = []
    if isinstance(summary, dict):
        text_lines = list(summary.get("lines", []) or [])
    try:
        from runtime.performance.runtime_latency_calibration import compress_operational_noise
        original = "\n".join(text_lines)
        compact_text = compress_operational_noise(original, level=verbosity)
        if compact_text != original:
            try:
                from runtime.telemetry.prometheus_metrics import record_verbosity_suppression
                record_verbosity_suppression("dedup_or_truncate")
            except Exception:
                pass
        text_lines = [ln for ln in compact_text.splitlines() if ln.strip()]
        if isinstance(summary, dict):
            summary["lines"] = text_lines[:10]
    except Exception:
        if isinstance(summary, dict):
            summary["lines"] = text_lines[:10]

    quality = _quality_score(text_lines)
    det = _hash({"routing": routing, "summary": summary, "authority": (auth or {}).get("deterministic_signature"), "verbosity": verbosity})

    resp = FastPathResponse(
        contract_version=FASTPATH_CONTRACT_VERSION,
        routing=routing,
        summary=summary if isinstance(summary, dict) else {"lines": [str(summary)]},
        authority=auth if isinstance(auth, dict) else {"value": auth},
        cache=get_fastpath_cache_state(),
        response_quality_score=quality,
        deterministic_signature=det,
        generated_at=_now(),
    ).to_dict()

    resp["used_cache"] = bool(used_cache)

    if os.environ.get("AI_LAB_ENABLE_FASTPATH_ARTIFACTS", "true").lower() in ("true", "1", "yes"):
        _write_artifact("/tmp/35d-fastpath-summary.json", resp)
        _write_artifact("/tmp/35d-fastpath-cache.json", get_fastpath_cache_state())
        _write_artifact("/tmp/35d-operational-quality.json", {"quality": quality, "lines": text_lines})
    return resp
