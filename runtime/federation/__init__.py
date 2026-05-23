"""Federation layer (bootstrap).

This package provides contracts and orchestration adapters for bounded-context
federation. It must not contain runtime behavior changes.
"""

from __future__ import annotations

__all__ = [
    "FEDERATION_CONTRACT_VERSION",
]

FEDERATION_CONTRACT_VERSION = "BOOTSTRAP-01"
