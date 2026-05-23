from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any

from runtime.authority.contracts import (
    AUTHORITY_CONTRACT_VERSION,
    AuthorityFreshness,
    AuthoritySnapshot,
    AuthorityEvidence,
    AuthorityCognitionSummary,
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


def _network_enabled(extra_ctx: dict[str, Any] | None = None) -> bool:
    extra_ctx = extra_ctx or {}
    if bool(extra_ctx.get("enable_network")):
        return True
    return os.environ.get("AI_LAB_ENABLE_LIVE_AUTHORITY_NETWORK", "false").lower() in ("true", "1", "yes")


def _safe_import_requests():
    try:
        import requests  # type: ignore
        return requests
    except Exception:
        return None


def _prometheus_base_url(extra_ctx: dict[str, Any] | None = None) -> str:
    extra_ctx = extra_ctx or {}
    # Prefer explicit env or infra registry.
    if extra_ctx.get("prometheus_url"):
        return str(extra_ctx.get("prometheus_url"))
    if os.environ.get("AI_LAB_PROMETHEUS_URL"):
        return str(os.environ.get("AI_LAB_PROMETHEUS_URL"))
    try:
        from runtime.infrastructure import build_infrastructure_semantic_summary
        s = build_infrastructure_semantic_summary("192.168.1.40")
        if s.get("authority_root"):
            return "http://192.168.1.40:9090"
    except Exception:
        pass
    return "http://192.168.1.40:9090"


def _fetch_json(url: str, *, timeout_s: int = 5) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    requests = _safe_import_requests()
    if requests is None:
        return None, {"status": "error", "error_type": "requests_unavailable", "error": "requests import failed"}
    start = time.time()
    try:
        r = requests.get(url, timeout=timeout_s, headers={"Accept": "application/json"})
        elapsed = round((time.time() - start) * 1000.0, 1)
        if r.status_code >= 400:
            return None, {"status": "error", "error_type": "http_error", "http_status": r.status_code, "fetch_time_ms": elapsed}
        try:
            return r.json(), {"status": "ok", "fetch_time_ms": elapsed}
        except Exception as exc:
            return None, {"status": "error", "error_type": "invalid_json", "error": str(exc), "fetch_time_ms": elapsed}
    except Exception as exc:
        elapsed = round((time.time() - start) * 1000.0, 1)
        return None, {"status": "error", "error_type": "network", "error": str(exc), "fetch_time_ms": elapsed}


def _get_cached(key: str, builder, *, ttl_s: int = 10) -> tuple[Any, bool]:
    global _CACHE_HITS, _CACHE_MISSES
    now = _now()
    with _CACHE_LOCK:
        ent = _CACHE.get(key)
        if ent is not None:
            age = now - float(ent.get("ts", 0.0))
            if age <= float(ent.get("ttl_s", ttl_s)):
                _CACHE_HITS += 1
                try:
                    from runtime.telemetry.prometheus_metrics import record_authority_cache_event
                    record_authority_cache_event(hit=True)
                except Exception:
                    pass
                return ent.get("value"), True
    _CACHE_MISSES += 1
    try:
        from runtime.telemetry.prometheus_metrics import record_authority_cache_event
        record_authority_cache_event(hit=False)
    except Exception:
        pass
    val = builder()
    with _CACHE_LOCK:
        _CACHE[key] = {"value": val, "ts": now, "ttl_s": int(ttl_s)}
    return val, False


def get_authority_cache_state() -> dict[str, Any]:
    with _CACHE_LOCK:
        entries = len(_CACHE)
    return {
        "contract_version": AUTHORITY_CONTRACT_VERSION,
        "cache_entries": entries,
        "cache_hits": _CACHE_HITS,
        "cache_misses": _CACHE_MISSES,
        "generated_at": _now(),
    }


def prime_authority_cache(*, extra_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}
    # Safe and cheap: hits cache if already present.
    query_prometheus_authority(extra_ctx=extra_ctx)
    return {"contract_version": AUTHORITY_CONTRACT_VERSION, "primed": True, "cache": get_authority_cache_state()}


def query_prometheus_authority(
    *,
    extra_ctx: dict[str, Any] | None = None,
    live_targets: dict[str, Any] | None = None,
    live_runtimeinfo: dict[str, Any] | None = None,
    live_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}
    base = _prometheus_base_url(extra_ctx)

    # IMPORTANT: cache key must incorporate fixtures.
    # Tests (and callers) may pass different live_* payloads; using a single key
    # would leak stale authority state across calls.
    cache_key = "prometheus:authority"
    if live_targets is not None or live_runtimeinfo is not None or live_config is not None:
        cache_key = "prometheus:authority:fixture:" + _hash({
            "targets": live_targets,
            "runtimeinfo": live_runtimeinfo,
            "config": live_config,
        })

    def _build():
        fetch = {"targets": {}, "runtimeinfo": {}, "config": {}, "prometheus_url": base}

        lt = live_targets
        if lt is None:
            if _network_enabled(extra_ctx):
                lt, fetch["targets"] = _fetch_json(f"{base}/api/v1/targets", timeout_s=int(extra_ctx.get("timeout_s", 5) or 5))
            else:
                fetch["targets"] = {"status": "skipped", "reason": "network_disabled"}
        else:
            fetch["targets"] = {"status": "fixture"}

        lr = live_runtimeinfo
        if lr is None:
            if _network_enabled(extra_ctx):
                lr, fetch["runtimeinfo"] = _fetch_json(f"{base}/api/v1/status/runtimeinfo", timeout_s=int(extra_ctx.get("timeout_s", 5) or 5))
            else:
                fetch["runtimeinfo"] = {"status": "skipped", "reason": "network_disabled"}
        else:
            fetch["runtimeinfo"] = {"status": "fixture"}

        lc = live_config
        if lc is None:
            if _network_enabled(extra_ctx):
                lc, fetch["config"] = _fetch_json(f"{base}/api/v1/status/config", timeout_s=int(extra_ctx.get("timeout_s", 5) or 5))
            else:
                fetch["config"] = {"status": "skipped", "reason": "network_disabled"}
        else:
            fetch["config"] = {"status": "fixture"}

        active = (((lt or {}).get("data") or {}).get("activeTargets") or []) if isinstance(lt, dict) else []
        up = sum(1 for t in active if str(t.get("health", "")).lower() == "up")
        down = sum(1 for t in active if str(t.get("health", "")).lower() == "down")

        # Exporters DOWN list
        down_list = []
        for t in active:
            if str(t.get("health", "")).lower() != "down":
                continue
            labels = t.get("labels", {}) or {}
            down_list.append({
                "job": labels.get("job"),
                "instance": labels.get("instance"),
                "last_error": str(t.get("lastError") or "")[:240],
            })
        down_list = sorted(down_list, key=lambda x: str(x.get("job") or "") + str(x.get("instance") or ""))

        runtimeinfo = (lr or {}).get("data", {}) if isinstance(lr, dict) else {}
        return {
            "contract_version": AUTHORITY_CONTRACT_VERSION,
            "authority": {"type": "prometheus", "absolute": True},
            "fetch": fetch,
            "targets": {
                "status": (lt or {}).get("status") if isinstance(lt, dict) else None,
                "active_total": len(active),
                "scrape_up": up,
                "scrape_down": down,
                "down_targets": down_list,
            },
            "runtimeinfo": {
                "version": runtimeinfo.get("version"),
                "revision": runtimeinfo.get("revision"),
            },
            "generated_at": _now(),
        }

    rep, used_cache = _get_cached(cache_key, _build, ttl_s=int(extra_ctx.get("ttl_s", 10) or 10))
    if isinstance(rep, dict):
        rep["used_cache"] = used_cache
    try:
        from runtime.telemetry.prometheus_metrics import record_live_authority_query
        record_live_authority_query("prometheus")
    except Exception:
        pass
    if os.environ.get("AI_LAB_ENABLE_AUTHORITY_ARTIFACTS", "true").lower() in ("true", "1", "yes"):
        _write_artifact("/tmp/35c-live-targets.json", rep if isinstance(rep, dict) else {"value": rep})
    return rep if isinstance(rep, dict) else {"value": rep}


def query_runtime_authority(*, extra_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}

    def _build():
        try:
            from runtime.state.runtime_state import RUNTIME_STATE, _current_runtime_mode
            s = dict(RUNTIME_STATE)
            s["mode"] = _current_runtime_mode()
            # Strip volatile timestamps.
            if _strict_mode():
                s.pop("started_at", None)
            return {"contract_version": AUTHORITY_CONTRACT_VERSION, "runtime": s, "generated_at": _now()}
        except Exception:
            return {"contract_version": AUTHORITY_CONTRACT_VERSION, "runtime": {"status": "unknown"}, "generated_at": _now()}

    rep, used_cache = _get_cached("runtime:authority", _build, ttl_s=5)
    if isinstance(rep, dict):
        rep["used_cache"] = used_cache
    return rep if isinstance(rep, dict) else {"value": rep}


def query_operational_truth(*, extra_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}
    try:
        from runtime.semantic import build_operational_truth
        return build_operational_truth(extra_ctx=extra_ctx)
    except Exception:
        return {"contract_version": "35B", "operational_nodes": [], "authority_roots": []}


def query_infrastructure_identity(*, extra_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}
    try:
        from runtime.infrastructure import build_infrastructure_identity_registry
        return build_infrastructure_identity_registry(extra_ctx=extra_ctx)
    except Exception:
        return {"contract_version": "35A", "authority_roots": [], "control_plane": []}


def calculate_authority_freshness(snapshot: dict[str, Any]) -> dict[str, Any]:
    reasons = []
    model_truth = ((snapshot.get("operational_truth", {}) or {}).get("models", {}) or {})
    model_fresh = model_truth.get("freshness", {}) or {}
    if str(model_fresh.get("status", "")) in ("expired", "unavailable"):
        return AuthorityFreshness(
            status="stale",
            confidence="low",
            reasons=["model_authority_stale", *list(model_fresh.get("reasons", []) or [])],
        ).to_dict()
    prom = snapshot.get("prometheus", {}) or {}
    t = (prom.get("targets", {}) or {})
    fetch = (prom.get("fetch", {}) or {}).get("targets", {})
    if fetch.get("status") != "ok" and fetch.get("status") != "fixture":
        reasons.append("prometheus_targets_unavailable")
    up = int((t.get("scrape_up") or 0))
    total = int((t.get("active_total") or 0))
    if total == 0:
        reasons.append("no_targets")
    if up == 0 and total > 0:
        reasons.append("all_targets_down")

    status = "fresh"
    conf = "high"
    if reasons:
        status = "partial" if up > 0 else "unavailable"
        conf = "medium" if up > 0 else "low"

    return AuthorityFreshness(status=status, confidence=conf, reasons=reasons).to_dict()


def detect_stale_authority(snapshot: dict[str, Any]) -> list[str]:
    fresh = snapshot.get("freshness", {}) or {}
    if fresh.get("status") in ("stale", "aged", "unavailable"):
        return ["prometheus"]
    return []


def detect_authority_gaps(snapshot: dict[str, Any]) -> list[str]:
    gaps = []
    prom = snapshot.get("prometheus", {}) or {}
    fetch = (prom.get("fetch", {}) or {})
    if (fetch.get("targets", {}) or {}).get("status") in ("skipped", "error"):
        gaps.append("prometheus_targets")
    return sorted(set(gaps))


def build_authority_backed_context(*, extra_ctx: dict[str, Any] | None = None, live_prometheus_targets: dict[str, Any] | None = None) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}
    prom = query_prometheus_authority(extra_ctx=extra_ctx, live_targets=live_prometheus_targets)
    runtime = query_runtime_authority(extra_ctx=extra_ctx)
    infra = query_infrastructure_identity(extra_ctx=extra_ctx)
    truth = query_operational_truth(extra_ctx=extra_ctx)
    try:
        from runtime.models.operational_truth import build_operational_model_truth

        model_truth = build_operational_model_truth(extra_ctx=extra_ctx)
    except Exception as exc:
        model_truth = {
            "contract_version": "OBS-HF-LMSTUDIO-1",
            "freshness": {"status": "unavailable", "confidence": "low", "reasons": ["model_truth_error"]},
            "summary": {"operational_total": 0, "rejected_total": 0},
            "operational_models": [],
            "discoverable_only_models": [],
            "error": str(exc),
        }

    base = {
        "contract_version": AUTHORITY_CONTRACT_VERSION,
        "prometheus": prom,
        "runtime": runtime,
        "infrastructure": {
            "contract_version": infra.get("contract_version"),
            "authority_roots": infra.get("authority_roots", []),
            "control_plane": infra.get("control_plane", []),
        },
        "operational_truth": {
            "contract_version": truth.get("contract_version"),
            "operational_nodes": truth.get("operational_nodes", []),
            "inventory_only_nodes": truth.get("inventory_only_nodes", []),
            "discoverable_nodes": truth.get("discoverable_nodes", []),
            "models": model_truth,
            "operational_models": [m.get("id") for m in (model_truth.get("operational_models", []) or []) if isinstance(m, dict)],
            "discoverable_only_models": [m.get("id") for m in (model_truth.get("discoverable_only_models", []) or []) if isinstance(m, dict)],
        },
    }
    base["freshness"] = calculate_authority_freshness(base)
    base["gaps"] = detect_authority_gaps(base)
    base["deterministic_signature"] = _hash({
        "prom_targets": (prom.get("targets", {}) if isinstance(prom, dict) else {}),
        "infra": base["infrastructure"],
        "truth": base["operational_truth"],
        "fresh": base["freshness"],
        "gaps": base["gaps"],
    })
    base["generated_at"] = _now()
    return base


def build_authority_evidence(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    ev = []
    prom = snapshot.get("prometheus", {}) or {}
    ev.append(AuthorityEvidence(
        evidence_type="prometheus_targets",
        source="prometheus",
        freshness=(snapshot.get("freshness", {}) or {}).get("status", "unknown"),
        payload=(prom.get("targets", {}) or {}),
    ).to_dict())
    ev.append(AuthorityEvidence(
        evidence_type="operational_truth",
        source="semantic_sterilization_35b",
        freshness="fresh",
        payload=snapshot.get("operational_truth", {}) or {},
    ).to_dict())
    ev.append(AuthorityEvidence(
        evidence_type="infrastructure_registry",
        source="infrastructure_registry_35a",
        freshness="fresh",
        payload=snapshot.get("infrastructure", {}) or {},
    ).to_dict())
    return ev


def build_live_authority_snapshot(*, extra_ctx: dict[str, Any] | None = None, live_prometheus_targets: dict[str, Any] | None = None) -> dict[str, Any]:
    snap = build_authority_backed_context(extra_ctx=extra_ctx, live_prometheus_targets=live_prometheus_targets)
    gaps = snap.get("gaps", []) or []
    det = snap.get("deterministic_signature")
    out = AuthoritySnapshot(
        contract_version=AUTHORITY_CONTRACT_VERSION,
        prometheus=snap.get("prometheus", {}) or {},
        runtime=snap.get("runtime", {}) or {},
        infrastructure=snap.get("infrastructure", {}) or {},
        operational_truth=snap.get("operational_truth", {}) or {},
        freshness=snap.get("freshness", {}) or {},
        gaps=gaps,
        deterministic_signature=str(det or _hash(snap)),
        generated_at=_now(),
    ).to_dict()

    if os.environ.get("AI_LAB_ENABLE_AUTHORITY_ARTIFACTS", "true").lower() in ("true", "1", "yes"):
        _write_artifact("/tmp/35c-authority-snapshot.json", out)
        _write_artifact("/tmp/35c-authority-freshness.json", out.get("freshness", {}) or {})
        _write_artifact("/tmp/35c-authority-gaps.json", {"gaps": out.get("gaps", [])})
    return out


def _write_artifact(path: str, payload: dict[str, Any]) -> None:
    try:
        Path(path).write_text(json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
    except Exception:
        pass


def build_authority_cognition_summary(*, extra_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    snap = build_live_authority_snapshot(extra_ctx=extra_ctx)
    fresh = snap.get("freshness", {}) or {}
    gaps = snap.get("gaps", []) or []
    status = fresh.get("status", "unknown")

    freshness_score = 100.0 if status == "fresh" else 70.0 if status == "partial" else 0.0
    grounded_score = 100.0 if status in ("fresh", "partial") else 40.0
    stale_total = 1 if status in ("stale", "aged", "unavailable") else 0

    rep = AuthorityCognitionSummary(
        contract_version=AUTHORITY_CONTRACT_VERSION,
        authority_freshness_score=freshness_score,
        grounded_cognition_score=grounded_score,
        stale_authority_total=stale_total,
        authority_gaps_total=len(gaps),
        deterministic_signature=_hash({"fresh": fresh, "gaps": gaps}),
        generated_at=_now(),
    ).to_dict()
    _write_artifact("/tmp/35c-authority-score.json", rep)
    return rep
