"""FASE 36C — Operator Intent Reasoning.

Deterministic classification of operator intent. This layer reasons about what
kind of operational answer is safe, but never executes or authorizes actions.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

OPERATOR_INTENT_CONTRACT_VERSION = "36C"


class OperatorIntentCategory(str, Enum):
    FAST_STATUS = "FAST_STATUS"
    FAST_INFRASTRUCTURE = "FAST_INFRASTRUCTURE"
    FAST_GPU_STATUS = "FAST_GPU_STATUS"
    FAST_OBSERVABILITY = "FAST_OBSERVABILITY"
    DIAGNOSTIC = "DIAGNOSTIC"
    TROUBLESHOOTING = "TROUBLESHOOTING"
    FORENSIC_ANALYSIS = "FORENSIC_ANALYSIS"
    INCIDENT_INVESTIGATION = "INCIDENT_INVESTIGATION"
    ARCHITECTURAL_REASONING = "ARCHITECTURAL_REASONING"
    PLANNING = "PLANNING"
    CAPACITY_ANALYSIS = "CAPACITY_ANALYSIS"
    MULTI_GPU_PREPARATION = "MULTI_GPU_PREPARATION"
    REMEDIATION_DISCUSSION = "REMEDIATION_DISCUSSION"
    IMPLEMENTATION_REQUEST = "IMPLEMENTATION_REQUEST"
    CODE_CHANGE_REQUEST = "CODE_CHANGE_REQUEST"
    UNKNOWN = "UNKNOWN"
    AMBIGUOUS = "AMBIGUOUS"
    MIXED_INTENT = "MIXED_INTENT"


@dataclass(frozen=True)
class OperatorIntentResult:
    contract_version: str
    category: str
    confidence: dict[str, Any]
    reason_codes: list[str] = field(default_factory=list)
    matched_terms: list[str] = field(default_factory=list)
    ambiguity: dict[str, Any] = field(default_factory=dict)
    safety: dict[str, Any] = field(default_factory=dict)
    authority: dict[str, Any] = field(default_factory=dict)
    precision: dict[str, Any] = field(default_factory=dict)
    explainability: dict[str, Any] = field(default_factory=dict)
    generated_at: float = 0.0
    deterministic_signature: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _strict_mode() -> bool:
    return os.environ.get("STRICT_VALIDATION_MODE", "false").lower() in ("true", "1", "yes")


def _now() -> float:
    return 0.0 if _strict_mode() else time.time()


def _hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _norm(text: str | None) -> str:
    t = (text or "").lower().strip()
    t = re.sub(r"\s+", " ", t)
    return t


def _term_matches(text: str, term: str) -> bool:
    escaped = re.escape(term)
    return re.search(rf"(?<![\w-]){escaped}(?![\w-])", text, flags=re.IGNORECASE) is not None


_MARKERS: dict[str, tuple[str, list[tuple[str, str]]]] = {
    OperatorIntentCategory.FAST_STATUS.value: ("fast", [
        ("estado runtime", "status_query"), ("runtime status", "status_query"),
        ("estado del runtime", "status_query"), ("como esta el runtime", "status_query"),
        ("cómo está el runtime", "status_query"), ("health del gateway", "status_query"),
    ]),
    OperatorIntentCategory.FAST_INFRASTRUCTURE.value: ("fast", [
        ("infraestructura", "infrastructure_terms"), ("infrastructure", "infrastructure_terms"),
        ("nodos", "infrastructure_terms"), ("control plane", "infrastructure_terms"),
        ("qué es 192.", "infrastructure_terms"), ("que es 192.", "infrastructure_terms"),
    ]),
    OperatorIntentCategory.FAST_GPU_STATUS.value: ("fast", [
        ("gpu", "gpu_terms"), ("rx9070", "gpu_terms"), ("rx7900", "gpu_terms"),
        ("vram", "gpu_terms"), ("modelos operacionales", "model_truth_query"),
        ("modelos están operacionales", "model_truth_query"), ("modelos estan operacionales", "model_truth_query"),
    ]),
    OperatorIntentCategory.FAST_OBSERVABILITY.value: ("fast", [
        ("observabilidad", "observability_terms"), ("observability", "observability_terms"),
        ("prometheus", "observability_terms"), ("grafana", "observability_terms"),
        ("exporters", "observability_terms"), ("targets", "observability_terms"),
        ("scrape", "observability_terms"), ("down", "observability_terms"),
    ]),
    OperatorIntentCategory.DIAGNOSTIC.value: ("deep", [
        ("diagnost", "diagnostic_terms"), ("analiza", "diagnostic_terms"),
        ("por qué", "diagnostic_terms"), ("por que", "diagnostic_terms"),
        ("root cause", "diagnostic_terms"), ("falla", "diagnostic_terms"),
        ("error", "diagnostic_terms"),
    ]),
    OperatorIntentCategory.TROUBLESHOOTING.value: ("deep", [
        ("troubleshoot", "troubleshooting_terms"), ("debug", "troubleshooting_terms"),
        ("qué está roto", "troubleshooting_terms"), ("que esta roto", "troubleshooting_terms"),
        ("roto", "troubleshooting_terms"), ("no funciona", "troubleshooting_terms"),
    ]),
    OperatorIntentCategory.FORENSIC_ANALYSIS.value: ("deep", [
        ("forense", "forensic_terms"), ("forensic", "forensic_terms"),
        ("postmortem", "forensic_terms"), ("timeline", "forensic_terms"),
        ("secuencia", "forensic_terms"), ("histórico", "forensic_terms"),
    ]),
    OperatorIntentCategory.INCIDENT_INVESTIGATION.value: ("deep", [
        ("incidente", "incident_keywords"), ("incident", "incident_keywords"),
        ("p0", "incident_keywords"), ("p1", "incident_keywords"),
        ("sev", "incident_keywords"), ("outage", "incident_keywords"),
    ]),
    OperatorIntentCategory.ARCHITECTURAL_REASONING.value: ("architecture", [
        ("arquitectura", "architecture_terms"), ("architecture", "architecture_terms"),
        ("rediseñar", "architecture_terms"), ("redisenar", "architecture_terms"),
        ("blast radius", "architecture_terms"), ("hotspots", "architecture_terms"),
        ("riesgos arquitectónicos", "architecture_terms"), ("riesgos arquitectonicos", "architecture_terms"),
    ]),
    OperatorIntentCategory.PLANNING.value: ("planning", [
        ("plan", "planning_terms"), ("roadmap", "planning_terms"),
        ("preparar", "planning_terms"), ("siguiente fase", "planning_terms"),
    ]),
    OperatorIntentCategory.CAPACITY_ANALYSIS.value: ("planning", [
        ("capacidad", "capacity_terms"), ("capacity", "capacity_terms"),
        ("vram", "capacity_terms"), ("throughput", "capacity_terms"),
        ("latencia", "capacity_terms"), ("carga", "capacity_terms"),
    ]),
    OperatorIntentCategory.MULTI_GPU_PREPARATION.value: ("planning", [
        ("multi-gpu", "multi_gpu_terms"), ("multigpu", "multi_gpu_terms"),
        ("rx7900xt", "multi_gpu_terms"), ("scheduler", "multi_gpu_terms"),
        ("failover", "multi_gpu_terms"), ("warm pool", "multi_gpu_terms"),
        ("queue arbitration", "multi_gpu_terms"),
    ]),
    OperatorIntentCategory.REMEDIATION_DISCUSSION.value: ("remediation", [
        ("cómo arreglar", "remediation_markers"), ("como arreglar", "remediation_markers"),
        ("cómo solucion", "remediation_markers"), ("como solucion", "remediation_markers"),
        ("remediation", "remediation_markers"), ("remediación", "remediation_markers"),
        ("remediacion", "remediation_markers"), ("mitigar", "remediation_markers"),
    ]),
    OperatorIntentCategory.IMPLEMENTATION_REQUEST.value: ("implementation", [
        ("implementa", "implementation_request"), ("implementar", "implementation_request"),
        ("build", "implementation_request"), ("añade", "implementation_request"),
        ("agrega", "implementation_request"), ("crea", "implementation_request"),
    ]),
    OperatorIntentCategory.CODE_CHANGE_REQUEST.value: ("implementation", [
        ("cambia el código", "code_change_request"), ("cambia el codigo", "code_change_request"),
        ("modifica", "code_change_request"), ("refactor", "code_change_request"),
        ("corrige el bug", "code_change_request"), ("fix the bug", "code_change_request"),
        ("tests", "code_change_request"),
    ]),
}

_ACTION_TERMS = ("ejecuta", "reinicia", "restart", "borra", "delete", "rm -rf", "sudo", "aplica", "deploy", "despliega")
_DANGEROUS_TERMS = ("rm -rf", "shutdown", "reboot", "format", "borrar", "eliminar", "drop database", "systemctl restart")


def _score_text(text: str) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    scores: dict[str, dict[str, Any]] = {}
    reason_codes: list[str] = []
    matched_terms: list[str] = []
    for category, (_group, markers) in _MARKERS.items():
        count = 0
        cat_reasons: list[str] = []
        cat_terms: list[str] = []
        for term, reason in markers:
            if _term_matches(text, term):
                count += 1
                cat_reasons.append(reason)
                cat_terms.append(term)
        if count:
            base = min(1.0, 0.42 + (count * 0.23))
            scores[category] = {"score": round(base, 3), "group": _group, "reasons": sorted(set(cat_reasons)), "terms": cat_terms}
            reason_codes.extend(cat_reasons)
            matched_terms.extend(cat_terms)
    return scores, sorted(set(reason_codes)), sorted(set(matched_terms))


def _select_category(scores: dict[str, dict[str, Any]], text: str) -> tuple[str, dict[str, Any]]:
    if not text:
        return OperatorIntentCategory.UNKNOWN.value, {"score": 0.0, "label": "unknown", "reasons": ["empty_input"]}
    if not scores:
        return OperatorIntentCategory.UNKNOWN.value, {"score": 0.2, "label": "low", "reasons": ["no_intent_markers"]}

    ranked = sorted(scores.items(), key=lambda kv: (-float(kv[1]["score"]), kv[0]))
    top_cat, top = ranked[0]
    active_groups = sorted({str(v.get("group")) for _k, v in ranked if float(v.get("score", 0.0)) >= 0.5})
    strong_cats = [k for k, v in ranked if float(v.get("score", 0.0)) >= 0.65]

    if len(active_groups) >= 2 and len(strong_cats) >= 2:
        return OperatorIntentCategory.MIXED_INTENT.value, {"score": min(0.86, float(top["score"])), "label": "medium", "reasons": ["multiple_intent_groups"]}
    top_group = str(ranked[0][1].get("group"))
    second_group = str(ranked[1][1].get("group")) if len(ranked) > 1 else top_group
    if len(strong_cats) >= 2 and top_group != second_group and abs(float(ranked[0][1]["score"]) - float(ranked[1][1]["score"])) <= 0.12:
        return OperatorIntentCategory.AMBIGUOUS.value, {"score": 0.48, "label": "low", "reasons": ["close_intent_scores"]}

    score = float(top["score"])
    label = "high" if score >= 0.82 else "medium" if score >= 0.55 else "low"
    return top_cat, {"score": round(score, 3), "label": label, "reasons": list(top.get("reasons", []))}


def _authority_context(authority_snapshot: dict[str, Any] | None) -> dict[str, Any]:
    if not authority_snapshot:
        return {"available": False, "freshness": "unknown", "confidence": "unknown", "reason": "authority_not_provided"}
    fresh = (authority_snapshot.get("freshness", {}) or {}) if isinstance(authority_snapshot, dict) else {}
    return {
        "available": True,
        "freshness": fresh.get("status", "unknown"),
        "confidence": fresh.get("confidence", "unknown"),
        "gaps": authority_snapshot.get("gaps", []) if isinstance(authority_snapshot, dict) else [],
    }


def _precision_context(precision_report: dict[str, Any] | None) -> dict[str, Any]:
    if not precision_report:
        return {"available": False, "certainty": "unknown", "reason": "precision_not_provided"}
    precision = precision_report.get("precision", {}) or {}
    return {
        "available": True,
        "operational_precision_score": precision.get("operational_precision_score", 0.0),
        "partial_state_total": precision.get("partial_state_total", 0),
        "authority_conflicts_total": precision.get("authority_conflicts_total", 0),
    }


def _safety(text: str, category: str) -> dict[str, Any]:
    action_markers = [term for term in _ACTION_TERMS if term in text]
    dangerous_markers = [term for term in _DANGEROUS_TERMS if term in text]
    remediation_like = category in {
        OperatorIntentCategory.REMEDIATION_DISCUSSION.value,
        OperatorIntentCategory.IMPLEMENTATION_REQUEST.value,
        OperatorIntentCategory.CODE_CHANGE_REQUEST.value,
        OperatorIntentCategory.MIXED_INTENT.value,
    }
    return {
        "can_execute": False,
        "execution_authority": "none",
        "remediation_authority": "discussion_only" if remediation_like else "none",
        "infrastructure_mutation_authority": "none",
        "requires_human_confirmation": bool(action_markers or dangerous_markers or remediation_like),
        "unsafe_action_markers": sorted(set(dangerous_markers)),
        "action_markers": sorted(set(action_markers)),
        "guards": [
            "NO_AUTONOMOUS_EXECUTION",
            "NO_REMEDIATION_AUTHORITY",
            "NO_INFRASTRUCTURE_MUTATION",
            "NO_INFERRED_OPERATIONAL_TRUTH",
        ],
    }


def analyze_operator_intent(
    text: str | None,
    *,
    authority_snapshot: dict[str, Any] | None = None,
    precision_report: dict[str, Any] | None = None,
    memory_context: dict[str, Any] | None = None,
    gitnexus_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    t = _norm(text)
    scores, reason_codes, matched_terms = _score_text(t)
    category, confidence = _select_category(scores, t)
    authority = _authority_context(authority_snapshot)
    precision = _precision_context(precision_report)

    degraded_reasons: list[str] = []
    if not authority.get("available"):
        degraded_reasons.append("authority_not_provided")
    elif authority.get("freshness") in ("stale", "aged", "unavailable", "unknown"):
        degraded_reasons.append("authority_not_fresh")
    if not precision.get("available"):
        degraded_reasons.append("precision_not_provided")
    elif int(precision.get("partial_state_total", 0) or 0) > 0:
        degraded_reasons.append("precision_partial")

    confidence = dict(confidence)
    if degraded_reasons and category not in (OperatorIntentCategory.UNKNOWN.value, OperatorIntentCategory.AMBIGUOUS.value):
        confidence["degraded"] = True
        confidence["degraded_reasons"] = degraded_reasons
    else:
        confidence["degraded"] = False
        confidence["degraded_reasons"] = []

    ranked = sorted(scores.items(), key=lambda kv: (-float(kv[1].get("score", 0.0)), kv[0]))
    ambiguity = {
        "is_ambiguous": category == OperatorIntentCategory.AMBIGUOUS.value,
        "is_mixed": category == OperatorIntentCategory.MIXED_INTENT.value,
        "candidates": [
            {"category": cat, "score": data.get("score"), "group": data.get("group"), "reasons": data.get("reasons", [])}
            for cat, data in ranked[:5]
        ],
    }
    safety = _safety(t, category)
    explainability = {
        "reason_codes": reason_codes,
        "matched_terms": matched_terms,
        "authority_used": bool(authority_snapshot),
        "precision_used": bool(precision_report),
        "memory_context_readonly": bool(memory_context),
        "gitnexus_context_readonly": bool(gitnexus_context),
        "memory_overrides_authority": False,
    }
    generated_at = _now()
    signature_payload = {
        "text": t,
        "category": category,
        "confidence": confidence,
        "reason_codes": reason_codes,
        "matched_terms": matched_terms,
        "ambiguity": ambiguity,
        "safety": safety,
        "authority": authority,
        "precision": precision,
    }
    result = OperatorIntentResult(
        contract_version=OPERATOR_INTENT_CONTRACT_VERSION,
        category=category,
        confidence=confidence,
        reason_codes=reason_codes,
        matched_terms=matched_terms,
        ambiguity=ambiguity,
        safety=safety,
        authority=authority,
        precision=precision,
        explainability=explainability,
        generated_at=generated_at,
        deterministic_signature=_hash(signature_payload),
    )
    return result.to_dict()


def classify_operator_intent(text: str | None) -> str:
    return str(analyze_operator_intent(text).get("category", OperatorIntentCategory.UNKNOWN.value))
