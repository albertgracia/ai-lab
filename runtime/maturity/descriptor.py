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
    PHASE_30D = "30D"
    PHASE_30G = "30G"
    PHASE_30H = "30H"


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
    OBSERVABILITY_NODE = "observability-node"
    EXTERNAL_GATEWAY = "external-gateway"


class FailureDomain(str, Enum):
    CONTROL_PLANE = "control-plane"
    INFERENCE_GPU = "inference-gpu"
    INFERENCE_CPU = "inference-cpu"
    NETWORK = "network"
    STORAGE = "storage"
    OBSERVABILITY = "observability"
    EXTERNAL = "external"


@dataclass
class NodeTopology:
    node_id: str
    host: str
    port: int | None = None
    role: TopologyRole = TopologyRole.INVENTORY_OFFLINE
    failure_domain: FailureDomain = FailureDomain.NETWORK
    status: str = "unknown"
    online: bool = False
    latency_ms: float | None = None
    last_seen: float = 0.0
    models: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "host": self.host,
            "port": self.port,
            "role": self.role.value,
            "failure_domain": self.failure_domain.value,
            "status": self.status,
            "online": self.online,
            "latency_ms": self.latency_ms,
            "last_seen": self.last_seen,
            "models": self.models,
            "capabilities": self.capabilities,
            "error": self.error,
        }


class SchedulerState(str, Enum):
    STATIC = "static"


class GovernanceLevel(str, Enum):
    PASSIVE = "passive"
    OBSERVABLE = "observable"
    ENFORCED = "enforced"
    DEGRADED = "degraded"
    LOCKDOWN = "lockdown"


class ModelStatus(str, Enum):
    LOADED = "loaded"
    ACTIVE = "active"
    DISCOVERABLE = "discoverable"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"


class RouteFamilyStatus(str, Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    THROTTLED = "throttled"
    BLOCKED = "blocked"
    UNUSED = "unused"
    UNKNOWN = "unknown"


@dataclass
class RouteSemantics:
    family: str = ""
    status: RouteFamilyStatus = RouteFamilyStatus.UNKNOWN
    status_source: str = "lifetime_metrics"
    total_requests: int = 0
    error_count: int = 0
    blocked_count: int = 0
    last_routed_at: float = 0.0
    last_error_at: float = 0.0
    avg_latency_ms: float = 0.0
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "family": self.family,
            "status": self.status.value,
            "status_source": self.status_source,
            "total_requests": self.total_requests,
            "error_count": self.error_count,
            "blocked_count": self.blocked_count,
            "last_routed_at": self.last_routed_at,
            "last_error_at": self.last_error_at,
            "avg_latency_ms": self.avg_latency_ms,
            "reason": self.reason,
        }


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
class GovVisibility:
    level: GovernanceLevel = GovernanceLevel.ENFORCED
    operational_state: str = "unknown"
    source: str = "control_plane"
    blocked_total: int = 0
    blocks_by_reason: dict = field(default_factory=dict)
    active_policies: list[str] = field(default_factory=list)
    temporal: TemporalState = field(default_factory=TemporalState)
    last_decision_at: float | None = None

    def to_dict(self) -> dict:
        return {
            "level": self.level.value,
            "operational_state": self.operational_state,
            "source": self.source,
            "blocked_total": self.blocked_total,
            "blocks_by_reason": dict(self.blocks_by_reason),
            "active_policies": list(self.active_policies),
            "temporal": self.temporal.to_dict(),
            "last_decision_at": self.last_decision_at,
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
    failure_domain: FailureDomain = FailureDomain.CONTROL_PLANE
    temporal: TemporalState = field(default_factory=TemporalState)
    generation_ts: float = field(default_factory=time.time)
    degraded_mode: dict | None = None
    gov_visibility: GovVisibility | None = None

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
            "failure_domain": self.failure_domain.value if isinstance(self.failure_domain, Enum) else self.failure_domain,
            "temporal": self.temporal.to_dict(),
            "generated_at": self.generation_ts,
        }
        if self.degraded_mode is not None:
            result["degraded_mode"] = self.degraded_mode
        if self.gov_visibility is not None:
            result["gov_visibility"] = self.gov_visibility.to_dict()
        return result
