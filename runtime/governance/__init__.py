"""Governance bounded context.

Keep __init__.py import-light to avoid performance/reporting cycles.
"""

from __future__ import annotations

from runtime.governance.contracts import (
    GOVERNANCE_CONTRACT_VERSION,
    GovernanceRegistryContract,
    GovernanceDomainContract,
    GovernanceAuthorityContract,
    GovernanceConfidenceContract,
    GovernanceRiskContract,
    GovernanceRemediationContract,
    GovernanceHealthContract,
    GovernanceContractRegistry,
)

__all__ = [
    "GOVERNANCE_CONTRACT_VERSION",
    "GovernanceRegistryContract",
    "GovernanceDomainContract",
    "GovernanceAuthorityContract",
    "GovernanceConfidenceContract",
    "GovernanceRiskContract",
    "GovernanceRemediationContract",
    "GovernanceHealthContract",
    "GovernanceContractRegistry",
    # Lazy re-exports.
    "build_runtime_governance_registry",
    "build_governance_domains",
    "build_governance_authority_map",
    "build_governance_confidence_map",
    "build_governance_contract_registry",
    "build_governance_health_summary",
    "build_governance_risk_summary",
    "build_governance_remediation_summary",
    "calculate_governance_score",
    "detect_governance_drift",
]


_LAZY = {
    "build_runtime_governance_registry": ("runtime.governance.runtime_governance_registry", "build_runtime_governance_registry"),
    "build_governance_domains": ("runtime.governance.runtime_governance_registry", "build_governance_domains"),
    "build_governance_authority_map": ("runtime.governance.runtime_governance_registry", "build_governance_authority_map"),
    "build_governance_confidence_map": ("runtime.governance.runtime_governance_registry", "build_governance_confidence_map"),
    "build_governance_contract_registry": ("runtime.governance.runtime_governance_registry", "build_governance_contract_registry"),
    "build_governance_health_summary": ("runtime.governance.runtime_governance_registry", "build_governance_health_summary"),
    "build_governance_risk_summary": ("runtime.governance.runtime_governance_registry", "build_governance_risk_summary"),
    "build_governance_remediation_summary": ("runtime.governance.runtime_governance_registry", "build_governance_remediation_summary"),
    "calculate_governance_score": ("runtime.governance.runtime_governance_registry", "calculate_governance_score"),
    "detect_governance_drift": ("runtime.governance.runtime_governance_registry", "detect_governance_drift"),
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
