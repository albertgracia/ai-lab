"""Infrastructure bounded context.

Keep __init__.py import-light to avoid pulling in authority/semantic chains.
"""

from __future__ import annotations

from runtime.infrastructure.contracts import (
    INFRASTRUCTURE_CONTRACT_VERSION,
    InfrastructureIdentity,
    AuthorityRoot,
    OperationalNode,
    InfrastructureRole,
    InfrastructureDependency,
    InfrastructureAuthorityMap,
    InfrastructureInventory,
    InfrastructureSemanticSummary,
)

__all__ = [
    "INFRASTRUCTURE_CONTRACT_VERSION",
    "INFRASTRUCTURE_REGISTRY_VERSION",
    "InfrastructureIdentity",
    "AuthorityRoot",
    "OperationalNode",
    "InfrastructureRole",
    "InfrastructureDependency",
    "InfrastructureAuthorityMap",
    "InfrastructureInventory",
    "InfrastructureSemanticSummary",
    # Lazy re-exports.
    "build_infrastructure_identity_registry",
    "build_authority_root_map",
    "build_operational_node_map",
    "build_infrastructure_semantic_summary",
    "identify_infrastructure",
    "classify_infrastructure_role",
    "classify_operational_state",
    "detect_authority_dependencies",
    "detect_control_plane_nodes",
    "calculate_infrastructure_identity_score",
]


_LAZY = {
    "INFRASTRUCTURE_REGISTRY_VERSION": ("runtime.infrastructure.infrastructure_identity_registry", "INFRASTRUCTURE_REGISTRY_VERSION"),
    "build_infrastructure_identity_registry": ("runtime.infrastructure.infrastructure_identity_registry", "build_infrastructure_identity_registry"),
    "build_authority_root_map": ("runtime.infrastructure.infrastructure_identity_registry", "build_authority_root_map"),
    "build_operational_node_map": ("runtime.infrastructure.infrastructure_identity_registry", "build_operational_node_map"),
    "build_infrastructure_semantic_summary": ("runtime.infrastructure.infrastructure_identity_registry", "build_infrastructure_semantic_summary"),
    "identify_infrastructure": ("runtime.infrastructure.infrastructure_identity_registry", "identify_infrastructure"),
    "classify_infrastructure_role": ("runtime.infrastructure.infrastructure_identity_registry", "classify_infrastructure_role"),
    "classify_operational_state": ("runtime.infrastructure.infrastructure_identity_registry", "classify_operational_state"),
    "detect_authority_dependencies": ("runtime.infrastructure.infrastructure_identity_registry", "detect_authority_dependencies"),
    "detect_control_plane_nodes": ("runtime.infrastructure.infrastructure_identity_registry", "detect_control_plane_nodes"),
    "calculate_infrastructure_identity_score": ("runtime.infrastructure.infrastructure_identity_registry", "calculate_infrastructure_identity_score"),
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
