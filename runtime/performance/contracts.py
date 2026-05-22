from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RuntimeLatencyContract:
    contract_version: str
    total_ms: float
    breakdown_ms: dict[str, float]
    generated_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "total_ms": float(self.total_ms),
            "breakdown_ms": {k: float(v) for k, v in (self.breakdown_ms or {}).items()},
            "generated_at": float(self.generated_at),
        }


@dataclass(frozen=True)
class GovernanceLatencyContract:
    contract_version: str
    governance_ms: float
    friction_detected: bool
    generated_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "governance_ms": float(self.governance_ms),
            "friction_detected": bool(self.friction_detected),
            "generated_at": float(self.generated_at),
        }


@dataclass(frozen=True)
class ValidationLatencyContract:
    contract_version: str
    validation_ms: float
    overhead_detected: bool
    generated_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "validation_ms": float(self.validation_ms),
            "overhead_detected": bool(self.overhead_detected),
            "generated_at": float(self.generated_at),
        }


@dataclass(frozen=True)
class OperationalFastPathContract:
    contract_version: str
    active: bool
    intent: str
    model: str
    used_cache: bool
    generated_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "active": bool(self.active),
            "intent": self.intent,
            "model": self.model,
            "used_cache": bool(self.used_cache),
            "generated_at": float(self.generated_at),
        }


@dataclass(frozen=True)
class AuthorityCacheContract:
    contract_version: str
    cache_entries: int
    cache_hits: int
    cache_misses: int
    freshness: str
    generated_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "cache_entries": int(self.cache_entries),
            "cache_hits": int(self.cache_hits),
            "cache_misses": int(self.cache_misses),
            "freshness": self.freshness,
            "generated_at": float(self.generated_at),
        }


@dataclass(frozen=True)
class VerbosityControlContract:
    contract_version: str
    level: str
    max_lines: int
    max_chars: int
    generated_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "level": self.level,
            "max_lines": int(self.max_lines),
            "max_chars": int(self.max_chars),
            "generated_at": float(self.generated_at),
        }
