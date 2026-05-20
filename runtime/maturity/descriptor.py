import time
from dataclasses import dataclass, field
from enum import Enum


class RuntimePhase(str, Enum):
    PHASE_28_1 = "28.1"
    PHASE_28_2 = "28.2"
    PHASE_28_3 = "28.3"
    PHASE_29_2 = "29.2"
    PHASE_29_3 = "29.3"
    PHASE_29_4 = "29.4"
    PHASE_30A = "30A"
    PHASE_30C = "30C"


class RuntimeMaturityLevel(str, Enum):
    BOOTING = "booting"
    STABILIZING = "stabilizing"
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    EMERGENCY = "emergency"
    SHUTDOWN = "shutdown"


class RuntimeMode(str, Enum):
    COGNITIVE = "cognitive"
    OPERATIONAL = "operational"
    TOOL = "tool"
    EXECUTE = "execute"
    OBSERVE = "observe"


class TopologyRole(str, Enum):
    PRIMARY_CONTROL_PLANE = "primary-control-plane"
    INFERENCE_BACKEND = "inference-backend"
    INVENTORY_OFFLINE = "inventory-offline"


class SchedulerState(str, Enum):
    STATIC = "static"


class GovernanceLevel(str, Enum):
    PASSIVE = "passive"
    OBSERVABLE = "observable"
    ENFORCED = "enforced"


class ModelStatus(str, Enum):
    LOADED = "loaded"
    ACTIVE = "active"
    DISCOVERABLE = "discoverable"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"


@dataclass
class TemporalState:
    last_seen: float = 0.0
    last_routed: float = 0.0
    last_health: str = "unknown"
    last_error: str = ""
    transition_count: int = 0
    first_seen: float = 0.0

    def touch(self) -> None:
        now = time.time()
        if self.first_seen == 0.0:
            self.first_seen = now
        self.last_seen = now

    def record_route(self) -> None:
        self.last_routed = time.time()
        self.transition_count += 1

    def record_health(self, health: str) -> None:
        self.last_health = health
        self.last_seen = time.time()

    def record_error(self, error: str) -> None:
        self.last_error = error
        self.last_seen = time.time()

    def to_dict(self) -> dict:
        return {
            "last_seen": self.last_seen,
            "last_routed": self.last_routed,
            "last_health": self.last_health,
            "last_error": self.last_error,
            "transition_count": self.transition_count,
            "first_seen": self.first_seen,
        }


@dataclass
class RuntimeStateDescriptor:
    phase: str
    maturity: RuntimeMaturityLevel
    topology_mode: str
    scheduler_mode: str
    governance_level: str
    mode: RuntimeMode
    topology_role: TopologyRole
    temporal: TemporalState = field(default_factory=TemporalState)
    generation_ts: float = field(default_factory=time.time)
    degraded_mode: dict | None = None

    def to_dict(self) -> dict:
        result = {
            "runtime_generation": {
                "phase": self.phase,
                "maturity": self.maturity.value,
                "topology_mode": self.topology_mode,
                "scheduler_mode": self.scheduler_mode,
                "governance_level": self.governance_level,
            },
            "mode": self.mode.value if isinstance(self.mode, Enum) else self.mode,
            "topology_role": self.topology_role.value if isinstance(self.topology_role, Enum) else self.topology_role,
            "temporal": self.temporal.to_dict(),
            "generated_at": self.generation_ts,
        }
        if self.degraded_mode is not None:
            result["degraded_mode"] = self.degraded_mode
        return result
