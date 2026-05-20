"""FASE 29.4 — SLO Enforcement & Adaptive Runtime Protection.
FASE 30C — Single-Node Explicit Degraded Mode.

Modules:
  runtime_slo.py       — RuntimeSLOManager + SLOState (GREEN/YELLOW/RED)
  degradation.py       — DegradationManager (LEVEL 0-3) + DegradedModeState
  degraded_state.py    — DegradedModeState + TemporalTransition (FASE 30C)
  concurrency.py       — AdaptiveConcurrency (dynamic qwen/llama parallel)
  priority_lanes.py    — PrioritySlotManager (Lane 1 reserved slots)
  circuit_breakers.py  — ModelCircuitBreaker + CircuitBreakerRegistry (observable)
  metrics.py           — All FASE 29.4 and FASE 30C Prometheus metric definitions
"""

from runtime.slo.runtime_slo import RuntimeSLOManager, SLOState, is_slo_enabled, is_slo_dry_run
from runtime.slo.degradation import DegradationManager
from runtime.slo.degraded_state import DegradedModeState, TemporalTransition, build_disabled_degraded_state
from runtime.slo.concurrency import AdaptiveConcurrency
from runtime.slo.priority_lanes import PrioritySlotManager, get_lane_for_route
from runtime.slo.circuit_breakers import CircuitBreakerRegistry

__all__ = [
    "RuntimeSLOManager",
    "SLOState",
    "DegradationManager",
    "DegradedModeState",
    "TemporalTransition",
    "build_disabled_degraded_state",
    "AdaptiveConcurrency",
    "PrioritySlotManager",
    "CircuitBreakerRegistry",
    "is_slo_enabled",
    "is_slo_dry_run",
    "get_lane_for_route",
]
