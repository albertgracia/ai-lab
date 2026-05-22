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
from runtime.reporting.reporting_engine import (
    build_operational_report,
    build_runtime_health_report,
    build_domain_health_report,
    build_governance_summary,
    build_executive_summary,
    build_operator_summary,
    build_degradation_report,
    build_confidence_report,
    build_explainability_summary,
    build_reporting_score,
)
from runtime.reporting.compact import format_compact_report
from runtime.reporting.verbose import format_verbose_report

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
