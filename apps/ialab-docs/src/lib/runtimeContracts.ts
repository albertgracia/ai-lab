// FASE 32A: Runtime UI Alignment — TypeScript contracts
// These types mirror the runtime Python contracts for type-safe API consumption.

export interface RuntimeEntity {
  entity_id: string;
  entity_type: "gpu" | "model" | "host" | "service" | "storage";
  operational_state: "active" | "loaded" | "idle" | "inactive" | "down";
  inventory_state?: "inventory" | "expected_offline" | "active";
  discoverability: "discoverable" | "inventory_visible" | "undiscovered";
  routable: boolean;
  deprecated?: boolean;
  confidence: "high" | "medium" | "low" | "unknown";
  freshness: "fresh" | "stale" | "expired" | "unavailable";
  source_of_truth?: string[];
}

export interface TopologyNode {
  node_id: string;
  node_type: string;
  operational_state: string;
  active: boolean;
  discoverable: boolean;
  routable: boolean;
  confidence: string;
  freshness: string;
  authority: string;
  inventory_only: boolean;
  entity_ref: string;
}

export interface TopologyEdge {
  source_id: string;
  target_id: string;
  relationship: string;
  direction: "forward" | "reverse";
  observed: boolean;
  confidence: string;
  weight: number;
}

export interface RuntimeTopology {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  degraded_paths: { source: string; target: string; relationship: string; reason: string }[];
  contract_version: string;
}

export interface RuntimeMaturity {
  runtime_state: "booting" | "stabilizing" | "operational" | "degraded" | "critical" | "unknown";
  maturity_score: number;
  confidence: string;
  uncertainty_level: string;
  operational_impact: string;
  degraded_domains: string[];
  unknown_domains: string[];
}

export interface UIAlignmentScore {
  overall_score: number;
  level: "high" | "medium" | "low" | "critical";
  factors: Record<string, number>;
  penalties: {
    hardcoded_inventory: number;
    fake_entities: number;
    topology_drift: number;
    runtime_mismatch: number;
  };
}

export interface UIAlignment {
  alignment_score: UIAlignmentScore;
  issues: {
    hardcoded_inventory: { entity_id: string; reason: string }[];
    fake_entities: { entity_id: string; fake_gpu: string; reason: string }[];
    topology_drift: { node_id: string; drift: string; severity: string }[];
    runtime_mismatch: { entity_id: string; reason: string }[];
  };
  summary: {
    total_hardcoded: number;
    total_fake: number;
    total_drift: number;
    total_mismatch: number;
    total_issues: number;
  };
}

export interface RuntimeReport {
  confidence: string;
  freshness: string;
  degraded_domains: string[];
  unknown_domains: string[];
  operational_impact: string;
  topology?: {
    total_nodes: number;
    total_edges: number;
    confidence_score: number;
    confidence_level: string;
  };
}

export interface GovernanceSummary {
  blocked_actions: number;
  blocked_by_reason?: Record<string, number>;
  evidence_guard_active: boolean;
  confidence: string;
}

export interface ObservabilityAudit {
  prometheus_targets?: Record<string, unknown>;
  dashboard_audit?: Record<string, unknown>;
  observability_health_score?: Record<string, unknown>;
}
