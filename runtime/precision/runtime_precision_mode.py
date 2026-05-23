from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from runtime.precision.contracts import (
    AuthorityConflict,
    ConfidenceScore,
    EvidenceStrength,
    OperationalCertainty,
    PartialState,
    PrecisionEvidence,
    PrecisionSummary,
)


PRECISION_CONTRACT_VERSION = "36B"


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


def _label_conf(score: float) -> str:
    if score >= 85.0:
        return "high"
    if score >= 60.0:
        return "medium"
    if score > 0.0:
        return "low"
    return "unknown"


def _is_leaky_identifier(value: str) -> bool:
    v = (value or "").strip().lower()
    if not v:
        return False
    # RULE-36B-9: no lmstudio-community leakage in operational payloads.
    if "lmstudio-community" in v:
        return True
    return False


def calculate_authority_confidence(authority: dict[str, Any]) -> ConfidenceScore:
    fresh = (authority.get("freshness", {}) or {})
    status = str(fresh.get("status", "unknown"))
    reasons = list(fresh.get("reasons", []) or [])
    score = 100.0 if status == "fresh" else 70.0 if status == "partial" else 20.0 if status in ("stale", "aged") else 0.0
    return ConfidenceScore(score=score, label=_label_conf(score), reasons=reasons)


def calculate_observability_confidence(authority: dict[str, Any]) -> ConfidenceScore:
    prom = (authority.get("prometheus", {}) or {})
    targets = (prom.get("targets", {}) or {})
    up = int(targets.get("scrape_up", 0) or 0)
    total = int(targets.get("active_total", 0) or 0)
    reasons: list[str] = []
    if total == 0:
        reasons.append("no_targets")
        score = 30.0
    else:
        ratio = up / max(1, total)
        if up == 0:
            reasons.append("all_targets_down")
        if ratio >= 0.95:
            score = 100.0
        elif ratio >= 0.60:
            score = 70.0
        else:
            score = 40.0
    return ConfidenceScore(score=score, label=_label_conf(score), reasons=reasons)


def calculate_routing_confidence(routability: list[dict[str, Any]]) -> ConfidenceScore:
    active_routable = [e for e in routability if e.get("routable") and e.get("operational_state") == "active" and not e.get("deprecated")]
    reasons: list[str] = []
    if not routability:
        return ConfidenceScore(score=0.0, label="unknown", reasons=["no_entity_registry"])
    if not active_routable:
        reasons.append("no_active_routable_entities")
        return ConfidenceScore(score=40.0, label=_label_conf(40.0), reasons=reasons)
    return ConfidenceScore(score=90.0, label=_label_conf(90.0), reasons=reasons)


def calculate_incident_confidence(incidents: dict[str, Any]) -> ConfidenceScore:
    if not incidents:
        return ConfidenceScore(score=60.0, label=_label_conf(60.0), reasons=["incidents_unavailable"])
    return ConfidenceScore(score=85.0, label=_label_conf(85.0), reasons=[])


def calculate_codebase_confidence(codebase: dict[str, Any]) -> ConfidenceScore:
    if not codebase:
        return ConfidenceScore(score=60.0, label=_label_conf(60.0), reasons=["codebase_unavailable"])
    score = float((codebase.get("score", {}) or {}).get("structural_health_score", 0.0) or 0.0)
    # Treat codebase as supporting evidence only.
    score = max(40.0, min(95.0, score))
    return ConfidenceScore(score=score, label=_label_conf(score), reasons=[])


def calculate_operational_confidence(
    *,
    authority_conf: ConfidenceScore,
    observability_conf: ConfidenceScore,
    routing_conf: ConfidenceScore,
    incident_conf: ConfidenceScore,
    codebase_conf: ConfidenceScore,
    partial_total: int,
    conflict_total: int,
) -> ConfidenceScore:
    # RULE-36B-5: partial evidence MUST reduce confidence.
    base = min(authority_conf.score, observability_conf.score, routing_conf.score)
    penalty = 0.0
    reasons: list[str] = []
    if partial_total:
        penalty += min(30.0, float(partial_total) * 10.0)
        reasons.append("partial_evidence")
    if conflict_total:
        penalty += min(30.0, float(conflict_total) * 15.0)
        reasons.append("authority_conflicts")
    base = min(base, max(50.0, incident_conf.score))
    base = min(base, max(50.0, codebase_conf.score))
    score = max(0.0, base - penalty)
    return ConfidenceScore(score=score, label=_label_conf(score), reasons=reasons)


def _detect_partial_states(authority: dict[str, Any], routability: list[dict[str, Any]]) -> list[dict[str, Any]]:
    partial: list[PartialState] = []
    fresh = (authority.get("freshness", {}) or {})
    if str(fresh.get("status")) in ("partial", "unavailable"):
        partial.append(PartialState(
            domain="authority",
            missing=list(fresh.get("reasons", []) or []) or ["unknown"],
            severity="warning" if str(fresh.get("status")) == "partial" else "critical",
            description="authority evidence incomplete",
        ))
    if not routability:
        partial.append(PartialState(
            domain="routing",
            missing=["entity_registry"],
            severity="warning",
            description="entity registry unavailable",
        ))
    return [p.to_dict() for p in partial]


def _detect_authority_conflicts(authority: dict[str, Any], routability: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conflicts: list[AuthorityConflict] = []
    fresh = (authority.get("freshness", {}) or {})
    status = str(fresh.get("status", "unknown"))
    truth = (authority.get("operational_truth", {}) or {})
    op_nodes = truth.get("operational_nodes", []) or []
    active_routable = [e for e in routability if e.get("routable") and e.get("operational_state") == "active" and not e.get("deprecated")]
    if status in ("unavailable", "stale") and (op_nodes or active_routable):
        conflicts.append(AuthorityConflict(
            conflict_type="stale_authority_with_operational_claims",
            severity="medium",
            description="authority freshness is unavailable/stale but operational entities exist in snapshot",
            evidence=["authority", "entities"],
        ))
    return [c.to_dict() for c in conflicts]


def _sanitize_discoverables(discoverables: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for e in discoverables or []:
        eid = str(e.get("entity_id", ""))
        if _is_leaky_identifier(eid):
            continue
        if e.get("deprecated"):
            continue
        e2 = dict(e)
        # RULE-36B-6: discoverable != routable.
        e2["operational_state"] = "inactive"
        e2["routable"] = False
        out.append(e2)
    return out


def _build_evidence_catalog(authority: dict[str, Any], routability: list[dict[str, Any]], incidents: dict[str, Any], codebase: dict[str, Any]) -> list[dict[str, Any]]:
    ev: list[PrecisionEvidence] = []
    fresh = (authority.get("freshness", {}) or {})
    status = str(fresh.get("status", "unknown"))
    strength = EvidenceStrength.CONFIRMED if status == "fresh" else EvidenceStrength.PARTIAL if status == "partial" else EvidenceStrength.UNKNOWN
    ev.append(PrecisionEvidence(
        evidence_type="authority_snapshot",
        strength=strength,
        source="authority_35c",
        payload={
            "freshness": fresh,
            "gaps": authority.get("gaps", []) or [],
            "deterministic_signature": authority.get("deterministic_signature"),
        },
        freshness=status,
        confidence=str(fresh.get("confidence", "unknown")),
    ))
    ev.append(PrecisionEvidence(
        evidence_type="routability",
        strength=EvidenceStrength.GROUNDED if routability else EvidenceStrength.UNKNOWN,
        source="entity_registry_31e",
        payload={
            "active_routable_total": sum(1 for e in routability if e.get("routable") and e.get("operational_state") == "active" and not e.get("deprecated")),
            "total_entities": len(routability),
        },
        freshness="fresh" if routability else "unknown",
        confidence="high" if routability else "unknown",
    ))
    ev.append(PrecisionEvidence(
        evidence_type="incidents",
        strength=EvidenceStrength.GROUNDED if incidents else EvidenceStrength.PARTIAL,
        source="incident_intelligence_36a",
        payload={
            "active_incidents_total": ((incidents.get("incidents", {}) or {}).get("active_incidents_total")) if isinstance(incidents, dict) else None,
            "highest_severity": ((incidents.get("incidents", {}) or {}).get("highest_severity")) if isinstance(incidents, dict) else None,
        },
        freshness="fresh" if incidents else "partial",
        confidence="medium" if incidents else "low",
    ))

    ev.append(PrecisionEvidence(
        evidence_type="codebase",
        strength=EvidenceStrength.GROUNDED if codebase else EvidenceStrength.PARTIAL,
        source="gitnexus_memory_dev36x",
        payload={
            "modules_total": codebase.get("modules_total") if isinstance(codebase, dict) else None,
            "edges_total": codebase.get("edges_total") if isinstance(codebase, dict) else None,
            "structural_health_score": ((codebase.get("score", {}) or {}).get("structural_health_score")) if isinstance(codebase, dict) else None,
        },
        freshness="fresh" if codebase else "partial",
        confidence="high" if codebase else "low",
    ))
    return [e.to_dict() for e in ev]


def build_runtime_precision_report(
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}
    sensor_snapshot = sensor_snapshot or {}

    try:
        from runtime.authority import build_live_authority_snapshot
        authority = build_live_authority_snapshot(extra_ctx=extra_ctx)
    except Exception:
        authority = {"contract_version": "35C", "freshness": {"status": "unavailable", "confidence": "low", "reasons": ["authority_error"]}, "gaps": ["authority"], "generated_at": _now()}

    try:
        from runtime.entities.entity_registry import (
            build_routability_summary,
            build_discoverable_entities,
            build_inventory_entities,
        )
        routability = build_routability_summary(sensor_snapshot, extra_ctx)
        discoverable = _sanitize_discoverables(build_discoverable_entities(sensor_snapshot, extra_ctx))
        inventory = build_inventory_entities(sensor_snapshot, extra_ctx)
    except Exception:
        routability = []
        discoverable = []
        inventory = []

    try:
        from runtime.incidents.incident_summary import build_incident_intelligence_summary
        incidents = build_incident_intelligence_summary(extra_ctx=extra_ctx)
    except Exception:
        incidents = {}

    try:
        from runtime.codebase.gitnexus_memory import build_codebase_summary
        codebase = build_codebase_summary(extra_ctx=extra_ctx)
    except Exception:
        codebase = {}

    partial_states = _detect_partial_states(authority, routability)
    conflicts = _detect_authority_conflicts(authority, routability)

    authority_conf = calculate_authority_confidence(authority)
    obs_conf = calculate_observability_confidence(authority)
    routing_conf = calculate_routing_confidence(routability)
    incident_conf = calculate_incident_confidence(incidents)
    codebase_conf = calculate_codebase_confidence(codebase)
    operational_conf = calculate_operational_confidence(
        authority_conf=authority_conf,
        observability_conf=obs_conf,
        routing_conf=routing_conf,
        incident_conf=incident_conf,
        codebase_conf=codebase_conf,
        partial_total=len(partial_states),
        conflict_total=len(conflicts),
    )

    certainty = OperationalCertainty.CONFIRMED if operational_conf.label == "high" and not partial_states and not conflicts else OperationalCertainty.UNCERTAIN

    evidence = _build_evidence_catalog(authority, routability, incidents, codebase)
    precision_score = float(operational_conf.score)
    confidence_integrity = 100.0 if not conflicts and not partial_states else max(40.0, 100.0 - (len(conflicts) * 20.0 + len(partial_states) * 10.0))

    payload = {
        "contract_version": PRECISION_CONTRACT_VERSION,
        "generated_at": _now(),
        "authority": {
            "contract_version": authority.get("contract_version", "35C"),
            "freshness": authority.get("freshness", {}) or {},
            "gaps": authority.get("gaps", []) or [],
            "deterministic_signature": authority.get("deterministic_signature"),
        },
        "confidence": {
            "operational": operational_conf.to_dict(),
            "authority": authority_conf.to_dict(),
            "observability": obs_conf.to_dict(),
            "routing": routing_conf.to_dict(),
            "incidents": incident_conf.to_dict(),
            "codebase": codebase_conf.to_dict(),
        },
        "evidence": evidence,
        "conflicts": conflicts,
        "partial": partial_states,
        "discoverable": {
            "total": len(discoverable),
            "entities": discoverable[:50],
        },
        "inventory": {
            "total": len(inventory),
        },
        "precision": {
            "operational_precision_score": round(precision_score, 2),
            "confidence_integrity_score": round(float(confidence_integrity), 2),
            "authority_conflicts_total": len(conflicts),
            "partial_state_total": len(partial_states),
            "stale_evidence_total": sum(1 for r in (authority_conf.reasons or []) if "unavailable" in r or "stale" in r),
            "discovery_leakage_total": 0,
            "precision_degraded_responses_total": 1 if certainty == OperationalCertainty.UNCERTAIN else 0,
            "confidence_downgrade_total": len(partial_states) + len(conflicts),
        },
    }
    payload["deterministic_signature"] = _hash({
        "authority": payload.get("authority"),
        "confidence": payload.get("confidence"),
        "precision": payload.get("precision"),
        "conflicts": payload.get("conflicts"),
        "partial": payload.get("partial"),
        "discoverable_total": payload.get("discoverable", {}).get("total"),
        "inventory_total": payload.get("inventory", {}).get("total"),
    })

    if os.environ.get("AI_LAB_ENABLE_PRECISION_ARTIFACTS", "true").lower() in ("true", "1", "yes"):
        _write_artifact("/tmp/36b-precision-summary.json", payload)
        _write_artifact("/tmp/36b-confidence-report.json", payload.get("confidence", {}) or {})
        _write_artifact("/tmp/36b-authority-conflicts.json", {"conflicts": payload.get("conflicts", [])})
        _write_artifact("/tmp/36b-partial-states.json", {"partial": payload.get("partial", [])})
        _write_artifact("/tmp/36b-evidence-ranking.json", {"evidence": payload.get("evidence", [])})
        _write_artifact("/tmp/36b-precision-score.json", payload.get("precision", {}) or {})
    return payload


def build_precision_summary(report: dict[str, Any]) -> dict[str, Any]:
    conf = ((report.get("confidence", {}) or {}).get("operational", {}) or {})
    label = str(conf.get("label", "unknown"))
    score = float(conf.get("score", 0.0) or 0.0)

    auth = report.get("authority", {}) or {}
    fresh = (auth.get("freshness", {}) or {}).get("status", "unknown")
    discoverable_total = int((report.get("discoverable", {}) or {}).get("total", 0) or 0)
    inventory_total = int((report.get("inventory", {}) or {}).get("total", 0) or 0)
    precision = report.get("precision", {}) or {}

    lines = [
        "Runtime operational.",
        f"Authority: {fresh}.",
        f"Discoverable: {discoverable_total} (not operational).",
        f"Inventory-only: {inventory_total}.",
        f"Confidence: {label} ({round(score, 1)}).",
    ]
    if precision.get("authority_conflicts_total"):
        lines.append(f"Authority conflicts: {precision.get('authority_conflicts_total')}.")
    if precision.get("partial_state_total"):
        lines.append(f"Partial evidence: {precision.get('partial_state_total')}.")
    lines = [ln for ln in lines if ln][:8]

    summ = PrecisionSummary(
        lines=lines,
        confidence=ConfidenceScore(score=score, label=label, reasons=list(conf.get("reasons", []) or [])),
        certainty=OperationalCertainty.CONFIRMED if label == "high" else OperationalCertainty.UNCERTAIN,
        determinism_signature=_hash({"lines": lines, "conf": conf, "sig": report.get("deterministic_signature")}),
    ).to_dict()
    return {
        "contract_version": PRECISION_CONTRACT_VERSION,
        "precision_summary": summ,
    }
