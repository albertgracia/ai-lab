"""Validation bounded context.

This package must stay import-light.

Rule: avoid importing the full validation framework from __init__.py to prevent
cross-domain import cycles (reporting/performance/governance).
"""

from __future__ import annotations

from runtime.validation.contracts import (
    VALIDATION_CONTRACT_VERSION,
    RuntimeValidationContract,
    RuntimeInvariantContract,
    RuntimeSafetyGateContract,
    RuntimePilotReadinessContract,
    RuntimeFailureSurfaceContract,
    RuntimeRegressionContract,
)

__all__ = [
    "VALIDATION_CONTRACT_VERSION",
    "RuntimeValidationContract",
    "RuntimeInvariantContract",
    "RuntimeSafetyGateContract",
    "RuntimePilotReadinessContract",
    "RuntimeFailureSurfaceContract",
    "RuntimeRegressionContract",
    # Lazy re-exports for backward compatibility.
    "build_runtime_validation_report",
    "build_runtime_invariants",
    "build_runtime_safety_gates",
    "build_runtime_assertions",
    "build_runtime_regression_summary",
    "build_runtime_pilot_readiness",
    "build_runtime_failure_surface",
    "calculate_runtime_validation_score",
    "detect_runtime_validation_failures",
]


_LAZY = {
    "build_runtime_validation_report": ("runtime.validation.runtime_validation_framework", "build_runtime_validation_report"),
    "build_runtime_invariants": ("runtime.validation.runtime_validation_framework", "build_runtime_invariants"),
    "build_runtime_safety_gates": ("runtime.validation.runtime_validation_framework", "build_runtime_safety_gates"),
    "build_runtime_assertions": ("runtime.validation.runtime_validation_framework", "build_runtime_assertions"),
    "build_runtime_regression_summary": ("runtime.validation.runtime_validation_framework", "build_runtime_regression_summary"),
    "build_runtime_pilot_readiness": ("runtime.validation.runtime_validation_framework", "build_runtime_pilot_readiness"),
    "build_runtime_failure_surface": ("runtime.validation.runtime_validation_framework", "build_runtime_failure_surface"),
    "calculate_runtime_validation_score": ("runtime.validation.runtime_validation_framework", "calculate_runtime_validation_score"),
    "detect_runtime_validation_failures": ("runtime.validation.runtime_validation_framework", "detect_runtime_validation_failures"),
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
