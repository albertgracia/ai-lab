"""Model bounded context."""

from __future__ import annotations

__all__ = [
    "build_operational_model_truth",
    "get_operational_model_ids",
    "is_model_operational",
]


def __getattr__(name: str):
    if name in __all__:
        import importlib

        mod = importlib.import_module("runtime.models.operational_truth")
        return getattr(mod, name)
    raise AttributeError(name)
