"""FASE OBS-31A.2: Observability source-of-truth contracts.

Defines contracts for observability layers:
- source contract: Prometheus → runtime
- dashboard contract: Grafana → runtime alignment
- metric contract: individual metric specification
- datasource contract: datasource validity
- alignment contract: runtime ↔ Grafana alignment
- inventory contract: dashboard inventory metadata
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

OBSERVABILITY_CONTRACT_VERSION = "OBS-31A"


@dataclass
class ObservabilitySourceContract:
    prometheus_up: bool = False
    loki_up: bool = False
    grafana_up: bool = False
    targets_healthy: int = 0
    targets_degraded: int = 0
    targets_expected_offline: int = 0
    targets_stale: int = 0
    targets_orphan: int = 0
    targets_total: int = 0
    dashboards_healthy: int = 0
    dashboards_stale: int = 0
    dashboards_broken: int = 0
    dashboards_total: int = 0
    runtime_alignment_score: float = 0.0
    stale_metrics_count: int = 0
    no_data_panels_count: int = 0
    query_validation_failures: int = 0
    contract_version: str = OBSERVABILITY_CONTRACT_VERSION
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "timestamp": self.timestamp,
            "prometheus_up": self.prometheus_up,
            "loki_up": self.loki_up,
            "grafana_up": self.grafana_up,
            "targets": {
                "healthy": self.targets_healthy,
                "degraded": self.targets_degraded,
                "expected_offline": self.targets_expected_offline,
                "stale": self.targets_stale,
                "orphan": self.targets_orphan,
                "total": self.targets_total,
            },
            "dashboards": {
                "healthy": self.dashboards_healthy,
                "stale": self.dashboards_stale,
                "broken": self.dashboards_broken,
                "total": self.dashboards_total,
            },
            "runtime_alignment_score": round(self.runtime_alignment_score, 2),
            "stale_metrics_count": self.stale_metrics_count,
            "no_data_panels_count": self.no_data_panels_count,
            "query_validation_failures": self.query_validation_failures,
        }


@dataclass
class DashboardContract:
    uid: str = ""
    title: str = ""
    panels_total: int = 0
    panels_broken: int = 0
    panels_no_data: int = 0
    datasource_valid: bool = True
    datasource_uid: str = ""
    runtime_domain: str = ""
    criticality: str = "low"
    semantic_owner: str = ""
    health: str = "unknown"
    deprecated: bool = False
    experimental: bool = False
    inventory_aligned: bool = True
    runtime_aligned: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "uid": self.uid,
            "title": self.title,
            "panels_total": self.panels_total,
            "panels_broken": self.panels_broken,
            "panels_no_data": self.panels_no_data,
            "datasource_valid": self.datasource_valid,
            "datasource_uid": self.datasource_uid,
            "runtime_domain": self.runtime_domain,
            "criticality": self.criticality,
            "semantic_owner": self.semantic_owner,
            "health": self.health,
            "deprecated": self.deprecated,
            "experimental": self.experimental,
            "inventory_aligned": self.inventory_aligned,
            "runtime_aligned": self.runtime_aligned,
        }


@dataclass
class MetricContract:
    metric_name: str = ""
    domain: str = ""
    criticality: str = "low"
    source_of_truth: str = "prometheus"
    query_valid: bool = True
    observed: bool = True
    used_by_runtime: bool = False
    used_by_dashboard: bool = False
    freshness_status: str = "unknown"
    semantic_owner: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "domain": self.domain,
            "criticality": self.criticality,
            "source_of_truth": self.source_of_truth,
            "query_valid": self.query_valid,
            "observed": self.observed,
            "used_by_runtime": self.used_by_runtime,
            "used_by_dashboard": self.used_by_dashboard,
            "freshness_status": self.freshness_status,
            "semantic_owner": self.semantic_owner,
        }


@dataclass
class DatasourceContract:
    name: str = ""
    uid: str = ""
    type: str = ""
    url: str = ""
    accessible: bool = True
    default: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "uid": self.uid,
            "type": self.type,
            "url": self.url,
            "accessible": self.accessible,
            "default": self.default,
        }


@dataclass
class GrafanaAlignmentContract:
    total_dashboards: int = 0
    healthy_dashboards: int = 0
    broken_dashboards: int = 0
    legacy_dashboards: int = 0
    stale_dashboards: int = 0
    total_drifts: int = 0
    gpu_drifts: int = 0
    topology_drifts: int = 0
    inventory_drifts: int = 0
    semantic_drifts: int = 0
    runtime_mismatches: int = 0
    broken_panels: int = 0
    no_data_panels: int = 0
    datasource_valid: bool = True
    datasource_prometheus: bool = True
    datasource_loki: bool = True
    alignment_score: float = 0.0
    alignment_level: str = "unknown"
    contract_version: str = "OBS-31A.2"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "timestamp": self.timestamp,
            "total_dashboards": self.total_dashboards,
            "dashboards_healthy": self.healthy_dashboards,
            "dashboards_broken": self.broken_dashboards,
            "dashboards_legacy": self.legacy_dashboards,
            "dashboards_stale": self.stale_dashboards,
            "total_drifts": self.total_drifts,
            "gpu_drifts": self.gpu_drifts,
            "topology_drifts": self.topology_drifts,
            "inventory_drifts": self.inventory_drifts,
            "semantic_drifts": self.semantic_drifts,
            "runtime_mismatches": self.runtime_mismatches,
            "broken_panels": self.broken_panels,
            "no_data_panels": self.no_data_panels,
            "datasource_valid": self.datasource_valid,
            "datasource_prometheus": self.datasource_prometheus,
            "datasource_loki": self.datasource_loki,
            "alignment_score": round(self.alignment_score, 2),
            "alignment_level": self.alignment_level,
        }


def build_observability_source_contract(**overrides: Any) -> dict[str, Any]:
    contract = ObservabilitySourceContract(**{
        k: v for k, v in overrides.items()
        if hasattr(ObservabilitySourceContract, k)
    })
    return contract.to_dict()


def build_dashboard_contract(**overrides: Any) -> dict[str, Any]:
    contract = DashboardContract(**{
        k: v for k, v in overrides.items()
        if hasattr(DashboardContract, k)
    })
    return contract.to_dict()


def build_metric_contract(**overrides: Any) -> dict[str, Any]:
    contract = MetricContract(**{
        k: v for k, v in overrides.items()
        if hasattr(MetricContract, k)
    })
    return contract.to_dict()


def build_datasource_contract(**overrides: Any) -> dict[str, Any]:
    contract = DatasourceContract(**{
        k: v for k, v in overrides.items()
        if hasattr(DatasourceContract, k)
    })
    return contract.to_dict()


def build_grafana_alignment_contract(**overrides: Any) -> dict[str, Any]:
    contract = GrafanaAlignmentContract(**{
        k: v for k, v in overrides.items()
        if hasattr(GrafanaAlignmentContract, k)
    })
    return contract.to_dict()
