"""Reporting bounded context.

Keep __init__.py import-light. The reporting engine is a high fan-in module and
must not be imported implicitly via package re-exports.
"""

from __future__ import annotations

from runtime.reporting.contracts import (
    REPORTING_CONTRACT_VERSION,
    OperationalReportContract,
    OperationalSummaryContract,
    GovernanceReportContract,
    RuntimeHealthContract,
    DomainHealthContract,
    OperatorExplainabilityContract,
    ExecutiveSummaryContract,
    DegradationReportContract,
)

__all__ = [
    "REPORTING_CONTRACT_VERSION",
    "OperationalReportContract",
    "OperationalSummaryContract",
    "GovernanceReportContract",
    "RuntimeHealthContract",
    "DomainHealthContract",
    "OperatorExplainabilityContract",
    "ExecutiveSummaryContract",
    "DegradationReportContract",
    # Lazy re-exports.
    "build_operational_report",
    "build_runtime_health_report",
    "build_domain_health_report",
    "build_governance_summary",
    "build_executive_summary",
    "build_operator_summary",
    "build_degradation_report",
    "build_confidence_report",
    "build_explainability_summary",
    "build_reporting_score",
    "format_compact_report",
    "format_verbose_report",
]


_LAZY = {
    "build_operational_report": ("runtime.reporting.reporting_engine", "build_operational_report"),
    "build_runtime_health_report": ("runtime.reporting.reporting_engine", "build_runtime_health_report"),
    "build_domain_health_report": ("runtime.reporting.reporting_engine", "build_domain_health_report"),
    "build_governance_summary": ("runtime.reporting.reporting_engine", "build_governance_summary"),
    "build_executive_summary": ("runtime.reporting.reporting_engine", "build_executive_summary"),
    "build_operator_summary": ("runtime.reporting.reporting_engine", "build_operator_summary"),
    "build_degradation_report": ("runtime.reporting.reporting_engine", "build_degradation_report"),
    "build_confidence_report": ("runtime.reporting.reporting_engine", "build_confidence_report"),
    "build_explainability_summary": ("runtime.reporting.reporting_engine", "build_explainability_summary"),
    "build_reporting_score": ("runtime.reporting.reporting_engine", "build_reporting_score"),
    "format_compact_report": ("runtime.reporting.compact", "format_compact_report"),
    "format_verbose_report": ("runtime.reporting.verbose", "format_verbose_report"),
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
