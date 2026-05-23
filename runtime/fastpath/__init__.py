"""FASE 35D: Operational fast-path engine.

Authority-first, deterministic, compact NOC-style summaries.

Keep __init__.py import-light to avoid importing downstream domains at import time.
"""

from __future__ import annotations

from runtime.fastpath.contracts import FASTPATH_CONTRACT_VERSION

__all__ = [
    "FASTPATH_CONTRACT_VERSION",
    "classify_fastpath_intent",
    "build_fastpath_response",
    "build_fast_operational_summary",
    "build_fast_observability_summary",
    "build_fast_governance_summary",
    "build_fast_validation_summary",
    "build_fast_topology_summary",
    "build_fast_infrastructure_summary",
    "build_fast_gpu_summary",
    "get_fastpath_cache_state",
    "prime_fastpath_cache",
]


_LAZY = {
    "classify_fastpath_intent": ("runtime.fastpath.operational_fastpath", "classify_fastpath_intent"),
    "build_fastpath_response": ("runtime.fastpath.operational_fastpath", "build_fastpath_response"),
    "build_fast_operational_summary": ("runtime.fastpath.operational_fastpath", "build_fast_operational_summary"),
    "build_fast_observability_summary": ("runtime.fastpath.operational_fastpath", "build_fast_observability_summary"),
    "build_fast_governance_summary": ("runtime.fastpath.operational_fastpath", "build_fast_governance_summary"),
    "build_fast_validation_summary": ("runtime.fastpath.operational_fastpath", "build_fast_validation_summary"),
    "build_fast_topology_summary": ("runtime.fastpath.operational_fastpath", "build_fast_topology_summary"),
    "build_fast_infrastructure_summary": ("runtime.fastpath.operational_fastpath", "build_fast_infrastructure_summary"),
    "build_fast_gpu_summary": ("runtime.fastpath.operational_fastpath", "build_fast_gpu_summary"),
    "get_fastpath_cache_state": ("runtime.fastpath.operational_fastpath", "get_fastpath_cache_state"),
    "prime_fastpath_cache": ("runtime.fastpath.operational_fastpath", "prime_fastpath_cache"),
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
