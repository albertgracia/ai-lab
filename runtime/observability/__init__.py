"""FASE OBS-31A: Observability Source-of-Truth Audit.

Converts Prometheus + Loki + Grafana into a fully validated,
coherent operational truth plane aligned with AI-LAB cognitive runtime.
"""

from runtime.observability.contracts import (
    OBSERVABILITY_CONTRACT_VERSION,
    build_observability_source_contract,
    build_dashboard_contract,
    build_metric_contract,
    build_datasource_contract,
)
from runtime.observability.prometheus_audit import (
    PrometheusTargetStatus,
    audit_prometheus_targets,
    classify_scrape_target,
    build_prometheus_audit_summary,
)
from runtime.observability.dashboard_validator import (
    DashboardHealth,
    DashboardValidationResult,
    DashboardValidator,
)
from runtime.observability.drift_detector import (
    DriftDetectionResult,
    DriftDetector,
    build_drift_summary,
)
from runtime.observability.loki_audit import (
    LokiStreamStatus,
    audit_loki,
    build_loki_audit_summary,
)
from runtime.observability.metric_inventory import (
    MetricEntry,
    MetricCriticality,
    build_metric_inventory,
    build_observability_health_score,
)

__all__ = [
    "OBSERVABILITY_CONTRACT_VERSION",
    "build_observability_source_contract",
    "build_dashboard_contract",
    "build_metric_contract",
    "build_datasource_contract",
    "PrometheusTargetStatus",
    "audit_prometheus_targets",
    "classify_scrape_target",
    "build_prometheus_audit_summary",
    "DashboardHealth",
    "DashboardValidationResult",
    "DashboardValidator",
    "DriftDetectionResult",
    "DriftDetector",
    "build_drift_summary",
    "LokiStreamStatus",
    "audit_loki",
    "build_loki_audit_summary",
    "MetricEntry",
    "MetricCriticality",
    "build_metric_inventory",
    "build_observability_health_score",
]
