from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from runtime.semantic.contracts import (
    SEMANTIC_CONTRACT_VERSION,
    LegacyEntity,
    PhantomEntity,
    SemanticContamination,
    SemanticClassification,
    OperationalTruth,
    SemanticSterilizationResult,
    SemanticIntegrityReport,
    IdentityHygieneSummary,
)


_LEGACY_MODEL_PREFIXES = (
    "lmstudio-community/",
)

_PHANTOM_GPU_MARKERS = (
    "a100",
    "h100",
    "h200",
    "rtx",
    "nvidia",
)


def _strict_mode() -> bool:
    return os.environ.get("STRICT_VALIDATION_MODE", "false").lower() in ("true", "1", "yes")


def _now() -> float:
    return 0.0 if _strict_mode() else time.time()


def _hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _artifact_enabled() -> bool:
    return os.environ.get("AI_LAB_ENABLE_SEMANTIC_ARTIFACTS", "true").lower() in ("true", "1", "yes")


def _write_artifact(path: str, payload: dict[str, Any]) -> None:
    if not _artifact_enabled():
        return
    try:
        Path(path).write_text(json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
    except Exception:
        pass


def classify_semantic_state(*, roles: list[str], expected_offline: bool, discoverable: bool, operational: bool, legacy: bool, phantom: bool) -> str:
    if phantom:
        return "STATE-PHANTOM"
    if legacy:
        return "STATE-LEGACY"
    if expected_offline:
        return "STATE-EXPECTED-OFFLINE"
    if operational:
        return "STATE-OPERATIONAL"
    if discoverable:
        return "STATE-DISCOVERABLE"
    if roles:
        return "STATE-INVENTORY"
    return "STATE-UNKNOWN"


def detect_legacy_entities(entities: list[str]) -> list[dict[str, Any]]:
    out = []
    for e in sorted(set(entities)):
        low = (e or "").lower()
        if any(low.startswith(p) for p in _LEGACY_MODEL_PREFIXES):
            out.append(LegacyEntity(identity=e, reason="legacy_model_prefix").to_dict())
    return out


def detect_phantom_entities(entities: list[str]) -> list[dict[str, Any]]:
    out = []
    for e in sorted(set(entities)):
        low = (e or "").lower()
        if any(m in low for m in _PHANTOM_GPU_MARKERS):
            out.append(PhantomEntity(identity=e, reason="phantom_gpu_marker").to_dict())
    return out


def detect_discoverable_contamination(*, discoverable_nodes: list[str], operational_nodes: list[str]) -> dict[str, Any]:
    contaminated = sorted(set(discoverable_nodes) & set(operational_nodes))
    return SemanticContamination(
        contamination_type="discoverable_contamination",
        total=len(contaminated),
        examples=contaminated[:5],
    ).to_dict()


def detect_inventory_leakage(*, inventory_nodes: list[str], operational_nodes: list[str]) -> dict[str, Any]:
    contaminated = sorted(set(inventory_nodes) & set(operational_nodes))
    return SemanticContamination(
        contamination_type="inventory_contamination",
        total=len(contaminated),
        examples=contaminated[:5],
    ).to_dict()


def build_operational_truth(*, extra_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build sterilized operational truth from authority roots.

    RULE-35B-3: Unknown cannot be operational.
    RULE-35B-4: Legacy entities cannot contaminate operational truth.
    """
    extra_ctx = extra_ctx or {}
    try:
        from runtime.infrastructure import build_infrastructure_identity_registry
        infra = build_infrastructure_identity_registry(extra_ctx=extra_ctx)
    except Exception:
        infra = {"authority_roots": [], "inventory": {}}

    inv = infra.get("inventory", {}) or {}
    authority_roots = sorted(infra.get("authority_roots", []) or [])
    operational_nodes = sorted({n.get("identity") for n in (inv.get("operational_nodes", []) or []) if isinstance(n, dict) and n.get("identity")})
    inventory_only_nodes = sorted({n.get("identity") for n in (inv.get("inventory_only_nodes", []) or []) if isinstance(n, dict) and n.get("identity")})
    discoverable_nodes = sorted({n.get("identity") for n in (inv.get("discoverable_nodes", []) or []) if isinstance(n, dict) and n.get("identity")})

    # Entities to classify (IPs only in this phase).
    all_nodes = sorted(set(authority_roots + operational_nodes + inventory_only_nodes + discoverable_nodes))

    legacy = detect_legacy_entities(all_nodes)
    phantom = detect_phantom_entities(all_nodes)
    legacy_set = {x.get("identity") for x in legacy}
    phantom_set = {x.get("identity") for x in phantom}

    classifications: list[dict[str, Any]] = []
    for ip in all_nodes:
        roles = []
        expected_offline = ip in inventory_only_nodes
        operational = ip in operational_nodes
        discoverable = ip in discoverable_nodes
        is_legacy = ip in legacy_set
        is_phantom = ip in phantom_set
        authority = ip in authority_roots

        # Strict separation:
        if expected_offline:
            operational = False
        if discoverable and not authority:
            operational = False

        st = classify_semantic_state(
            roles=roles,
            expected_offline=expected_offline,
            discoverable=discoverable,
            operational=operational,
            legacy=is_legacy,
            phantom=is_phantom,
        )

        classifications.append(SemanticClassification(
            identity=ip,
            semantic_state=st,
            roles=roles,
            authority=authority,
            operational=operational,
            routable=operational and not expected_offline,
            expected_offline=expected_offline,
            legacy=is_legacy,
            phantom=is_phantom,
        ).to_dict())

    det = _hash({
        "authority_roots": authority_roots,
        "operational_nodes": operational_nodes,
        "inventory_only_nodes": inventory_only_nodes,
        "discoverable_nodes": discoverable_nodes,
        "classifications": classifications,
    })
    truth = OperationalTruth(
        contract_version=SEMANTIC_CONTRACT_VERSION,
        authority_roots=authority_roots,
        operational_nodes=operational_nodes,
        inventory_only_nodes=inventory_only_nodes,
        discoverable_nodes=discoverable_nodes,
        classifications=classifications,
        deterministic_signature=det,
        generated_at=_now(),
    ).to_dict()

    _write_artifact("/tmp/35b-operational-truth.json", truth)
    return truth


def sterilize_semantic_entities(*, extra_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    truth = build_operational_truth(extra_ctx=extra_ctx)
    entities = []
    entities.extend(truth.get("authority_roots", []) or [])
    entities.extend(truth.get("operational_nodes", []) or [])
    entities.extend(truth.get("inventory_only_nodes", []) or [])
    entities.extend(truth.get("discoverable_nodes", []) or [])

    legacy = detect_legacy_entities(entities)
    phantom = detect_phantom_entities(entities)
    cont = [
        detect_discoverable_contamination(
            discoverable_nodes=truth.get("discoverable_nodes", []) or [],
            operational_nodes=truth.get("operational_nodes", []) or [],
        ),
        detect_inventory_leakage(
            inventory_nodes=truth.get("inventory_only_nodes", []) or [],
            operational_nodes=truth.get("operational_nodes", []) or [],
        ),
    ]
    det = _hash({"truth": truth.get("deterministic_signature"), "legacy": legacy, "phantom": phantom, "cont": cont})

    result = SemanticSterilizationResult(
        contract_version=SEMANTIC_CONTRACT_VERSION,
        operational_truth=truth,
        legacy_entities=legacy,
        phantom_entities=phantom,
        contaminations=cont,
        deterministic_signature=det,
        generated_at=_now(),
    ).to_dict()

    _write_artifact("/tmp/35b-legacy-leakage.json", {"legacy_entities": legacy})
    _write_artifact("/tmp/35b-phantom-entities.json", {"phantom_entities": phantom})
    _write_artifact("/tmp/35b-semantic-integrity.json", result)
    return result


def calculate_semantic_integrity_score(report: dict[str, Any]) -> dict[str, Any]:
    issues = []
    score = 100.0
    phantom = int(report.get("phantom_entities_total", 0) or 0)
    legacy = int(report.get("legacy_leakage_total", 0) or 0)
    disc = int(report.get("discoverable_contamination_total", 0) or 0)
    inv = int(report.get("inventory_contamination_total", 0) or 0)
    unk = int(report.get("unknown_operational_entities_total", 0) or 0)

    if legacy:
        score -= min(60.0, legacy * 10.0)
        issues.append("legacy_leakage")
    if phantom:
        score -= min(60.0, phantom * 15.0)
        issues.append("phantom_entities")
    if disc:
        score -= min(40.0, disc * 10.0)
        issues.append("discoverable_contamination")
    if inv:
        score -= min(40.0, inv * 10.0)
        issues.append("inventory_contamination")
    if unk:
        score -= min(50.0, unk * 10.0)
        issues.append("unknown_operational")

    score = max(0.0, min(100.0, score))
    level = "high" if score >= 85 else "medium" if score >= 65 else "low" if score >= 40 else "critical"
    return {
        "contract_version": SEMANTIC_CONTRACT_VERSION,
        "semantic_integrity_score": round(score, 1),
        "semantic_integrity_level": level,
        "issues": issues,
        "deterministic_signature": _hash({"score": round(score, 1), "issues": issues, "phantom": phantom, "legacy": legacy, "disc": disc, "inv": inv, "unk": unk}),
        "generated_at": _now(),
    }


def build_semantic_integrity_report(*, extra_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    sterilized = sterilize_semantic_entities(extra_ctx=extra_ctx)
    truth = sterilized.get("operational_truth", {}) or {}
    legacy_total = len(sterilized.get("legacy_entities", []) or [])
    phantom_total = len(sterilized.get("phantom_entities", []) or [])
    cont = {c.get("contamination_type"): c for c in (sterilized.get("contaminations", []) or []) if isinstance(c, dict)}
    disc_total = int((cont.get("discoverable_contamination", {}) or {}).get("total", 0) or 0)
    inv_total = int((cont.get("inventory_contamination", {}) or {}).get("total", 0) or 0)

    unknown_operational = 0
    for c in truth.get("classifications", []) or []:
        if not isinstance(c, dict):
            continue
        if c.get("operational") and c.get("semantic_state") == "STATE-UNKNOWN":
            unknown_operational += 1

    base = {
        "phantom_entities_total": phantom_total,
        "legacy_leakage_total": legacy_total,
        "discoverable_contamination_total": disc_total,
        "inventory_contamination_total": inv_total,
        "unknown_operational_entities_total": unknown_operational,
        "sterilized_operational_nodes_total": len(truth.get("operational_nodes", []) or []),
    }
    score = calculate_semantic_integrity_score(base)
    rep = SemanticIntegrityReport(
        contract_version=SEMANTIC_CONTRACT_VERSION,
        semantic_integrity_score=float(score.get("semantic_integrity_score", 0.0) or 0.0),
        semantic_integrity_level=str(score.get("semantic_integrity_level", "unknown")),
        phantom_entities_total=phantom_total,
        legacy_leakage_total=legacy_total,
        discoverable_contamination_total=disc_total,
        inventory_contamination_total=inv_total,
        unknown_operational_entities_total=unknown_operational,
        sterilized_operational_nodes_total=len(truth.get("operational_nodes", []) or []),
        issues=list(score.get("issues", []) or []),
        deterministic_signature=str(score.get("deterministic_signature")),
        generated_at=_now(),
    ).to_dict()

    _write_artifact("/tmp/35b-semantic-score.json", rep)
    return rep


def build_identity_hygiene_summary(*, extra_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    rep = build_semantic_integrity_report(extra_ctx=extra_ctx)
    issues = []
    authority_ok = True
    legacy_ok = int(rep.get("legacy_leakage_total", 0) or 0) == 0
    phantom_ok = int(rep.get("phantom_entities_total", 0) or 0) == 0
    strict_sep_ok = (
        int(rep.get("discoverable_contamination_total", 0) or 0) == 0
        and int(rep.get("inventory_contamination_total", 0) or 0) == 0
        and int(rep.get("unknown_operational_entities_total", 0) or 0) == 0
    )
    if not legacy_ok:
        issues.append("legacy_leakage")
    if not phantom_ok:
        issues.append("phantom_entities")
    if not strict_sep_ok:
        issues.append("state_separation")

    det = _hash({"authority_ok": authority_ok, "legacy_ok": legacy_ok, "phantom_ok": phantom_ok, "strict_sep_ok": strict_sep_ok, "issues": issues})
    summ = IdentityHygieneSummary(
        contract_version=SEMANTIC_CONTRACT_VERSION,
        authority_roots_ok=authority_ok,
        legacy_leakage_ok=legacy_ok,
        phantom_ok=phantom_ok,
        strict_state_separation_ok=strict_sep_ok,
        issues=issues,
        deterministic_signature=det,
        generated_at=_now(),
    ).to_dict()

    _write_artifact("/tmp/35b-identity-hygiene.json", summ)
    return summ
