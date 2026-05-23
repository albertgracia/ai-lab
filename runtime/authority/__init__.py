"""Authority bounded context.

Keep __init__.py import-light to avoid pulling in semantic/infrastructure at
import time.
"""

from __future__ import annotations

from runtime.authority.contracts import (
    AUTHORITY_CONTRACT_VERSION,
    AuthoritySnapshot,
    AuthorityEvidence,
    AuthorityQuery,
    AuthorityResponse,
    AuthorityFreshness,
    AuthorityBackedCognition,
    AuthorityCacheEntry,
    AuthorityValidationResult,
    AuthorityCognitionSummary,
)

__all__ = [
    "AUTHORITY_CONTRACT_VERSION",
    "AuthoritySnapshot",
    "AuthorityEvidence",
    "AuthorityQuery",
    "AuthorityResponse",
    "AuthorityFreshness",
    "AuthorityBackedCognition",
    "AuthorityCacheEntry",
    "AuthorityValidationResult",
    "AuthorityCognitionSummary",
    # Lazy re-exports.
    "build_live_authority_snapshot",
    "query_prometheus_authority",
    "query_runtime_authority",
    "query_operational_truth",
    "query_infrastructure_identity",
    "build_authority_backed_context",
    "build_authority_evidence",
    "calculate_authority_freshness",
    "detect_stale_authority",
    "detect_authority_gaps",
    "get_authority_cache_state",
    "prime_authority_cache",
    "build_authority_cognition_summary",
]


_LAZY = {
    "build_live_authority_snapshot": ("runtime.authority.live_authority_cognition", "build_live_authority_snapshot"),
    "query_prometheus_authority": ("runtime.authority.live_authority_cognition", "query_prometheus_authority"),
    "query_runtime_authority": ("runtime.authority.live_authority_cognition", "query_runtime_authority"),
    "query_operational_truth": ("runtime.authority.live_authority_cognition", "query_operational_truth"),
    "query_infrastructure_identity": ("runtime.authority.live_authority_cognition", "query_infrastructure_identity"),
    "build_authority_backed_context": ("runtime.authority.live_authority_cognition", "build_authority_backed_context"),
    "build_authority_evidence": ("runtime.authority.live_authority_cognition", "build_authority_evidence"),
    "calculate_authority_freshness": ("runtime.authority.live_authority_cognition", "calculate_authority_freshness"),
    "detect_stale_authority": ("runtime.authority.live_authority_cognition", "detect_stale_authority"),
    "detect_authority_gaps": ("runtime.authority.live_authority_cognition", "detect_authority_gaps"),
    "get_authority_cache_state": ("runtime.authority.live_authority_cognition", "get_authority_cache_state"),
    "prime_authority_cache": ("runtime.authority.live_authority_cognition", "prime_authority_cache"),
    "build_authority_cognition_summary": ("runtime.authority.live_authority_cognition", "build_authority_cognition_summary"),
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
