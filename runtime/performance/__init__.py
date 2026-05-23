"""Performance bounded context.

Keep __init__.py import-light to avoid validation/reporting/governance cycles.
"""

from __future__ import annotations

from runtime.performance.contracts import (
    RuntimeLatencyContract,
    GovernanceLatencyContract,
    ValidationLatencyContract,
    OperationalFastPathContract,
    AuthorityCacheContract,
    VerbosityControlContract,
)

__all__ = [
    "PERFORMANCE_CONTRACT_VERSION",
    "RuntimeLatencyContract",
    "GovernanceLatencyContract",
    "ValidationLatencyContract",
    "OperationalFastPathContract",
    "AuthorityCacheContract",
    "VerbosityControlContract",
    "profile_runtime_latency",
    "profile_governance_latency",
    "profile_validation_latency",
    "profile_reporting_latency",
    "profile_observability_latency",
    "profile_grounding_latency",
    "build_latency_breakdown",
    "calculate_runtime_performance_score",
    "detect_governance_friction",
    "detect_validation_overhead",
    "compress_operational_noise",
    "build_fast_operational_summary",
    "get_performance_cache_state",
    "prime_async_diagnostics",
]


_LAZY = {
    "PERFORMANCE_CONTRACT_VERSION": ("runtime.performance.runtime_latency_calibration", "PERFORMANCE_CONTRACT_VERSION"),
    "profile_runtime_latency": ("runtime.performance.runtime_latency_calibration", "profile_runtime_latency"),
    "profile_governance_latency": ("runtime.performance.runtime_latency_calibration", "profile_governance_latency"),
    "profile_validation_latency": ("runtime.performance.runtime_latency_calibration", "profile_validation_latency"),
    "profile_reporting_latency": ("runtime.performance.runtime_latency_calibration", "profile_reporting_latency"),
    "profile_observability_latency": ("runtime.performance.runtime_latency_calibration", "profile_observability_latency"),
    "profile_grounding_latency": ("runtime.performance.runtime_latency_calibration", "profile_grounding_latency"),
    "build_latency_breakdown": ("runtime.performance.runtime_latency_calibration", "build_latency_breakdown"),
    "calculate_runtime_performance_score": ("runtime.performance.runtime_latency_calibration", "calculate_runtime_performance_score"),
    "detect_governance_friction": ("runtime.performance.runtime_latency_calibration", "detect_governance_friction"),
    "detect_validation_overhead": ("runtime.performance.runtime_latency_calibration", "detect_validation_overhead"),
    "compress_operational_noise": ("runtime.performance.runtime_latency_calibration", "compress_operational_noise"),
    "build_fast_operational_summary": ("runtime.performance.runtime_latency_calibration", "build_fast_operational_summary"),
    "get_performance_cache_state": ("runtime.performance.runtime_latency_calibration", "get_performance_cache_state"),
    "prime_async_diagnostics": ("runtime.performance.runtime_latency_calibration", "prime_async_diagnostics"),
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
