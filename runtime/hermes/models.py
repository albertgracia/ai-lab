from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SoulIdentity:
    name: str
    edition: str
    version: str
    operator_role: str
    mission: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SoulTruthModel:
    truth_levels: dict[str, Any]
    evidence_required: bool
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SoulProtocol:
    priority: int
    description: str
    rule: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SoulBoundaries:
    forbidden_actions: list[dict[str, Any]]
    read_only_allowed: list[dict[str, Any]]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SoulDomain:
    description: str
    scope: str
    nodes: list[dict[str, Any]]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Capability:
    id: str
    name: str
    version: str
    purpose: str
    domains: list[str]
    required_mcp: list[str]
    optional_mcp: list[str]
    permissions: dict[str, Any]
    forbidden_actions: list[str]
    evidence_requirements: dict[str, Any]
    reports: list[dict[str, Any]]
    dependencies: list[str]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPTool:
    name: str
    description: str
    read_only: bool


@dataclass
class MCPServer:
    id: str
    name: str
    description: str
    version: str
    protocol: str
    tools: list[MCPTool]
    status: str
    priority: int
    auth: dict[str, Any]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Operator:
    id: str
    name: str
    version: str
    description: str
    capabilities: list[str]
    domains: list[str]
    execution_mode: str
    required_mcp: list[str]
    required_protocols: list[str]
    authorization_required: bool
    priority: int
    reports: list[dict[str, Any]]
    forbidden_actions: list[str]
    truth_model: dict[str, Any]
    success_criteria: list[str]
    failure_conditions: list[str]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Hook:
    id: str
    name: str
    version: str
    lifecycle_event: str
    description: str
    enabled: bool
    mode: str
    timeout_ms: int
    failure_policy: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class HermesRegistry:
    soul_identity: Optional[SoulIdentity] = None
    soul_truth_model: Optional[SoulTruthModel] = None
    soul_protocols: list[SoulProtocol] = field(default_factory=list)
    soul_boundaries: Optional[SoulBoundaries] = None
    soul_domains: list[SoulDomain] = field(default_factory=list)
    capabilities: list[Capability] = field(default_factory=list)
    mcp_servers: list[MCPServer] = field(default_factory=list)
    operators: list[Operator] = field(default_factory=list)
    hooks: list[Hook] = field(default_factory=list)


@dataclass
class ValidationError:
    field: str
    message: str
    source: str


@dataclass
class ValidationWarning:
    field: str
    message: str
    source: str


@dataclass
class ValidationResult:
    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationWarning] = field(default_factory=list)


@dataclass
class CapabilityDependencyGraph:
    nodes: list[str]
    edges: list[dict[str, str]]
    cycles_detected: bool
    cycles: list[list[str]]


@dataclass
class TriggerSignals:
    slo_state: str = "GREEN"
    degradation_level: str = "NONE"
    emergency_mode: bool = False
    vram_pressure: float = 0.0
    gpu_pressure: float = 0.0
    timeout_rate: float = 0.0


@dataclass
class GovernanceModeDef:
    name: str
    description: str
    allows: list[str]
    blocks: list[str]
    default_capability_behavior: str
    requires_approval: list[str]


@dataclass
class GovernanceState:
    mode: str
    source: str
    resolved_at: float
    trigger_signals: TriggerSignals
    capabilities: dict[str, str] = field(default_factory=dict)
    previous_mode: Optional[str] = None
    transition_count: int = 0


@dataclass
class CapabilityGovernanceEntry:
    capability_id: str
    status: str


@dataclass
class StatusReport:
    registries_loaded: bool
    soul_loaded: bool
    capabilities_count: int
    operators_count: int
    hooks_count: int
    mcp_servers_count: int
    enforcement_active: bool
    errors: list[dict[str, str]]
    warnings: list[dict[str, str]]
    capability_validation: Optional[dict[str, Any]] = None
    capability_dependency_graph: Optional[dict[str, Any]] = None
    capability_cycles_detected: bool = False
    governance_mode: Optional[str] = None
    governance_transition_count: int = 0
