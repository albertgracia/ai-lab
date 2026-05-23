"""FASE 36A: Operational Incident Intelligence.

Deterministic, grounded incident detection and correlation engine.
No LLM used — all hypotheses derived from authority/observability/topology evidence.
"""

from runtime.incidents.contracts import (
    INCIDENT_CONTRACT_VERSION,
    DOMAIN_DEPENDENCY_MAP,
    CORRELATION_DOMAINS,
    SEVERITY_ORDER,
    IncidentSignal,
)
from runtime.incidents.incident_intelligence import (
    build_incident_intelligence_report,
    detect_authority_incidents,
    detect_observability_incidents,
    detect_validation_incidents,
    detect_governance_incidents,
    detect_topology_incidents,
    detect_semantic_incidents,
    detect_fastpath_incidents,
    detect_infrastructure_incidents,
    detect_performance_incidents,
    detect_storage_incidents,
    detect_gpu_incidents,
    detect_execution_incidents,
    correlate_incident_signals,
    calculate_incident_blast_radius,
    build_incident_hypotheses,
    build_incident_recommendations,
    build_blast_radius_summary,
)

__all__ = [
    "INCIDENT_CONTRACT_VERSION",
    "DOMAIN_DEPENDENCY_MAP",
    "CORRELATION_DOMAINS",
    "SEVERITY_ORDER",
    "IncidentSignal",
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
