"""Adaptive Weights — live dynamic capability weights.

Maintains a mutable copy of TASK_MODEL_SCORING weights that can be
adjusted by the autonomous optimiser (runtime_optimizer.py) based on
historical performance.

Bounds protect against runaway drift:
  MIN_WEIGHT = 0.1   MAX_WEIGHT = 2.0
"""

import copy
from threading import Lock

MIN_WEIGHT = 0.1
MAX_WEIGHT = 2.0

_lock = Lock()

# ── seed from the static registry (if available) ──────────────────────
try:
    from runtime.models.model_registry import TASK_MODEL_SCORING
    _seed = copy.deepcopy(TASK_MODEL_SCORING)
except ImportError:
    _seed = {
        "coding":    {"coding": 1.0, "reasoning": 0.5, "speed": 0.3, "memory": 0.2},
        "reasoning":{"reasoning": 1.0, "coding": 0.4, "speed": 0.1, "memory": 0.3},
        "fast":      {"speed": 1.0, "coding": 0.4, "reasoning": 0.2, "memory": 0.1},
        "general":   {"coding": 0.5, "reasoning": 0.5, "speed": 0.5, "memory": 0.3},
    }

LIVE_TASK_WEIGHTS = copy.deepcopy(_seed)


def get_weights(task_type: str) -> dict[str, float]:
    with _lock:
        return copy.deepcopy(LIVE_TASK_WEIGHTS.get(task_type, {"speed": 1.0}))


def adjust_weight(task_type: str, metric: str, delta: float):
    with _lock:
        weights = LIVE_TASK_WEIGHTS.setdefault(task_type, copy.deepcopy(_seed.get(task_type, {"speed": 1.0})))
        current = weights.get(metric, 0.0)
        new_val = current + delta
        new_val = max(MIN_WEIGHT, min(MAX_WEIGHT, new_val))
        weights[metric] = round(new_val, 4)


def reset_weights():
    global LIVE_TASK_WEIGHTS
    with _lock:
        LIVE_TASK_WEIGHTS = copy.deepcopy(_seed)


def snapshot() -> dict:
    with _lock:
        return copy.deepcopy(LIVE_TASK_WEIGHTS)
