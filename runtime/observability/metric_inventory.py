"""FASE OBS-31A: Metric inventory catalog.

Creates a complete inventory of all runtime metrics with
domain, criticality, source, and freshness metadata.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any


class MetricCriticality(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class MetricEntry:
    metric_name: str = ""
    domain: str = ""
    criticality: str = MetricCriticality.LOW.value
    source: str = "prometheus"
    query_valid: bool = True
    observed: bool = True
    used_by_runtime: bool = False
    used_by_dashboard: bool = False
    freshness_status: str = "fresh"
    semantic_owner: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "domain": self.domain,
            "criticality": self.criticality,
            "source": self.source,
            "query_valid": self.query_valid,
            "observed": self.observed,
            "used_by_runtime": self.used_by_runtime,
            "used_by_dashboard": self.used_by_dashboard,
            "freshness_status": self.freshness_status,
            "semantic_owner": self.semantic_owner,
        }


_CRITICAL_METRICS = [
    MetricEntry("ailab_first_token_latency_ms", "latency", "critical", used_by_runtime=True, used_by_dashboard=True, semantic_owner="runtime"),
    MetricEntry("ailab_request_total_latency_ms", "latency", "critical", used_by_runtime=True, used_by_dashboard=True, semantic_owner="runtime"),
    MetricEntry("ailab_slo_state", "slo", "critical", used_by_runtime=True, used_by_dashboard=True, semantic_owner="slo"),
    MetricEntry("ailab_degradation_level", "slo", "critical", used_by_runtime=True, used_by_dashboard=True, semantic_owner="slo"),
    MetricEntry("ailab_runtime_timeout_rate", "slo", "critical", used_by_runtime=True, used_by_dashboard=True, semantic_owner="slo"),
    MetricEntry("ailab_runtime_gpu_pressure", "slo", "critical", used_by_runtime=True, used_by_dashboard=True, semantic_owner="slo"),
    MetricEntry("ailab_runtime_vram_pressure", "slo", "critical", used_by_runtime=True, used_by_dashboard=True, semantic_owner="slo"),
    MetricEntry("ailab_circuit_breaker_state", "slo", "critical", used_by_runtime=True, used_by_dashboard=True, semantic_owner="slo"),
    MetricEntry("ailab_slo_violations_total", "slo", "critical", used_by_runtime=True, used_by_dashboard=True, semantic_owner="slo"),
    MetricEntry("ailab_route_family_total", "routing", "critical", used_by_runtime=True, used_by_dashboard=True, semantic_owner="routing"),
    MetricEntry("ailab_profile_total", "routing", "high", used_by_runtime=True, used_by_dashboard=True, semantic_owner="routing"),
    MetricEntry("ailab_greeting_fastpath_total", "routing", "medium", used_by_runtime=True, used_by_dashboard=True, semantic_owner="routing"),
    MetricEntry("ailab_qwen_escalation_total", "routing", "medium", used_by_runtime=True, used_by_dashboard=True, semantic_owner="routing"),
    MetricEntry("ailab_stream_chunks_total", "streaming", "high", used_by_runtime=True, used_by_dashboard=True, semantic_owner="streaming"),
    MetricEntry("ailab_stream_stalls_total", "streaming", "high", used_by_runtime=True, used_by_dashboard=True, semantic_owner="streaming"),
    MetricEntry("ailab_stream_finish_inconsistent_total", "streaming", "critical", used_by_runtime=True, used_by_dashboard=True, semantic_owner="streaming"),
    MetricEntry("ailab_tool_call_total", "tools", "medium", used_by_runtime=True, used_by_dashboard=True, semantic_owner="governance"),
    MetricEntry("ailab_tool_empty_arguments_total", "tools", "medium", used_by_runtime=True, used_by_dashboard=True, semantic_owner="governance"),
    MetricEntry("ailab_memory_recall_total", "memory", "high", used_by_runtime=True, used_by_dashboard=True, semantic_owner="memory"),
    MetricEntry("ailab_memory_contamination_risk", "memory", "high", used_by_runtime=True, used_by_dashboard=True, semantic_owner="memory"),
    MetricEntry("ailab_quality_score", "quality", "high", used_by_runtime=True, used_by_dashboard=True, semantic_owner="quality"),
    MetricEntry("ailab_hallucination_risk", "quality", "critical", used_by_runtime=True, used_by_dashboard=True, semantic_owner="quality"),
    MetricEntry("ailab_gpu_active_requests", "gpu", "high", used_by_runtime=True, used_by_dashboard=True, semantic_owner="gpu"),
    MetricEntry("ailab_gpu_estimated_utilization_pct", "gpu", "high", used_by_runtime=True, used_by_dashboard=True, semantic_owner="gpu"),
    MetricEntry("ailab_cognitive_summary_total", "cognitive", "medium", used_by_runtime=True, used_by_dashboard=False, semantic_owner="cognitive"),
    MetricEntry("ailab_sensor_fusion_total", "sensor", "high", used_by_runtime=True, used_by_dashboard=True, semantic_owner="sensor"),
    MetricEntry("ailab_sensor_fusion_missing_source_total", "sensor", "high", used_by_runtime=True, used_by_dashboard=True, semantic_owner="sensor"),
    MetricEntry("ailab_runtime_grounding_validation_total", "grounding", "high", used_by_runtime=True, used_by_dashboard=False, semantic_owner="grounding"),
    MetricEntry("ailab_runtime_grounding_rejected_total", "grounding", "high", used_by_runtime=True, used_by_dashboard=False, semantic_owner="grounding"),
    MetricEntry("ailab_deprecated_model_routing_total", "routing", "medium", used_by_runtime=True, used_by_dashboard=True, semantic_owner="routing"),
    MetricEntry("ailab_gateway_uptime_seconds", "gateway", "high", used_by_runtime=True, used_by_dashboard=True, semantic_owner="gateway"),
    MetricEntry("ailab_gateway_boot_total", "gateway", "medium", used_by_runtime=True, used_by_dashboard=True, semantic_owner="gateway"),
    MetricEntry("ailab_report_evidence_score", "evidence", "high", used_by_runtime=True, used_by_dashboard=False, semantic_owner="evidence"),
    MetricEntry("ailab_report_hallucination_suppressed_total", "evidence", "high", used_by_runtime=True, used_by_dashboard=False, semantic_owner="evidence"),
    MetricEntry("ailab_observed_runtime_context_size_bytes", "sensor", "info", used_by_runtime=True, used_by_dashboard=False, semantic_owner="sensor"),
]

_HIGH_METRICS = [
    MetricEntry("ailab_stream_first_chunk_ms", "streaming", "high", used_by_runtime=True, used_by_dashboard=True, semantic_owner="streaming"),
    MetricEntry("ailab_stream_chunk_cadence_ms", "streaming", "high", used_by_runtime=True, used_by_dashboard=True, semantic_owner="streaming"),
    MetricEntry("ailab_tokens_per_second", "gpu", "high", used_by_runtime=True, used_by_dashboard=True, semantic_owner="gpu"),
    MetricEntry("ailab_model_load_seconds", "gpu", "high", used_by_runtime=True, used_by_dashboard=True, semantic_owner="gpu"),
    MetricEntry("ailab_queue_wait_seconds", "gpu", "high", used_by_runtime=True, used_by_dashboard=True, semantic_owner="gpu"),
    MetricEntry("ailab_executor_commands_total", "agentic", "high", used_by_runtime=True, used_by_dashboard=False, semantic_owner="agentic"),
    MetricEntry("ailab_agentic_executions_total", "agentic", "high", used_by_runtime=True, used_by_dashboard=False, semantic_owner="agentic"),
    MetricEntry("ailab_report_grounding_total", "reporting", "high", used_by_runtime=True, used_by_dashboard=False, semantic_owner="reporting"),
    MetricEntry("ailab_agentic_risk_score", "agentic", "medium", used_by_runtime=True, used_by_dashboard=False, semantic_owner="agentic"),
    MetricEntry("ailab_sandbox_mutations_total", "sandbox", "high", used_by_runtime=True, used_by_dashboard=False, semantic_owner="sandbox"),
    MetricEntry("ailab_sandbox_policy_denied_total", "sandbox", "high", used_by_runtime=True, used_by_dashboard=False, semantic_owner="sandbox"),
    MetricEntry("ailab_context_cap_exceeded_total", "memory", "medium", used_by_runtime=True, used_by_dashboard=False, semantic_owner="memory"),
    MetricEntry("ailab_completion_truncated_total", "quality", "medium", used_by_runtime=True, used_by_dashboard=False, semantic_owner="quality"),
    MetricEntry("ailab_governance_blocked_actions_total", "governance", "high", used_by_runtime=True, used_by_dashboard=True, semantic_owner="governance"),
    MetricEntry("ailab_governance_blocked_actions_by_reason_total", "governance", "high", used_by_runtime=True, used_by_dashboard=True, semantic_owner="governance"),
    MetricEntry("ailab_cold_start_total", "gpu", "high", used_by_runtime=True, used_by_dashboard=True, semantic_owner="gpu"),
    MetricEntry("ailab_disabled_model_selection_total", "routing", "medium", used_by_runtime=True, used_by_dashboard=True, semantic_owner="routing"),
    MetricEntry("ailab_llama_fastpath_total", "routing", "medium", used_by_runtime=True, used_by_dashboard=True, semantic_owner="routing"),
]

_MEDIUM_METRICS = [
    MetricEntry("ailab_runtime_maturity_state", "runtime", "medium", used_by_runtime=True, used_by_dashboard=True, semantic_owner="runtime"),
    MetricEntry("ailab_runtime_maturity_phase", "runtime", "medium", used_by_runtime=True, used_by_dashboard=True, semantic_owner="runtime"),
    MetricEntry("ailab_runtime_model_state", "runtime", "medium", used_by_runtime=True, used_by_dashboard=True, semantic_owner="runtime"),
    MetricEntry("ailab_memory_chars_injected", "memory", "medium", used_by_runtime=True, used_by_dashboard=False, semantic_owner="memory"),
    MetricEntry("ailab_memory_items_total", "memory", "medium", used_by_runtime=True, used_by_dashboard=False, semantic_owner="memory"),
    MetricEntry("ailab_agentic_plans_total", "agentic", "medium", used_by_runtime=True, used_by_dashboard=False, semantic_owner="agentic"),
    MetricEntry("ailab_agentic_dry_runs_total", "agentic", "medium", used_by_runtime=True, used_by_dashboard=False, semantic_owner="agentic"),
    MetricEntry("ailab_agentic_approvals_requested_total", "agentic", "medium", used_by_runtime=True, used_by_dashboard=False, semantic_owner="agentic"),
    MetricEntry("ailab_runtime_context_autoinjected_total", "reporting", "medium", used_by_runtime=True, used_by_dashboard=False, semantic_owner="reporting"),
    MetricEntry("ailab_cognitive_summary_signal_count", "cognitive", "low", used_by_runtime=True, used_by_dashboard=False, semantic_owner="cognitive"),
    MetricEntry("ailab_cognitive_summary_confidence", "cognitive", "low", used_by_runtime=True, used_by_dashboard=False, semantic_owner="cognitive"),
    MetricEntry("ailab_operational_model_selected_total", "routing", "low", used_by_runtime=True, used_by_dashboard=False, semantic_owner="routing"),
    MetricEntry("ailab_coding_model_selected_total", "routing", "low", used_by_runtime=True, used_by_dashboard=False, semantic_owner="routing"),
    MetricEntry("ailab_prompt_checksum_changes_total", "governance", "low", used_by_runtime=True, used_by_dashboard=False, semantic_owner="governance"),
    MetricEntry("ailab_report_evidence_guard_total", "evidence", "medium", used_by_runtime=True, used_by_dashboard=False, semantic_owner="evidence"),
    MetricEntry("ailab_report_evidence_guard_scoped_total", "evidence", "medium", used_by_runtime=True, used_by_dashboard=False, semantic_owner="evidence"),
]

_INFO_METRICS = [
    MetricEntry("ailab_router_chat_requests_total", "routing", "info", used_by_runtime=False, used_by_dashboard=False, semantic_owner="routing"),
    MetricEntry("ailab_embedding_input_chars", "memory", "info", used_by_runtime=False, used_by_dashboard=False, semantic_owner="memory"),
    MetricEntry("ailab_embedding_truncations_total", "memory", "info", used_by_runtime=False, used_by_dashboard=False, semantic_owner="memory"),
    MetricEntry("ailab_recall_query_chars", "memory", "info", used_by_runtime=False, used_by_dashboard=False, semantic_owner="memory"),
    MetricEntry("ailab_sensor_fusion_duration_ms", "sensor", "info", used_by_runtime=False, used_by_dashboard=False, semantic_owner="sensor"),
    MetricEntry("ailab_cognitive_summary_generation_duration_ms", "cognitive", "info", used_by_runtime=False, used_by_dashboard=False, semantic_owner="cognitive"),
    MetricEntry("ailab_executor_duration_ms", "agentic", "info", used_by_runtime=False, used_by_dashboard=False, semantic_owner="agentic"),
    MetricEntry("ailab_checkpoint_trace_total", "governance", "info", used_by_runtime=False, used_by_dashboard=False, semantic_owner="governance"),
    MetricEntry("ailab_agentic_execution_duration_ms", "agentic", "info", used_by_runtime=False, used_by_dashboard=False, semantic_owner="agentic"),
    MetricEntry("ailab_sandbox_mutation_duration_seconds", "sandbox", "info", used_by_runtime=False, used_by_dashboard=False, semantic_owner="sandbox"),
]

_ALL_METRICS = _CRITICAL_METRICS + _HIGH_METRICS + _MEDIUM_METRICS + _INFO_METRICS


def build_metric_inventory() -> list[dict[str, Any]]:
    return [m.to_dict() for m in _ALL_METRICS]


def build_observability_health_score(
    targets_healthy: int = 0,
    targets_total: int = 0,
    dashboards_healthy: int = 0,
    dashboards_total: int = 0,
    no_data_panels: int = 0,
    stale_metrics: int = 0,
    query_failures: int = 0,
    runtime_alignment_score: float = 1.0,
) -> dict[str, Any]:
    target_score = (targets_healthy / max(targets_total, 1)) * 100
    dashboard_score = (dashboards_healthy / max(dashboards_total, 1)) * 100
    penalty = (no_data_panels * 2) + (stale_metrics * 1) + (query_failures * 3)
    alignment_weighted = runtime_alignment_score * 100
    raw_score = (target_score * 0.3 + dashboard_score * 0.3 + alignment_weighted * 0.4) - penalty
    final_score = max(0.0, min(100.0, raw_score))

    if final_score >= 90:
        level = "healthy"
    elif final_score >= 70:
        level = "degraded"
    elif final_score >= 50:
        level = "unhealthy"
    else:
        level = "critical"

    return {
        "score": round(final_score, 1),
        "level": level,
        "components": {
            "targets_score": round(target_score, 1),
            "dashboard_score": round(dashboard_score, 1),
            "alignment_score": round(runtime_alignment_score * 100, 1),
        },
        "penalties": {
            "no_data_panels": no_data_panels,
            "stale_metrics": stale_metrics,
            "query_failures": query_failures,
            "total_penalty": penalty,
        },
        "timestamp": time.time(),
    }
