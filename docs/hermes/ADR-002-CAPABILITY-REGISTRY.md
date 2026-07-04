# ADR-002: Capability Registry

**Status:** DRAFT — Design only
**Date:** 2026-07-03
**Based on:** ADR-001 (SOUL domains)

---

## Context

Hermes Enterprise operates across multiple domains (AI-LAB, Marketplace, Observability, GitNexus). Each domain requires specific capabilities. Currently:
- Capabilities are implicit in AGENTS.md and workflow files
- No formal registry exists
- No way to discover what Hermes can do without reading all documentation

Audit finding: "Skills/MCP/Operators funcionan, pero no tienen registry enterprise unificado."

## Decision

Create `runtime/hermes/capabilities/` with a formal Capability Registry. Each capability is a bounded, observable unit of operation.

---

## Design

### 1. What is a Capability?

A **capability** is a bounded domain of operation that Hermes can exercise. It defines:
- What domain it belongs to
- What tools/MCP servers it requires
- What governance level it needs
- What outputs it produces
- Whether it is read-only or can write

### 2. Capability Schema (`capability_schema.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["id", "name", "version", "domain", "read_only", "governance_level"],
  "properties": {
    "id": { "type": "string", "description": "Unique capability identifier" },
    "name": { "type": "string", "description": "Human-readable name" },
    "version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
    "description": { "type": "string" },
    "domain": { "type": "string", "enum": ["ai-lab", "marketplace", "observability", "windows", "gitnexus"] },
    "read_only": { "type": "boolean", "default": true },
    "governance_level": {
      "type": "array",
      "items": { "type": "string", "enum": ["normal", "elevated", "degraded", "lockdown"] },
      "description": "Governance levels where this capability is allowed"
    },
    "mcp_required": {
      "type": "array",
      "items": { "type": "string" },
      "description": "MCP server IDs required"
    },
    "tools_required": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Runtime tools required (e.g., read, bash, curl)"
    },
    "skills_required": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Agent skill names required"
    },
    "hooks": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Hook IDs that activate with this capability"
    },
    "dependencies": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Capability IDs that must be available"
    },
    "outputs": {
      "type": "array",
      "items": { "type": "string", "enum": ["report", "alert", "metric", "command", "artifact"] }
    },
    "health_check": {
      "type": "object",
      "properties": {
        "endpoint": { "type": "string" },
        "interval_seconds": { "type": "integer" }
      }
    }
  }
}
```

### 3. Example Capabilities (`registry.json`)

```json
{
  "version": "1.0.0",
  "capabilities": [
    {
      "id": "ai-lab-runtime",
      "name": "AI-LAB Runtime Operations",
      "version": "1.0.0",
      "description": "Monitor and diagnose AI-LAB gateway, router, live-api, SLO, and inference nodes",
      "domain": "ai-lab",
      "read_only": true,
      "governance_level": ["normal", "elevated", "degraded", "lockdown"],
      "mcp_required": ["ailab-runtime-mcp"],
      "tools_required": ["curl"],
      "skills_required": [],
      "hooks": ["before_request", "after_request"],
      "dependencies": [],
      "outputs": ["report", "alert", "metric"],
      "health_check": {
        "endpoint": "http://192.168.1.30:8008/health",
        "interval_seconds": 30
      }
    },
    {
      "id": "marketplace-operator",
      "name": "Marketplace Read-only Operations",
      "version": "1.0.0",
      "description": "Observe and audit Rioja Marketplace OS via GitNexus MCP and public API",
      "domain": "marketplace",
      "read_only": true,
      "governance_level": ["normal", "elevated"],
      "mcp_required": ["gitnexus"],
      "tools_required": ["webfetch"],
      "skills_required": [],
      "hooks": [],
      "dependencies": ["gitnexus-analysis"],
      "outputs": ["report", "alert"],
      "health_check": {
        "endpoint": "https://marketplace.labrazahome.com",
        "interval_seconds": 300
      }
    },
    {
      "id": "observability",
      "name": "Observability Operations",
      "version": "1.0.0",
      "description": "Query Prometheus metrics, Grafana dashboards, and Loki logs",
      "domain": "observability",
      "read_only": true,
      "governance_level": ["normal", "elevated"],
      "mcp_required": [],
      "tools_required": ["curl"],
      "skills_required": [],
      "hooks": [],
      "dependencies": [],
      "outputs": ["report", "metric"],
      "health_check": {
        "endpoint": "http://192.168.1.40:9090/api/v1/query?query=up",
        "interval_seconds": 60
      }
    },
    {
      "id": "gitnexus-analysis",
      "name": "GitNexus Code Analysis",
      "version": "1.0.0",
      "description": "Query the code knowledge graph for impact analysis, context, and structural cognition",
      "domain": "gitnexus",
      "read_only": true,
      "governance_level": ["normal", "elevated", "degraded", "lockdown"],
      "mcp_required": ["gitnexus"],
      "tools_required": [],
      "skills_required": [],
      "hooks": [],
      "dependencies": [],
      "outputs": ["report"],
      "health_check": {
        "endpoint": "gitnexus://repo/ai-lab/context",
        "interval_seconds": 300
      }
    },
    {
      "id": "deployment-review",
      "name": "Deployment Review",
      "version": "1.0.0",
      "description": "Review deployment readiness: Git status, build status, test results, SLO health",
      "domain": "ai-lab",
      "read_only": true,
      "governance_level": ["elevated"],
      "mcp_required": ["ailab-runtime-mcp"],
      "tools_required": ["bash", "read"],
      "skills_required": ["deployment-procedures"],
      "hooks": ["before_request", "on_incident"],
      "dependencies": ["ai-lab-runtime", "gitnexus-analysis"],
      "outputs": ["report"],
      "health_check": {}
    },
    {
      "id": "incident-response",
      "name": "Incident Response",
      "version": "1.0.0",
      "description": "Detect, diagnose, and report runtime incidents with evidence-based analysis",
      "domain": "ai-lab",
      "read_only": true,
      "governance_level": ["normal", "elevated"],
      "mcp_required": ["ailab-runtime-mcp"],
      "tools_required": ["curl"],
      "skills_required": [],
      "hooks": ["on_incident"],
      "dependencies": ["ai-lab-runtime", "observability"],
      "outputs": ["report", "alert"],
      "health_check": {}
    }
  ]
}
```

---

## Impact

| Aspect | Before | After |
|--------|--------|-------|
| Discoverability | Implícito en docs | Formal registry with schema |
| Dependency tracking | Manual | Explicit dependencies array |
| Governance binding | None | Per-capability governance levels |
| Health checks | Ad-hoc | Formal per-capability health check |

## Status

**DRAFT** — Design approved for architecture phase. Implementation deferred to E-02.
