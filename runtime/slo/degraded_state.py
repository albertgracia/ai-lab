"""FASE 30C — Single-Node Explicit Degraded Mode.

Exposes the DegradationManager's internal state as a serializable,
observable DegradedModeState object with full metadata for NOC/ops.

RULE-30C-1: level=0 means NOT degraded.
RULE-30C-2: each transition creates a TemporalTransition.
RULE-30C-3: health checks deque stores last 20 booleans.
RULE-30C-4: to_dict() is JSON-safe.
RULE-30C-5: duration_seconds is real-time calculated.
RULE-30C-6: endpoint lives in openai_gateway.py (not router).
RULE-30C-7: /runtime/degraded-state always 200; if disabled, return reason.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TemporalTransition:
    timestamp: float = 0.0
    previous_level: int = 0
    current_level: int = 0
    reason: str = ""
    source: str = "runtime_slo"

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "previous_level": self.previous_level,
            "current_level": self.current_level,
            "reason": self.reason,
            "source": self.source,
        }


@dataclass
class DegradedModeState:
    level: int = 0
    reason: str = ""
    trigger_metric: str = ""
    trigger_value: float = 0.0
    threshold: float = 0.0
    phase: str = "30C"
    dry_run: bool = True
    source: str = "startup"
    started_at: float = 0.0
    healthy_since: float = 0.0
    cooldown_seconds: float = 30.0

    previous_level: int = 0
    transition_count: int = 0

    transitions: list[TemporalTransition] = field(default_factory=list)
    health_checks: deque[bool] = field(default_factory=lambda: deque(maxlen=20))

    @property
    def is_degraded(self) -> bool:
        return self.level > 0

    @property
    def duration_seconds(self) -> float:
        if self.started_at == 0.0 or self.level == 0:
            return 0.0
        return time.time() - self.started_at

    @property
    def cooldown_remaining(self) -> float:
        if self.level > 0:
            return 0.0
        if self.healthy_since == 0.0:
            return 0.0
        elapsed = time.time() - self.healthy_since
        remaining = self.cooldown_seconds - elapsed
        return max(0.0, remaining)

    def record_health_check(self, healthy: bool) -> None:
        self.health_checks.append(healthy)

    def record_transition(
        self,
        prev_level: int,
        new_level: int,
        reason: str,
        source: str = "runtime_slo",
    ) -> None:
        self.previous_level = prev_level
        self.level = new_level
        self.reason = reason
        self.source = source
        self.transition_count += 1
        if new_level > 0 and self.started_at == 0.0:
            self.started_at = time.time()
        if new_level == 0:
            self.started_at = 0.0
            self.trigger_metric = ""
            self.trigger_value = 0.0
            self.threshold = 0.0
        self.transitions.append(
            TemporalTransition(
                timestamp=time.time(),
                previous_level=prev_level,
                current_level=new_level,
                reason=reason,
                source=source,
            )
        )

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "is_degraded": self.is_degraded,
            "reason": self.reason,
            "source": self.source,
            "trigger_metric": self.trigger_metric,
            "trigger_value": self.trigger_value,
            "threshold": self.threshold,
            "phase": self.phase,
            "dry_run": self.dry_run,
            "started_at": self.started_at,
            "duration_seconds": self.duration_seconds,
            "cooldown_remaining": self.cooldown_remaining,
            "healthy_since": self.healthy_since,
            "cooldown_seconds": self.cooldown_seconds,
            "previous_level": self.previous_level,
            "transition_count": self.transition_count,
            "transitions": [t.to_dict() for t in self.transitions],
            "health_checks": list(self.health_checks),
        }

    def update_from_degradation(
        self,
        level: int,
        dry_run: bool,
        reason: str = "",
        trigger_metric: str = "",
        trigger_value: float = 0.0,
        threshold: float = 0.0,
        source: str = "runtime_slo",
        healthy_since: float = 0.0,
        cooldown_seconds: float = 30.0,
    ) -> None:
        prev = self.level
        self.level = level
        self.dry_run = dry_run
        self.source = source
        self.healthy_since = healthy_since
        self.cooldown_seconds = cooldown_seconds

        if level != prev:
            self.previous_level = prev
            self.transition_count += 1
            self.reason = reason
            if level > 0:
                self.trigger_metric = trigger_metric
                self.trigger_value = trigger_value
                self.threshold = threshold
                if self.started_at == 0.0:
                    self.started_at = time.time()
            else:
                self.started_at = 0.0
                self.trigger_metric = ""
                self.trigger_value = 0.0
                self.threshold = 0.0
            self.transitions.append(
                TemporalTransition(
                    timestamp=time.time(),
                    previous_level=prev,
                    current_level=level,
                    reason=reason,
                    source=source,
                )
            )


def build_disabled_degraded_state() -> DegradedModeState:
    state = DegradedModeState(
        level=0,
        reason="slo_enforcement_disabled",
        source="startup",
        dry_run=True,
    )
    return state
