"""FEDERATION-CONTEXT-BUDGETS-01: deterministic context budget enforcement.

Goal: prevent cross-domain context explosion via small, explicit, contracts-first budgets.

Hard rules:
- Deterministic, no heuristics, no LLM.
- Metadata-first (no operational truth mutation).
- No orchestration, no recursion/loops.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable


class ContextOverflowPolicy(str, Enum):
    REJECT = "reject"
    TRUNCATE = "truncate"


@dataclass(frozen=True)
class ContextBudget:
    max_chars: int
    max_items: int
    overflow_policy: ContextOverflowPolicy = ContextOverflowPolicy.TRUNCATE


@dataclass(frozen=True)
class DomainContextLimits:
    """Domain-scoped context limits.

    Keep these small by design. These are not token budgets; they are deterministic
    limits for payload size and list-like fanout.
    """

    authority: ContextBudget
    observability: ContextBudget
    semantic: ContextBudget
    memory: ContextBudget
    gateway: ContextBudget
    tests: ContextBudget
    incidents: ContextBudget
    infrastructure: ContextBudget
    docs: ContextBudget
    operator_intent: ContextBudget

    def for_domain(self, domain: str) -> ContextBudget:
        d = (domain or "").strip().lower()
        if not d:
            return self.gateway
        if hasattr(self, d):
            return getattr(self, d)
        return self.gateway


@dataclass(frozen=True)
class BudgetConsumption:
    chars: int
    items: int

    def remaining(self, budget: ContextBudget) -> dict[str, int]:
        return {
            "chars": max(0, int(budget.max_chars) - int(self.chars)),
            "items": max(0, int(budget.max_items) - int(self.items)),
        }

    def overflow(self, budget: ContextBudget) -> dict[str, int]:
        return {
            "chars": max(0, int(self.chars) - int(budget.max_chars)),
            "items": max(0, int(self.items) - int(budget.max_items)),
        }


@dataclass(frozen=True)
class ContextEnvelope:
    """Context payload + enforcement metadata.

    payload is expected to be a small, JSON-serializable dict.
    """

    domain: str
    payload: dict[str, Any]
    budget: ContextBudget
    consumed: BudgetConsumption
    remaining: dict[str, int]
    overflow: dict[str, int]
    truncated: bool
    rejected: bool
    degraded: bool
    truncated_keys: list[str]

    def to_metadata(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "budget": {
                "max_chars": int(self.budget.max_chars),
                "max_items": int(self.budget.max_items),
                "overflow_policy": self.budget.overflow_policy.value,
            },
            "consumed": {"chars": int(self.consumed.chars), "items": int(self.consumed.items)},
            "remaining": dict(self.remaining),
            "overflow": dict(self.overflow),
            "truncated": bool(self.truncated),
            "rejected": bool(self.rejected),
            "degraded": bool(self.degraded),
            "truncated_keys": list(self.truncated_keys or []),
        }


def default_domain_limits() -> DomainContextLimits:
    """Small, explicit budgets.

    These are designed to cap context fanout and payload flooding.
    """

    return DomainContextLimits(
        authority=ContextBudget(max_chars=700, max_items=8, overflow_policy=ContextOverflowPolicy.REJECT),
        observability=ContextBudget(max_chars=1200, max_items=14, overflow_policy=ContextOverflowPolicy.TRUNCATE),
        semantic=ContextBudget(max_chars=900, max_items=10, overflow_policy=ContextOverflowPolicy.TRUNCATE),
        memory=ContextBudget(max_chars=800, max_items=6, overflow_policy=ContextOverflowPolicy.TRUNCATE),
        gateway=ContextBudget(max_chars=900, max_items=10, overflow_policy=ContextOverflowPolicy.TRUNCATE),
        tests=ContextBudget(max_chars=800, max_items=10, overflow_policy=ContextOverflowPolicy.TRUNCATE),
        incidents=ContextBudget(max_chars=1100, max_items=12, overflow_policy=ContextOverflowPolicy.TRUNCATE),
        infrastructure=ContextBudget(max_chars=900, max_items=10, overflow_policy=ContextOverflowPolicy.TRUNCATE),
        docs=ContextBudget(max_chars=700, max_items=10, overflow_policy=ContextOverflowPolicy.TRUNCATE),
        operator_intent=ContextBudget(max_chars=700, max_items=10, overflow_policy=ContextOverflowPolicy.TRUNCATE),
    )


def compute_budget_consumption(payload: Any) -> BudgetConsumption:
    """Deterministically estimate payload size.

    - chars: sum of string lengths for str values and keys.
    - items: count of list elements (flat) and dict keys.

    This is a strict, deterministic approximation to cap growth; it does not
    attempt semantic meaning.
    """

    chars = 0
    items = 0

    def _walk(obj: Any) -> None:
        nonlocal chars, items
        if obj is None:
            return
        if isinstance(obj, str):
            chars += len(obj)
            items += 1
            return
        if isinstance(obj, (int, float, bool)):
            items += 1
            return
        if isinstance(obj, dict):
            items += len(obj)
            for k, v in obj.items():
                if isinstance(k, str):
                    chars += len(k)
                else:
                    items += 1
                _walk(v)
            return
        if isinstance(obj, (list, tuple)):
            items += len(obj)
            for it in obj:
                _walk(it)
            return
        # Unknown objects: treat as 1 item.
        items += 1

    _walk(payload)
    return BudgetConsumption(chars=int(chars), items=int(items))


def validate_context_budget(*, domain: str, payload: dict[str, Any], limits: DomainContextLimits) -> tuple[bool, str, ContextBudget, BudgetConsumption]:
    budget = limits.for_domain(domain)
    consumed = compute_budget_consumption(payload)
    if consumed.chars > budget.max_chars or consumed.items > budget.max_items:
        if budget.overflow_policy == ContextOverflowPolicy.REJECT:
            return False, "overflow_rejected", budget, consumed
        return True, "overflow_truncate", budget, consumed
    return True, "ok", budget, consumed


def _truncate_string(s: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(s) <= max_chars:
        return s
    # Deterministic suffix marker.
    if max_chars <= 12:
        return s[:max_chars]
    return s[: max_chars - 12] + "...[truncated]"


def _truncate_list(xs: list[Any], max_items: int) -> list[Any]:
    if max_items <= 0:
        return []
    if len(xs) <= max_items:
        return xs
    return xs[:max_items]


def truncate_context_payload(*, payload: dict[str, Any], budget: ContextBudget) -> tuple[dict[str, Any], list[str]]:
    """Truncate payload deterministically.

    Strategy:
    - For list-like values: slice to max_items.
    - For str values: clamp length.
    - Do not recurse deeply; keep it cheap and predictable.
    """

    truncated_keys: list[str] = []
    out: dict[str, Any] = {}
    for k in sorted(payload.keys()):
        v = payload.get(k)
        if isinstance(v, str):
            nv = _truncate_string(v, budget.max_chars)
            if nv != v:
                truncated_keys.append(k)
            out[k] = nv
            continue
        if isinstance(v, list):
            nv = _truncate_list(v, budget.max_items)
            if nv is not v and len(nv) != len(v):
                truncated_keys.append(k)
            out[k] = nv
            continue
        if isinstance(v, dict):
            # Keep only first N keys deterministically.
            keys = sorted(v.keys())
            if len(keys) > budget.max_items:
                truncated_keys.append(k)
            out[k] = {kk: v[kk] for kk in keys[: budget.max_items]}
            continue
        out[k] = v
    return out, truncated_keys


def enforce_context_budget(*, domain: str, payload: dict[str, Any], limits: DomainContextLimits | None = None) -> ContextEnvelope:
    """Enforce budgets and return an envelope with metadata."""

    limits = limits or default_domain_limits()
    ok, status, budget, consumed = validate_context_budget(domain=domain, payload=payload, limits=limits)
    remaining = consumed.remaining(budget)
    overflow = consumed.overflow(budget)

    if ok and status == "ok":
        return ContextEnvelope(
            domain=domain,
            payload=payload,
            budget=budget,
            consumed=consumed,
            remaining=remaining,
            overflow=overflow,
            truncated=False,
            rejected=False,
            degraded=False,
            truncated_keys=[],
        )

    if not ok and budget.overflow_policy == ContextOverflowPolicy.REJECT:
        # Reject but still return deterministic metadata.
        return ContextEnvelope(
            domain=domain,
            payload={},
            budget=budget,
            consumed=consumed,
            remaining=remaining,
            overflow=overflow,
            truncated=False,
            rejected=True,
            degraded=True,
            truncated_keys=[],
        )

    # Truncate.
    truncated_payload, truncated_keys = truncate_context_payload(payload=payload, budget=budget)
    truncated_consumed = compute_budget_consumption(truncated_payload)
    return ContextEnvelope(
        domain=domain,
        payload=truncated_payload,
        budget=budget,
        consumed=truncated_consumed,
        remaining=truncated_consumed.remaining(budget),
        overflow=truncated_consumed.overflow(budget),
        truncated=True,
        rejected=False,
        degraded=True,
        truncated_keys=truncated_keys,
    )


def build_federation_budget_metadata(*, envelopes: Iterable[ContextEnvelope]) -> dict[str, Any]:
    """Aggregate per-domain envelope metadata for federation traceability."""

    envs = list(envelopes)
    truncated_domains = sorted({e.domain for e in envs if e.truncated or e.rejected})
    return {
        "_budget_consumed": {e.domain: e.to_metadata()["consumed"] for e in envs},
        "_budget_remaining": {e.domain: e.to_metadata()["remaining"] for e in envs},
        "_budget_overflow": {e.domain: e.to_metadata()["overflow"] for e in envs},
        "_truncated_domains": truncated_domains,
    }
