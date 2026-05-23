"""FASE 36A: Operational Incident Intelligence.

Deterministic, grounded incident detection and correlation engine.
No LLM used — all hypotheses derived from authority/observability/topology evidence.

Keep __init__.py import-light to avoid importing the full incident engine.
"""

from __future__ import annotations

from runtime.incidents.contracts import (
    INCIDENT_CONTRACT_VERSION,
    DOMAIN_DEPENDENCY_MAP,
    CORRELATION_DOMAINS,
    SEVERITY_ORDER,
    IncidentSignal,
)

__all__ = [
    "INCIDENT_CONTRACT_VERSION",
    "DOMAIN_DEPENDENCY_MAP",
    "CORRELATION_DOMAINS",
    "SEVERITY_ORDER",
    "IncidentSignal",
    # Lazy re-exports.
    "build_incident_intelligence_report",
    "detect_authority_incidents",
    "detect_observability_incidents",
    "detect_validation_incidents",
    "detect_governance_incidents",
    "detect_topology_incidents",
    "detect_semantic_incidents",
    "detect_fastpath_incidents",
    "detect_infrastructure_incidents",
    "detect_performance_incidents",
    "detect_storage_incidents",
    "detect_gpu_incidents",
    "detect_execution_incidents",
    "correlate_incident_signals",
    "calculate_incident_blast_radius",
    "build_incident_hypotheses",
    "build_incident_recommendations",
    "build_blast_radius_summary",
]


_LAZY = {
    "build_incident_intelligence_report": ("runtime.incidents.incident_intelligence", "build_incident_intelligence_report"),
    "detect_authority_incidents": ("runtime.incidents.incident_intelligence", "detect_authority_incidents"),
    "detect_observability_incidents": ("runtime.incidents.incident_intelligence", "detect_observability_incidents"),
    "detect_validation_incidents": ("runtime.incidents.incident_intelligence", "detect_validation_incidents"),
    "detect_governance_incidents": ("runtime.incidents.incident_intelligence", "detect_governance_incidents"),
    "detect_topology_incidents": ("runtime.incidents.incident_intelligence", "detect_topology_incidents"),
    "detect_semantic_incidents": ("runtime.incidents.incident_intelligence", "detect_semantic_incidents"),
    "detect_fastpath_incidents": ("runtime.incidents.incident_intelligence", "detect_fastpath_incidents"),
    "detect_infrastructure_incidents": ("runtime.incidents.incident_intelligence", "detect_infrastructure_incidents"),
    "detect_performance_incidents": ("runtime.incidents.incident_intelligence", "detect_performance_incidents"),
    "detect_storage_incidents": ("runtime.incidents.incident_intelligence", "detect_storage_incidents"),
    "detect_gpu_incidents": ("runtime.incidents.incident_intelligence", "detect_gpu_incidents"),
    "detect_execution_incidents": ("runtime.incidents.incident_intelligence", "detect_execution_incidents"),
    "correlate_incident_signals": ("runtime.incidents.incident_intelligence", "correlate_incident_signals"),
    "calculate_incident_blast_radius": ("runtime.incidents.incident_intelligence", "calculate_incident_blast_radius"),
    "build_incident_hypotheses": ("runtime.incidents.incident_intelligence", "build_incident_hypotheses"),
    "build_incident_recommendations": ("runtime.incidents.incident_intelligence", "build_incident_recommendations"),
    "build_blast_radius_summary": ("runtime.incidents.incident_intelligence", "build_blast_radius_summary"),
}


def __getattr__(name: str):
    target = _LAZY.get(name)
    if not target:
        raise AttributeError(name)
    import importlib
    module_name, attr = target
    mod = importlib.import_module(module_name)
    return getattr(mod, attr)


def __dir__() -> list[str]:
    return sorted(set(list(globals().keys()) + list(_LAZY.keys())))
