"""FASE 30I-G: Deterministic Runtime Grounding.

Provides grounding validation layer: positive entity verification (entity registry),
post-response validation against observed runtime, and unknown-state semantics
for claims without runtime evidence.

Architecture:
  denylist (evidence_guard) → entity registry (positive validation) → unknown-state (fallback)
"""

from __future__ import annotations

import json
import re
from typing import Any

from runtime.context.runtime_entity_registry import RuntimeEntityRegistry


GROUNDING_CONTRACT_VERSION = "30I-G"

UNKNOWN_STATE_TOKENS = frozenset({
    "NOT_OBSERVED",
    "NO_RUNTIME_EVIDENCE",
    "SOURCE_UNAVAILABLE",
    "STALE_EVIDENCE",
    "LOW_CONFIDENCE",
})


_OPERATIONAL_GROUNDING_PATTERNS = (
    "estado gpu", "estado runtime", "estado de gpu", "gpu rx9070",
    "gpu rx7900xt", "confianza de los sensores", "health del gateway",
    "topology del cluster", "storage backup", "cómo está",
    "qué tal está", "qué gpu", "qué modelo", "qué servicios",
    "qué hosts", "ai-lab runtime", "estado de los servicios",
    "estado del sistema", "qué nodos", "qué inferencia",
)

_ENTITY_REFERENCE_PATTERN = re.compile(
    r"\b(?:gpu|modelo|host|servicio|storage|nodo|backend|"
    r"gateway|router|runtime|cluster|topology|node)\b",
    re.IGNORECASE,
)


def is_runtime_grounded_prompt(user_text: str) -> bool:
    if not user_text or not isinstance(user_text, str):
        return False
    text = user_text.strip().lower()
    if len(text) < 4:
        return False
    for pattern in _OPERATIONAL_GROUNDING_PATTERNS:
        if pattern in text:
            return True
    if _ENTITY_REFERENCE_PATTERN.search(text):
        return True
    ctx_terms = ("observado", "observada", "evidencia", "fuente", "confianza",
                 "freshness", "source_of_truth", "estado operativo")
    return any(t in text for t in ctx_terms)


def extract_runtime_entities(
    user_text: str,
    entity_registry: RuntimeEntityRegistry | None = None,
) -> dict[str, list[dict[str, str]]]:
    found: dict[str, list[dict[str, str]]] = {
        "gpu": [], "model": [], "host": [], "service": [],
        "storage": [], "topology_mode": [],
    }
    if not user_text:
        return found
    text = user_text.strip().lower()
    gpu_patterns = [re.compile(rf"(?i)\b{re.escape(gpu)}\b") for gpu in
                    ("rx9070", "rx7900xt", "rx 9070", "rx 7900 xt")]
    for pat in gpu_patterns:
        if pat.search(text):
            found["gpu"].append({"name": pat.pattern.strip("(?i)\\b"), "match_type": "pattern"})

    model_terms = ("llama", "qwen", "nomic", "embed")
    for term in model_terms:
        if term in text:
            found["model"].append({"name": term, "match_type": "keyword"})

    host_terms = ("192.168.1.30", "192.168.1.50", "192.168.1.60", "192.168.1.40",
                  "ubuntu-ialab", "192.168.1.200")
    for term in host_terms:
        if term in text:
            found["host"].append({"name": term, "match_type": "pattern"})

    svc_terms = ("gateway", "router", "live-api", "prometheus", "grafana",
                 "metrics", "docs", "heartbeat")
    for term in svc_terms:
        if term in text:
            found["service"].append({"name": term, "match_type": "keyword"})

    if "storage" in text or "backup" in text or "archive" in text or "disco" in text:
        found["storage"].append({"name": "storage", "match_type": "keyword"})

    topo_terms = ("single-node", "degraded", "topology", "cluster")
    for term in topo_terms:
        if term in text:
            found["topology_mode"].append({"name": term, "match_type": "keyword"})

    if entity_registry:
        for etype in found:
            filtered = []
            for entry in found[etype]:
                ename = entry["name"].replace("rx 9070", "rx9070").replace("rx 7900 xt", "rx7900xt")
                if entity_registry.is_observed(etype, ename):
                    entry["observed"] = True
                else:
                    entry["observed"] = False
                filtered.append(entry)
            found[etype] = filtered

    return found


def validate_runtime_claim(
    claim: str,
    entity_registry: RuntimeEntityRegistry | None = None,
) -> dict[str, Any]:
    if not claim:
        return {
            "valid": False, "reason": "empty_claim",
            "unknown_state": "NOT_OBSERVED",
        }
    text = claim.lower().strip()
    if not entity_registry:
        return {
            "valid": True, "reason": "no_registry_available",
            "unknown_state": None,
        }

    forbidden = entity_registry.get_forbidden_patterns()
    forbidden_gpus = {g.lower() for g in forbidden.get("forbidden_gpus", set())}
    all_gpu_patterns = list(forbidden_gpus) + ["rx9070", "rx7900xt"]
    gpu_refs = re.findall(r"(?i)\b(" + "|".join(re.escape(g) for g in all_gpu_patterns) + r")\b", text)
    for ref in gpu_refs:
        rl = ref.lower()
        if rl in forbidden_gpus:
            return {
                "valid": False, "reason": f"gpu_not_observed:{rl}",
                "unknown_state": "NOT_OBSERVED",
            }
        if not entity_registry.is_observed("gpu", rl):
            return {
                "valid": False, "reason": f"gpu_not_observed:{rl}",
                "unknown_state": "NOT_OBSERVED",
            }
        entities = entity_registry.get_observed_entities().get("gpu", [])
        for ent in entities:
            if ent.get("name", "").lower() == rl:
                conf = ent.get("confidence", "low")
                if conf == "low":
                    return {
                        "valid": False, "reason": f"gpu_low_confidence:{rl}",
                        "unknown_state": "LOW_CONFIDENCE",
                    }

    forbidden_platforms = {p.lower() for p in forbidden.get("forbidden_platforms", set())}
    platform_refs = re.findall(r"(?i)\b(" + "|".join(re.escape(p) for p in forbidden_platforms) + r")\b", text)
    for ref in platform_refs:
        return {
            "valid": False, "reason": f"external_platform_not_observed:{ref}",
            "unknown_state": "NOT_OBSERVED",
        }

    model_refs = re.findall(r"(?i)\b(llama|qwen|nomic|gpt|claude|gemini)\b", text)
    for ref in model_refs:
        known = entity_registry.get_known_models()
        if not any(ref in m.lower() for m in known):
            return {
                "valid": False, "reason": f"model_not_observed:{ref}",
                "unknown_state": "NOT_OBSERVED",
            }

    return {
        "valid": True, "reason": None,
        "unknown_state": None,
    }


def build_grounding_envelope(
    user_text: str,
    runtime_context: dict[str, Any] | None = None,
    entity_registry: RuntimeEntityRegistry | None = None,
) -> dict[str, Any]:
    if entity_registry is None and runtime_context:
        entity_registry = RuntimeEntityRegistry(runtime_context)

    envelope: dict[str, Any] = {
        "contract_version": "30I-G",
        "grounded": False,
        "intent_detected": False,
        "observed_entities": {},
        "forbidden_patterns": {},
        "unknown_state": None,
        "confidence": "low",
    }

    if not user_text:
        return envelope

    envelope["intent_detected"] = is_runtime_grounded_prompt(user_text)

    if entity_registry:
        envelope["observed_entities"] = entity_registry.get_observed_entities()
        envelope["forbidden_patterns"] = entity_registry.get_forbidden_patterns()
        envelope["grounded"] = True
        envelope["confidence"] = "high"

    return envelope


def filter_unobserved_claims(
    text: str,
    entity_registry: RuntimeEntityRegistry | None = None,
) -> tuple[str, list[str]]:
    if not text:
        return text, []
    if not entity_registry:
        return text, []

    unobserved: list[str] = []

    forbidden = entity_registry.get_forbidden_patterns()
    forbidden_gpus = {g.lower() for g in forbidden.get("forbidden_gpus", set())}
    all_gpu_patterns = list(forbidden_gpus) + ["rx9070", "rx7900xt"]
    gpu_refs = re.findall(r"(?i)\b(" + "|".join(re.escape(g) for g in all_gpu_patterns) + r")\b", text)
    for ref in gpu_refs:
        rl = ref.lower()
        if rl in forbidden_gpus:
            unobserved.append(f"gpu_not_observed:{ref}")
            text = re.sub(rf"(?i)\b{re.escape(ref)}\b", f"[NO OBSERVADO: {ref}]", text)
        elif not entity_registry.is_observed("gpu", rl):
            unobserved.append(f"gpu_not_observed:{ref}")
            text = re.sub(rf"(?i)\b{re.escape(ref)}\b", f"[NO OBSERVADO: {ref}]", text)

    model_refs = re.findall(r"(?i)\b(Llama|Qwen|Nomic|GPT|Claude|Gemini)\b", text)
    known_models = entity_registry.get_known_models()
    for ref in model_refs:
        if not any(ref.lower() in m.lower() for m in known_models):
            unobserved.append(f"model_not_observed:{ref}")
            text = re.sub(rf"(?i)\b{re.escape(ref)}\b", f"[NO OBSERVADO: {ref}]", text)

    ip_refs = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text)
    known_hosts = entity_registry.get_known_hosts()
    for ip in ip_refs:
        if ip not in known_hosts:
            unobserved.append(f"unknown_ip:{ip}")
            text = re.sub(rf"\b{re.escape(ip)}\b", f"[NO OBSERVADO: {ip}]", text)

    if unobserved:
        text += "\n\n---\n[GROUNDING] Las siguientes entidades no estan observadas en el runtime activo:"
        for u in unobserved:
            text += f"\n- {u}"

    return text, unobserved


def validate_response_against_observed_runtime(
    response_text: str,
    runtime_context: dict[str, Any] | None = None,
    entity_registry: RuntimeEntityRegistry | None = None,
) -> dict[str, Any]:
    if entity_registry is None and runtime_context:
        entity_registry = RuntimeEntityRegistry(runtime_context)

    result: dict[str, Any] = {
        "valid": True,
        "unknown_state": None,
        "unverified_claims": [],
        "sanitized_text": response_text,
        "evidence_score": 1.0,
        "invented_entities": [],
    }

    if not response_text or not entity_registry:
        return result

    sanitized, unobserved = filter_unobserved_claims(response_text, entity_registry)

    result["unverified_claims"] = unobserved
    result["sanitized_text"] = sanitized

    if unobserved:
        result["valid"] = False
        result["evidence_score"] = max(0.0, 1.0 - (0.15 * len(unobserved)))
        result["invented_entities"] = [
            c.split(":", 1)[1] if ":" in c else c
            for c in unobserved
        ]
        if len(unobserved) >= 5:
            result["unknown_state"] = "NOT_OBSERVED"

    return result
