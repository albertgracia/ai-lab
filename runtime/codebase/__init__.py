"""DEV-36X: Codebase Memory Integration.

Structural memory of the codebase via GitNexus.
NO OperationalTruth contamination. NO runtime state indexing.
"""

from runtime.codebase.contracts import CODEBASE_CONTRACT_VERSION
from runtime.codebase.gitnexus_memory import (
    load_codebase_memory,
    build_codebase_dependency_graph,
    build_codebase_module_topology,
    build_codebase_ownership,
    build_codebase_blast_radius_analysis,
    build_codebase_structural_risks,
    build_codebase_summary,
    build_codebase_score,
    get_codebase_memory_freshness,
    get_codebase_cache_state,
    reset_codebase_memory_cache,
)

__all__ = [
    "CODEBASE_CONTRACT_VERSION",
    "load_codebase_memory",
    "build_codebase_dependency_graph",
    "build_codebase_module_topology",
    "build_codebase_ownership",
    "build_codebase_blast_radius_analysis",
    "build_codebase_structural_risks",
    "build_codebase_summary",
    "build_codebase_score",
    "get_codebase_memory_freshness",
    "get_codebase_cache_state",
    "reset_codebase_memory_cache",
]
