"""FASE 29.4 — Runtime Degradation Manager.
FASE 30C — Integrates DegradedModeState for explicit observable state.

Implements adaptive degradation levels:

LEVEL 0 — NORMAL: full routing
LEVEL 1 — LIGHT: forced llama routing, qwen protection
LEVEL 2 — HEAVY: pause qwen routing, block cognitive (observable only)
LEVEL 3 — EMERGENCY: force llama-only (observable only, no auto-activation)

LEVEL 0 and LEVEL 1 are active in this phase.
LEVEL 2 and LEVEL 3 are observable AND metricated but NOT auto-activated.
"""

from __future__ import annotations

import logging
import threading
import time

from runtime.slo.metrics import (
    RUNTIME_DEGRADATION_LEVEL,
    RUNTIME_EMERGENCY_MODE_TOTAL,
    RUNTIME_QWEN_PROTECTION_TOTAL,
    RUNTIME_LLAMA_FASTPATH_FORCED_TOTAL,
)
from runtime.slo.degraded_state import DegradedModeState

logger = logging.getLogger("ai-lab.slo.degradation")

# Anti-flapping: minimum seconds between transitions
MIN_TRANSITION_INTERVAL = 30.0

# Cooldown before clearing degradation (seconds of continuous healthy state)
COOLDOWN_SECONDS = 30.0


class DegradationManager:
    """Manages runtime degradation levels and protection actions.

    Thread-safe. All actions are observable before enforcement.
    FASE 30C: exposes DegradedModeState with full transition metadata.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._current_level = 0
        self._last_transition = 0.0
        self._healthy_since: float | None = None
        self._state = DegradedModeState(
            level=0,
            reason="normal",
            source="startup",
            dry_run=True,
            healthy_since=0.0,
            cooldown_seconds=COOLDOWN_SECONDS,
        )

    def get_current_level(self) -> int:
        with self._lock:
            return self._current_level

    def get_degraded_state(self) -> DegradedModeState:
        with self._lock:
            return self._state

    def evaluate_and_apply(
        self,
        slo_state: int,
        slo_snapshot: dict,
        is_dry_run: bool,
    ) -> int:
        """Evaluate whether to change degradation level based on SLO state.

        Returns the resulting degradation level.
        """
        return self._evaluate(slo_state, slo_snapshot, is_dry_run)

    def _evaluate(
        self,
        slo_state: int,
        snap: dict,
        dry_run: bool,
    ) -> int:
        now = time.time()
        with self._lock:
            if now - self._last_transition < MIN_TRANSITION_INTERVAL:
                return self._current_level

            new_level = self._compute_target_level(slo_state, snap)
            prev = self._current_level

            if new_level == prev:
                self._healthy_since = now if new_level == 0 else None
                self._state.healthy_since = self._healthy_since or 0.0
                return prev

            if new_level > prev:
                self._last_transition = now
                self._current_level = new_level
                self._healthy_since = None
                self._log_transition(prev, new_level, snap, dry_run)
                self._sync_state_from_transition(prev, new_level, snap, dry_run)
                if not dry_run:
                    RUNTIME_DEGRADATION_LEVEL.set(new_level)
                return new_level

            if new_level < prev:
                if self._healthy_since is None:
                    self._healthy_since = now
                    self._state.healthy_since = now
                    return prev
                if now - self._healthy_since < COOLDOWN_SECONDS:
                    return prev
                self._last_transition = now
                self._current_level = new_level
                self._healthy_since = None
                self._log_transition(prev, new_level, snap, dry_run)
                self._sync_state_from_transition(prev, new_level, snap, dry_run)
                if not dry_run:
                    RUNTIME_DEGRADATION_LEVEL.set(new_level)
                return new_level

            return prev

    def _compute_target_level(self, slo_state: int, snap: dict) -> int:
        if slo_state >= 2:
            return 3
        if slo_state == 1:
            if snap.get("timeout_rate", 0) > 0.05:
                return 2
            if snap.get("vram_pressure", 0) > 0.97:
                return 2
            if snap.get("gpu_util", 0) > 0.92:
                return 1
            if snap.get("ttfb_p95", 0) > 10000:
                return 1
            return 1
        return 0

    def _log_transition(self, prev: int, new: int, snap: dict, dry_run: bool) -> None:
        tag = "[DRY-RUN]" if dry_run else "[ACTIVE]"
        logger.info(
            "%s Degradation transition: LEVEL %d → LEVEL %d  "
            "ttfb_p50=%.0f ttfb_p95=%.0f timeout_rate=%.3f gpu=%.2f vram=%.2f",
            tag,
            prev,
            new,
            snap.get("ttfb_p50", 0),
            snap.get("ttfb_p95", 0),
            snap.get("timeout_rate", 0),
            snap.get("gpu_util", 0),
            snap.get("vram_pressure", 0),
        )
        if new == 3 and not dry_run:
            RUNTIME_EMERGENCY_MODE_TOTAL.labels(
                reason=f"degradation_{prev}_to_{new}"
            ).inc()

    # ── Protection action helpers ─────────────────────────────

    def should_force_llama(self, level: int | None = None) -> bool:
        """DEPRECATED (ROUTER-HF-MODEL-POLICY-01): no longer forces model selection."""
        lvl = level if level is not None else self.get_current_level()
        if lvl >= 3:
            return True
        return False

    def should_block_qwen_escalation(self, level: int | None = None) -> bool:
        """If level >= 1, block unnecessary escalation to qwen (greetings)."""
        lvl = level if level is not None else self.get_current_level()
        return lvl >= 1

    def should_pause_qwen_routing(self, level: int | None = None) -> bool:
        """If level >= 2, completely pause qwen routing."""
        lvl = level if level is not None else self.get_current_level()
        return lvl >= 2

    def should_block_observe_report(self, level: int | None = None) -> bool:
        """If level >= 2, block observe/report/cognitive routes."""
        lvl = level if level is not None else self.get_current_level()
        return lvl >= 2

    def should_reject_long_prompts(self, level: int | None = None) -> bool:
        """If level == 3, reject prompts over 500 chars."""
        lvl = level if level is not None else self.get_current_level()
        return lvl >= 3

    def should_disable_embeddings(self, level: int | None = None) -> bool:
        """If level == 3, disable embeddings temporarily."""
        lvl = level if level is not None else self.get_current_level()
        return lvl >= 3

    def _sync_state_from_transition(
        self,
        prev_level: int,
        new_level: int,
        snap: dict,
        dry_run: bool,
    ) -> None:
        reason = self._transition_reason(new_level, snap)
        self._state.update_from_degradation(
            level=new_level,
            dry_run=dry_run,
            reason=reason,
            trigger_metric=self._detect_trigger_metric(snap, new_level),
            trigger_value=self._detect_trigger_value(snap, new_level),
            threshold=self._detect_threshold(snap, new_level),
            source="runtime_slo",
            healthy_since=self._healthy_since or 0.0,
            cooldown_seconds=COOLDOWN_SECONDS,
        )

    def _transition_reason(self, new_level: int, snap: dict) -> str:
        if new_level == 0:
            return "recovered"
        if new_level == 3:
            return f"slo_red_timeout_rate_{snap.get('timeout_rate', 0):.3f}"
        if new_level == 2:
            if snap.get("timeout_rate", 0) > 0.05:
                return f"timeout_rate_{snap.get('timeout_rate', 0):.3f}"
            if snap.get("vram_pressure", 0) > 0.97:
                return f"vram_pressure_{snap.get('vram_pressure', 0):.3f}"
            return "slo_yellow"
        if new_level == 1:
            if snap.get("gpu_util", 0) > 0.92:
                return f"gpu_pressure_{snap.get('gpu_util', 0):.3f}"
            if snap.get("ttfb_p95", 0) > 10000:
                return f"ttfb_high_{snap.get('ttfb_p95', 0):.0f}ms"
            return "slo_yellow"
        return "unknown"

    def _detect_trigger_metric(self, snap: dict, new_level: int) -> str:
        if new_level == 0:
            return ""
        if new_level >= 2:
            if snap.get("timeout_rate", 0) > 0.05:
                return "timeout_rate"
            if snap.get("vram_pressure", 0) > 0.97:
                return "vram_pressure"
        if new_level == 1:
            if snap.get("gpu_util", 0) > 0.92:
                return "gpu_util"
            if snap.get("ttfb_p95", 0) > 10000:
                return "ttfb_p95"
        return "slo_state"

    def _detect_trigger_value(self, snap: dict, new_level: int) -> float:
        metric = self._detect_trigger_metric(snap, new_level)
        return snap.get(metric, 0) if metric else 0.0

    def _detect_threshold(self, snap: dict, new_level: int) -> float:
        metric = self._detect_trigger_metric(snap, new_level)
        thresholds = {
            "timeout_rate": 0.05,
            "vram_pressure": 0.97,
            "gpu_util": 0.92,
            "ttfb_p95": 10000.0,
            "slo_state": 1.0,
        }
        return thresholds.get(metric, 0.0)

    def record_qwen_protection(self, reason: str, dry_run: bool) -> None:
        logger.info("Qwen protection triggered: %s  [dry_run=%s]", reason, dry_run)
        with self._lock:
            self._state.record_transition(
                prev_level=self._current_level,
                new_level=self._current_level,
                reason=f"qwen_protection:{reason}",
                source="runtime_slo",
            )
        if not dry_run:
            RUNTIME_QWEN_PROTECTION_TOTAL.labels(reason=reason).inc()

    def record_llama_forced(self, reason: str, dry_run: bool) -> None:
        logger.info("Llama forced: %s  [dry_run=%s]", reason, dry_run)
        with self._lock:
            self._state.record_transition(
                prev_level=self._current_level,
                new_level=self._current_level,
                reason=f"llama_forced:{reason}",
                source="runtime_slo",
            )
        if not dry_run:
            RUNTIME_LLAMA_FASTPATH_FORCED_TOTAL.labels(reason=reason).inc()

    def record_health_check(self, healthy: bool) -> None:
        with self._lock:
            self._state.record_health_check(healthy)
