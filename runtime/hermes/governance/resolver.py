import json
import os
import time

from dataclasses import dataclass, field
from typing import Optional


GOVERNANCE_DIR = os.path.dirname(os.path.abspath(__file__))


@dataclass
class TriggerSignals:
    slo_state: str = "GREEN"
    degradation_level: str = "NONE"
    emergency_mode: bool = False
    vram_pressure: float = 0.0
    gpu_pressure: float = 0.0
    timeout_rate: float = 0.0

    def to_dict(self) -> dict:
        return {
            "slo_state": self.slo_state,
            "degradation_level": self.degradation_level,
            "emergency_mode": self.emergency_mode,
            "vram_pressure": self.vram_pressure,
            "gpu_pressure": self.gpu_pressure,
            "timeout_rate": self.timeout_rate,
        }


@dataclass
class CapabilityGovernanceEntry:
    capability_id: str
    status: str  # "allowed" | "requires_approval" | "blocked"

    def to_dict(self) -> dict:
        return {"capability_id": self.capability_id, "status": self.status}


@dataclass
class GovernanceState:
    mode: str
    source: str  # "control_plane" | "fallback"
    resolved_at: float
    trigger_signals: TriggerSignals
    capabilities: dict[str, str] = field(default_factory=dict)
    previous_mode: Optional[str] = None
    transition_count: int = 0

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "source": self.source,
            "resolved_at": self.resolved_at,
            "trigger_signals": self.trigger_signals.to_dict(),
            "capabilities": dict(self.capabilities),
            "previous_mode": self.previous_mode,
            "transition_count": self.transition_count,
        }


@dataclass
class GovernanceMode:
    name: str
    description: str
    allows: list[str]
    blocks: list[str]
    default_capability_behavior: str
    requires_approval: list[str]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "allows": list(self.allows),
            "blocks": list(self.blocks),
            "default_capability_behavior": self.default_capability_behavior,
            "requires_approval": list(self.requires_approval),
        }


TRANSITION_RULES: dict[tuple[str, str], dict] = {
    ("NORMAL", "ELEVATED"):    {"allowed": True, "stabilization": 0},
    ("NORMAL", "DEGRADED"):    {"allowed": True, "stabilization": 0},
    ("NORMAL", "LOCKDOWN"):    {"allowed": True, "stabilization": 0},
    ("ELEVATED", "NORMAL"):    {"allowed": True, "stabilization": 60},
    ("ELEVATED", "DEGRADED"):  {"allowed": True, "stabilization": 0},
    ("ELEVATED", "LOCKDOWN"):  {"allowed": True, "stabilization": 0},
    ("DEGRADED", "NORMAL"):    {"allowed": True, "stabilization": 120},
    ("DEGRADED", "ELEVATED"):  {"allowed": True, "stabilization": 0},
    ("DEGRADED", "LOCKDOWN"):  {"allowed": True, "stabilization": 0},
    ("LOCKDOWN", "NORMAL"):    {"allowed": False, "reason": "Manual operator intervention required"},
    ("LOCKDOWN", "ELEVATED"):  {"allowed": False, "reason": "Manual operator intervention required"},
    ("LOCKDOWN", "DEGRADED"):  {"allowed": False, "reason": "Manual operator intervention required"},
}


class GovernanceResolver:

    def __init__(self, anti_flap_seconds: float = 30.0):
        self._modes: dict[str, GovernanceMode] = {}
        self._matrix: dict[str, dict[str, str]] = {}
        self._last_transition_time: float = time.time()
        self._anti_flap_seconds = anti_flap_seconds
        self._last_state: Optional[GovernanceState] = None
        self._load()

    def _load(self) -> None:
        modes_path = os.path.join(GOVERNANCE_DIR, "modes.json")
        matrix_path = os.path.join(GOVERNANCE_DIR, "matrix.json")

        if os.path.exists(modes_path):
            with open(modes_path, encoding="utf-8") as f:
                data = json.load(f)
            for name, cfg in data.get("modes", {}).items():
                self._modes[name] = GovernanceMode(
                    name=name,
                    description=cfg.get("description", ""),
                    allows=cfg.get("allows", []),
                    blocks=cfg.get("blocks", []),
                    default_capability_behavior=cfg.get("default_capability_behavior", "read_only"),
                    requires_approval=cfg.get("requires_approval", []),
                )

        if os.path.exists(matrix_path):
            with open(matrix_path, encoding="utf-8") as f:
                data = json.load(f)
            self._matrix = data.get("capability_governance", {})

    def get_modes(self) -> dict[str, GovernanceMode]:
        return dict(self._modes)

    def get_matrix(self) -> dict[str, dict[str, str]]:
        return dict(self._matrix)

    def resolve_governance_mode(self, signals: TriggerSignals) -> str:
        if signals.emergency_mode:
            return "LOCKDOWN"
        if signals.degradation_level in ("HEAVY", "EMERGENCY"):
            return "DEGRADED"
        if signals.degradation_level == "LIGHT":
            return "ELEVATED"
        if signals.slo_state == "RED":
            return "ELEVATED"
        if signals.vram_pressure > 0.9:
            return "ELEVATED"
        if signals.gpu_pressure > 0.9:
            return "ELEVATED"
        if signals.timeout_rate > 0.1:
            return "ELEVATED"
        return "NORMAL"

    def _check_anti_flap(self, new_mode: str) -> bool:
        now = time.time()
        if now - self._last_transition_time < self._anti_flap_seconds:
            return False
        return True

    def _check_transition_allowed(self, from_mode: str, to_mode: str) -> tuple[bool, str]:
        if from_mode == to_mode:
            return True, ""
        if self._last_state is None:
            return True, ""
        rule = TRANSITION_RULES.get((from_mode, to_mode))
        if rule is None:
            return False, f"Unknown transition from {from_mode} to {to_mode}"
        if not rule["allowed"]:
            return False, rule.get("reason", "Transition not allowed")

        stab = rule.get("stabilization", 0)
        now = time.time()
        if stab > 0 and now - self._last_transition_time < stab:
            return False, f"Stabilization period of {stab}s required for {from_mode} -> {to_mode}"

        return True, ""

    @staticmethod
    def _resolve_capability_status(
        mode: str,
        capability_id: str,
        matrix: dict[str, dict[str, str]],
        default_behavior: str,
    ) -> str:
        cap_matrix = matrix.get(capability_id, {})
        explicit = cap_matrix.get(mode)
        if explicit is not None:
            return explicit
        mapping = {
            "read_only": "allowed",
            "requires_approval": "requires_approval",
            "blocked_except_observe": "requires_approval",
            "blocked": "blocked",
        }
        return mapping.get(default_behavior, "requires_approval")

    def resolve(self, signals: TriggerSignals) -> GovernanceState:
        new_mode = self.resolve_governance_mode(signals)

        prev_mode = None
        prev_source = "control_plane"
        transition_count = 0

        if self._last_state is not None:
            prev_mode = self._last_state.mode
            prev_source = self._last_state.source
            transition_count = self._last_state.transition_count

            if new_mode != prev_mode:
                allowed, msg = self._check_transition_allowed(prev_mode, new_mode)
                if not allowed:
                    new_mode = prev_mode
                else:
                    if not self._check_anti_flap(new_mode):
                        new_mode = prev_mode
                    else:
                        self._last_transition_time = time.time()
                        transition_count += 1

        default_behavior = self._get_default_behavior(new_mode)
        resolved_caps = {}
        all_cap_ids = set(self._matrix.keys())
        for cid in sorted(all_cap_ids):
            resolved_caps[cid] = self._resolve_capability_status(
                new_mode, cid, self._matrix, default_behavior,
            )

        state = GovernanceState(
            mode=new_mode,
            source=prev_source if prev_source else "control_plane",
            resolved_at=time.time(),
            trigger_signals=signals,
            capabilities=resolved_caps,
            previous_mode=prev_mode,
            transition_count=transition_count,
        )

        self._last_state = state
        return state

    def _get_default_behavior(self, mode: str) -> str:
        gm = self._modes.get(mode)
        if gm is not None:
            return gm.default_capability_behavior
        return "read_only"

    def get_mode_description(self, mode: str) -> Optional[dict]:
        gm = self._modes.get(mode)
        if gm is not None:
            return {
                "allows": gm.allows,
                "blocks": gm.blocks,
                "requires_approval": gm.requires_approval,
            }
        return None
