"""Operator intent reasoning bounded context."""

from __future__ import annotations

__all__ = [
    "OPERATOR_INTENT_CONTRACT_VERSION",
    "OperatorIntentCategory",
    "analyze_operator_intent",
    "classify_operator_intent",
]


def __getattr__(name: str):
    if name in __all__:
        import importlib

        mod = importlib.import_module("runtime.operator_intent.operator_intent_reasoning")
        return getattr(mod, name)
    raise AttributeError(name)
