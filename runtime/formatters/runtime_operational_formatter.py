from __future__ import annotations

import json
from typing import Any

from runtime.formatters.gpu_operational_formatter import format_gpu_operational_block


def _confidence_score(domain_confidence: dict[str, str]) -> float:
    weights = {"high": 1.0, "medium": 0.6, "low": 0.2}
    if not domain_confidence:
        return 0.0
    values = [weights.get(value, 0.0) for value in domain_confidence.values()]
    return round(sum(values) / len(values), 2)


def _aggregate_freshness(source_quality: dict[str, Any]) -> str:
    statuses = []
    for item in source_quality.values():
        freshness = item.get("freshness", {}) if isinstance(item, dict) else {}
        status = freshness.get("status")
        if status:
            statuses.append(status)
    if not statuses:
        return "unavailable"
    if any(status == "expired" for status in statuses):
        return "expired"
    if any(status == "stale" for status in statuses):
        return "stale"
    if all(status == "fresh" for status in statuses):
        return "fresh"
    return "unavailable"


def format_runtime_topology(runtime_context: dict[str, Any]) -> str:
    topology_mode = runtime_context.get("topology_mode") or runtime_context.get("runtime_topology", {}).get("mode", "unknown")
    summaries = runtime_context.get("gpu_operational_summaries", [])
    active = sum(1 for item in summaries if item.get("operational_state") == "active")
    expected_offline = sum(1 for item in summaries if item.get("observed_state") == "expected_offline")
    return "\n".join([
        f"topology={topology_mode}",
        f"active_gpu_backends={active}",
        f"expected_offline_backends={expected_offline}",
    ])


def format_runtime_health(runtime_context: dict[str, Any]) -> str:
    topology_mode = runtime_context.get("topology_mode") or runtime_context.get("runtime_topology", {}).get("mode", "unknown")
    runtime_state = "healthy_degraded" if topology_mode == "degraded_single_gpu" else "healthy"
    return "\n".join([
        f"runtime_state={runtime_state}",
        f"grounding=verified",
    ])


def format_runtime_domain_confidence(runtime_context: dict[str, Any], domain: str = "gpu_nodes") -> str:
    domain_confidence = runtime_context.get("domain_confidence", {}) if isinstance(runtime_context.get("domain_confidence"), dict) else {}
    source_quality = runtime_context.get("source_quality", {}) if isinstance(runtime_context.get("source_quality"), dict) else {}
    target_quality = source_quality.get(domain, {}) if isinstance(source_quality.get(domain), dict) else {}
    freshness = target_quality.get("freshness", {}) if isinstance(target_quality.get("freshness"), dict) else {}
    source = target_quality.get("source_of_truth", []) if isinstance(target_quality.get("source_of_truth"), list) else []
    return "\n".join([
        f"domain={domain}",
        f"confidence={domain_confidence.get(domain, 'unknown')}",
        f"freshness={freshness.get('status', 'unavailable')}",
        f"source={'+'.join(source) if source else 'unknown'}",
    ])


def format_runtime_cluster_state(runtime_context: dict[str, Any]) -> str:
    domain_confidence = runtime_context.get("domain_confidence", {}) if isinstance(runtime_context.get("domain_confidence"), dict) else {}
    source_quality = runtime_context.get("source_quality", {}) if isinstance(runtime_context.get("source_quality"), dict) else {}

    # FASE 31B: Runtime maturity context
    try:
        from runtime.semantics.runtime_maturity import calculate_runtime_maturity
        maturity = calculate_runtime_maturity(runtime_context)
        mat_state = maturity.get("runtime_state", "unknown")
        mat_conf = maturity.get("confidence", "unknown")
        degraded = maturity.get("degraded_domains", [])
        impact = maturity.get("operational_impact", "none")
        uncertainty = maturity.get("uncertainty_level", "none")
    except ImportError:
        mat_state = format_runtime_health(runtime_context).split("=")[-1] if "=" in format_runtime_health(runtime_context) else "unknown"
        mat_conf = "unknown"
        degraded = []
        impact = "none"
        uncertainty = "none"

    lines = [
        "AI-LAB Runtime",
        format_runtime_topology(runtime_context),
        f"runtime_state={mat_state}",
        f"confidence={mat_conf}",
        f"sensor_confidence={_confidence_score(domain_confidence)}",
        f"observability_freshness={_aggregate_freshness(source_quality)}",
        f"operational_impact={impact}",
        f"uncertainty={uncertainty}",
    ]
    if degraded:
        lines.append(f"degraded_domains={','.join(degraded)}")
    return "\n".join(lines)


def compact_runtime_response(
    user_text: str,
    runtime_context_json: str | dict[str, Any] | None,
    *,
    profile: str = "operational_compact",
) -> str | None:
    if profile not in {"operational_compact", "operational_verbose", "operational_debug"}:
        return None
    if runtime_context_json is None:
        return None
    if isinstance(runtime_context_json, str):
        try:
            runtime_context = json.loads(runtime_context_json)
        except json.JSONDecodeError:
            return None
    else:
        runtime_context = runtime_context_json
    text = (user_text or "").lower().strip()
    summaries = runtime_context.get("gpu_operational_summaries", []) if isinstance(runtime_context.get("gpu_operational_summaries"), list) else []
    if any(term in text for term in ("rx9070", "rx7900xt", "gpu")):
        target = None
        if "rx9070" in text:
            target = "rx9070"
        elif "rx7900xt" in text:
            target = "rx7900xt"
        block = format_gpu_operational_block(summaries, target_gpu=target, mode=profile)
        if profile == "operational_verbose":
            return block + "\n\ncontract=30I-D"
        if profile == "operational_debug":
            return block + f"\n\ndomain_confidence={runtime_context.get('domain_confidence', {})}"
        return block
    if "confianza" in text and "sensor" in text:
        return format_runtime_domain_confidence(runtime_context, domain="gpu_nodes")
    if "runtime" in text or "ai-lab" in text or "cluster" in text:
        return format_runtime_cluster_state(runtime_context)
    return None
