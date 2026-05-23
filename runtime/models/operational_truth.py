"""Authority-backed operational model truth for LM Studio.

Separates discoverable/loaded/healthy/capable/operational so runtime cognition
never treats discovery inventory as usable model state.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any

MODEL_TRUTH_CONTRACT_VERSION = "OBS-HF-LMSTUDIO-1"
DEFAULT_MODEL_TRUTH_TTL_SECONDS = 60


def _strict_mode() -> bool:
    return os.environ.get("STRICT_VALIDATION_MODE", "false").lower() in ("true", "1", "yes")


def _now() -> float:
    return 0.0 if _strict_mode() else time.time()


def _hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _normalize(model_id: str) -> str:
    try:
        from runtime.models.model_registry import normalize_model_id

        return normalize_model_id(model_id)
    except Exception:
        model = (model_id or "").strip().lower()
        return model.split("/")[-1] if "/" in model else model


def _metadata(model_id: str) -> dict[str, Any]:
    try:
        from runtime.models.model_registry import get_model_metadata

        meta = get_model_metadata(model_id) or {}
        return dict(meta)
    except Exception:
        return {}


def _is_enabled(meta: dict[str, Any]) -> bool:
    return bool(meta.get("enabled", True))


def _ctx(meta: dict[str, Any], discovered: dict[str, Any]) -> int:
    for key in ("context_window", "ctx", "context_length", "max_context"):
        val = meta.get(key, discovered.get(key))
        try:
            n = int(val or 0)
        except Exception:
            n = 0
        if n > 0:
            return n
    return 0


def _skills(meta: dict[str, Any]) -> list[str]:
    skills = meta.get("skills", [])
    if not isinstance(skills, list):
        return []
    return sorted({str(s).strip() for s in skills if str(s).strip()})


def _node_freshness(discovery: dict[str, Any], now: float) -> dict[str, Any]:
    ts = float(discovery.get("timestamp", 0) or 0)
    ttl = int(discovery.get("ttl_seconds", DEFAULT_MODEL_TRUTH_TTL_SECONDS) or DEFAULT_MODEL_TRUTH_TTL_SECONDS)
    age = max(0.0, now - ts) if ts else float("inf")
    expired = (not ts) or age > ttl
    status = "expired" if expired else "fresh"
    confidence = "low" if expired else "high"
    reasons = [] if not expired else ["model_discovery_stale"]
    return {
        "status": status,
        "confidence": confidence,
        "age_seconds": None if age == float("inf") else round(age, 3),
        "ttl_seconds": ttl,
        "expired": expired,
        "reasons": reasons,
    }


def _node_health(node: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not bool(node.get("online")):
        reasons.append("backend_offline")
    err = str(node.get("error") or "").strip()
    if err:
        reasons.append("backend_error")
        if "operation canceled" in err.lower() or "operation cancelled" in err.lower():
            reasons.append("operation_canceled")
    return (not reasons), reasons


def _build_record(model_id: str, discovered: dict[str, Any], node: dict[str, Any], freshness: dict[str, Any]) -> dict[str, Any]:
    canonical = _normalize(model_id)
    meta = _metadata(canonical)
    skills = _skills(meta)
    ctx = _ctx(meta, discovered)
    healthy, health_reasons = _node_health(node)
    loaded = bool(node.get("online")) and bool(model_id)
    capable = ctx > 0 and bool(skills)
    enabled = _is_enabled(meta)

    rejection_reasons: list[str] = []
    if not enabled:
        rejection_reasons.append("model_disabled")
    if not loaded:
        rejection_reasons.append("not_loaded")
    if not healthy:
        rejection_reasons.extend(health_reasons)
    if ctx <= 0:
        rejection_reasons.append("ctx_zero")
    if not skills:
        rejection_reasons.append("skills_empty")
    if freshness.get("expired"):
        rejection_reasons.append("authority_freshness_expired")

    operational = loaded and healthy and capable and enabled and not freshness.get("expired")
    state = "operational" if operational else "loaded" if loaded and capable and healthy else "discoverable" if loaded else "unavailable"
    if not enabled:
        state = "disabled"

    return {
        "id": canonical,
        "discovered_id": model_id,
        "node": node.get("name") or node.get("node") or "unknown",
        "host": node.get("host"),
        "port": node.get("port"),
        "discoverable": True,
        "loaded": loaded,
        "healthy": healthy,
        "capable": capable,
        "operational": operational,
        "state": state,
        "ctx": ctx,
        "skills": skills,
        "chat_capable": bool(meta.get("chat_eligible", True)) and "embeddings" not in skills,
        "embedding_capable": bool(meta.get("embedding")) or "embeddings" in skills,
        "metadata_source": meta.get("source", "unknown"),
        "freshness": freshness,
        "rejection_reasons": sorted(set(rejection_reasons)),
    }


def build_operational_model_truth(
    *,
    extra_ctx: dict[str, Any] | None = None,
    discovery: dict[str, Any] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Build deterministic LM Studio operational model truth.

    Authority precedence: live backend discovery > runtime cache > registry metadata.
    Registry metadata can enrich capabilities but cannot make a stale/unhealthy
    discovery result operational.
    """
    extra_ctx = extra_ctx or {}
    now = _now()
    if discovery is None:
        try:
            from runtime.models.model_discovery import discover_all_models

            discovery = discover_all_models(force=bool(force or extra_ctx.get("force_model_truth")))
        except Exception as exc:
            discovery = {
                "timestamp": now,
                "ttl_seconds": DEFAULT_MODEL_TRUTH_TTL_SECONDS,
                "nodes": [],
                "error": str(exc),
                "models_found": 0,
                "online_nodes": 0,
                "total_nodes": 0,
            }

    freshness = _node_freshness(discovery or {}, now)
    records: list[dict[str, Any]] = []
    node_health: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for node in (discovery or {}).get("nodes", []) or []:
        healthy, reasons = _node_health(node if isinstance(node, dict) else {})
        node_health.append({
            "name": (node or {}).get("name"),
            "host": (node or {}).get("host"),
            "online": bool((node or {}).get("online")),
            "healthy": healthy,
            "reasons": reasons,
            "latency_ms": (node or {}).get("latency_ms"),
        })
        if not isinstance(node, dict):
            continue
        for item in node.get("models", []) or []:
            if isinstance(item, dict):
                model_id = item.get("id") or item.get("model") or item.get("name")
                discovered = item
            else:
                model_id = str(item)
                discovered = {"id": model_id}
            if not model_id:
                continue
            key = (_normalize(str(model_id)), str(node.get("host") or ""))
            if key in seen:
                continue
            seen.add(key)
            records.append(_build_record(str(model_id), discovered, node, freshness))

    records.sort(key=lambda r: (r.get("id", ""), r.get("host") or ""))
    operational = [r for r in records if r.get("operational")]
    loaded = [r for r in records if r.get("loaded")]
    discoverable_only = [r for r in records if r.get("discoverable") and not r.get("operational")]
    rejected = [r for r in records if r.get("rejection_reasons")]

    confidence_score = 100.0
    reasons: list[str] = []
    if freshness.get("expired"):
        confidence_score = min(confidence_score, 20.0)
        reasons.append("stale_model_authority")
    if not records:
        confidence_score = min(confidence_score, 30.0)
        reasons.append("no_models_discovered")
    if records and not operational:
        confidence_score = min(confidence_score, 45.0)
        reasons.append("no_operational_models")
    if any("operation_canceled" in (r.get("rejection_reasons") or []) for r in rejected):
        confidence_score = min(confidence_score, 35.0)
        reasons.append("operation_canceled")

    out = {
        "contract_version": MODEL_TRUTH_CONTRACT_VERSION,
        "generated_at": now,
        "freshness": freshness,
        "authority_hierarchy": ["live_backend_truth", "runtime_cache", "semantic_recall", "discoverable_inventory"],
        "models": records,
        "operational_models": operational,
        "loaded_models": loaded,
        "discoverable_only_models": discoverable_only,
        "rejected_models": rejected,
        "summary": {
            "models_total": len(records),
            "operational_total": len(operational),
            "loaded_total": len(loaded),
            "discoverable_only_total": len(discoverable_only),
            "rejected_total": len(rejected),
            "ctx_zero_rejected": sum(1 for r in rejected if "ctx_zero" in (r.get("rejection_reasons") or [])),
            "empty_skills_rejected": sum(1 for r in rejected if "skills_empty" in (r.get("rejection_reasons") or [])),
            "unhealthy_rejected": sum(1 for r in rejected if any(x in (r.get("rejection_reasons") or []) for x in ("backend_offline", "backend_error", "operation_canceled"))),
        },
        "node_health": node_health,
        "confidence": {"score": round(confidence_score, 2), "label": "high" if confidence_score >= 85 else "medium" if confidence_score >= 60 else "low" if confidence_score > 0 else "unknown", "reasons": reasons},
    }
    out["deterministic_signature"] = _hash({
        "freshness": out["freshness"],
        "models": [{k: r.get(k) for k in ("id", "host", "operational", "ctx", "skills", "rejection_reasons")} for r in records],
        "summary": out["summary"],
    })
    return out


def get_operational_model_ids(*, extra_ctx: dict[str, Any] | None = None, discovery: dict[str, Any] | None = None) -> list[str]:
    truth = build_operational_model_truth(extra_ctx=extra_ctx, discovery=discovery)
    return [str(m.get("id")) for m in truth.get("operational_models", []) or [] if m.get("id")]


def is_model_operational(model_id: str, *, extra_ctx: dict[str, Any] | None = None, discovery: dict[str, Any] | None = None) -> bool:
    canonical = _normalize(model_id)
    return canonical in set(get_operational_model_ids(extra_ctx=extra_ctx, discovery=discovery))
