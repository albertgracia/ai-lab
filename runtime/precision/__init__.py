"""Precision bounded context.

Keep __init__.py import-light to avoid reporting cycles.
"""

from __future__ import annotations

__all__ = [
    "PRECISION_CONTRACT_VERSION",
    "build_runtime_precision_report",
    "build_precision_summary",
]


_LAZY = {
    "PRECISION_CONTRACT_VERSION": ("runtime.precision.runtime_precision_mode", "PRECISION_CONTRACT_VERSION"),
    "build_runtime_precision_report": ("runtime.precision.runtime_precision_mode", "build_runtime_precision_report"),
    "build_precision_summary": ("runtime.precision.runtime_precision_mode", "build_precision_summary"),
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
