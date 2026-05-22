"""FASE 35D: Operational fast-path engine.

Authority-first, deterministic, compact NOC-style summaries.
"""

from runtime.fastpath.contracts import FASTPATH_CONTRACT_VERSION
from runtime.fastpath.operational_fastpath import (
    classify_fastpath_intent,
    build_fastpath_response,
    build_fast_operational_summary,
    build_fast_observability_summary,
    build_fast_governance_summary,
    build_fast_validation_summary,
    build_fast_topology_summary,
    build_fast_infrastructure_summary,
    build_fast_gpu_summary,
    get_fastpath_cache_state,
    prime_fastpath_cache,
)

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
