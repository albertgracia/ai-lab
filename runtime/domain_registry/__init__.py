"""Domain registry (governance metadata).

Defines official bounded contexts and allowed dependencies.
"""

from __future__ import annotations

__all__ = [
    "DOMAIN_REGISTRY_VERSION",
    "DomainSpec",
    "DOMAIN_SPECS",
    "get_domain_spec",
    "validate_dependency",
]

from runtime.domain_registry.domain_registry import (  # noqa: E402
    DOMAIN_REGISTRY_VERSION,
    DomainSpec,
    DOMAIN_SPECS,
    get_domain_spec,
    validate_dependency,
)
