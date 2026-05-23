"""Semantic bounded context.

Keep __init__.py import-light. Semantic sterilization may touch infrastructure
and should not be pulled in implicitly.
"""

from __future__ import annotations

from runtime.semantic.contracts import (
    SEMANTIC_CONTRACT_VERSION,
    SemanticIdentity,
    SemanticClassification,
    SemanticSterilizationResult,
    SemanticContamination,
    LegacyEntity,
    PhantomEntity,
    OperationalTruth,
    SemanticIntegrityReport,
    IdentityHygieneSummary,
)

__all__ = [
    "SEMANTIC_CONTRACT_VERSION",
    "SemanticIdentity",
    "SemanticClassification",
    "SemanticSterilizationResult",
    "SemanticContamination",
    "LegacyEntity",
    "PhantomEntity",
    "OperationalTruth",
    "SemanticIntegrityReport",
    "IdentityHygieneSummary",
    # Lazy re-exports.
    "build_operational_truth",
    "sterilize_semantic_entities",
    "classify_semantic_state",
    "detect_legacy_entities",
    "detect_phantom_entities",
    "detect_discoverable_contamination",
    "detect_inventory_leakage",
    "build_identity_hygiene_summary",
    "build_semantic_integrity_report",
    "calculate_semantic_integrity_score",
]


_LAZY = {
    "build_operational_truth": ("runtime.semantic.semantic_sterilization", "build_operational_truth"),
    "sterilize_semantic_entities": ("runtime.semantic.semantic_sterilization", "sterilize_semantic_entities"),
    "classify_semantic_state": ("runtime.semantic.semantic_sterilization", "classify_semantic_state"),
    "detect_legacy_entities": ("runtime.semantic.semantic_sterilization", "detect_legacy_entities"),
    "detect_phantom_entities": ("runtime.semantic.semantic_sterilization", "detect_phantom_entities"),
    "detect_discoverable_contamination": ("runtime.semantic.semantic_sterilization", "detect_discoverable_contamination"),
    "detect_inventory_leakage": ("runtime.semantic.semantic_sterilization", "detect_inventory_leakage"),
    "build_identity_hygiene_summary": ("runtime.semantic.semantic_sterilization", "build_identity_hygiene_summary"),
    "build_semantic_integrity_report": ("runtime.semantic.semantic_sterilization", "build_semantic_integrity_report"),
    "calculate_semantic_integrity_score": ("runtime.semantic.semantic_sterilization", "calculate_semantic_integrity_score"),
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
