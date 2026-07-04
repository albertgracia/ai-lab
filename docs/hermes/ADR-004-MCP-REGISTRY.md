# ADR-004: MCP Registry

**Status:** DRAFT — Design only
**Date:** 2026-07-03
**Based on:** ADR-002 (Capability Registry)

---

## Context

Hermes currently has 3 MCP servers:
- `ailab-semantic-gateway` → AI-LAB runtime tools (:8091)
- `filesystem` → local file access
- `git` → git operations

Additionally, GitNexus is available as an MCP tool set, and Prometheus/Marketplace MCP servers are planned.

Currently:
- No formal registry of MCP servers
- No health check requirement for MCP servers (violates Rule #8: always-on)
- No priority or fallback mechanism
- Authentication is per-server, not standardized

## Decision

Create `runtime/hermes/mcp/` with a formal MCP Registry.

---

## Design

### 1. MCP Server Schema (`mcp_server_schema.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["id", "name", "protocol", "tools"],
  "properties": {
    "id": { "type": "string" },
    "name": { "type": "string" },
    "description": { "type": "string" },
    "version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
    "protocol": {
      "type": "string",
      "enum": ["stdio", "url", "gitnexus"]
    },
    "url": { "type": "string", "description": "URL for url protocol" },
    "auth": {
      "type": "object",
      "properties": {
        "type": { "type": "string", "enum": ["token", "none", "key"] },
        "token_var": { "type": "string", "description": "Environment variable name for token" }
      }
    },
    "tools": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "description", "read_only"],
        "properties": {
          "name": { "type": "string" },
          "description": { "type": "string" },
          "read_only": { "type": "boolean" }
        }
      }
    },
    "priority": {
      "type": "integer",
      "description": "Higher = preferred when multiple servers can fulfill a request"
    },
    "health_check": {
      "type": "object",
      "properties": {
        "endpoint": { "type": "string" },
        "interval_seconds": { "type": "integer" },
        "timeout_seconds": { "type": "integer" },
        "expected_status": { "type": "integer" }
      }
    },
    "fallback": {
      "type": "string",
      "description": "Server ID to use if this server is unavailable"
    },
    "status": {
      "type": "string",
      "enum": ["active", "degraded", "planned", "deprecated"]
    }
  }
}
```

### 2. Registry (`registry.json`)

```json
{
  "version": "1.0.0",
  "servers": [
    {
      "id": "gitnexus",
      "name": "GitNexus Code Intelligence",
      "description": "Code knowledge graph for impact analysis, context, and structural cognition",
      "version": "1.6.5",
      "protocol": "gitnexus",
      "auth": { "type": "none" },
      "tools": [
        { "name": "gitnexus_impact", "description": "Blast radius analysis", "read_only": true },
        { "name": "gitnexus_context", "description": "360-degree symbol view", "read_only": true },
        { "name": "gitnexus_query", "description": "Semantic code search", "read_only": true },
        { "name": "gitnexus_detect_changes", "description": "Pre-commit change analysis", "read_only": true },
        { "name": "gitnexus_route_map", "description": "API route mapping", "read_only": true },
        { "name": "gitnexus_rename", "description": "Coordinated symbol rename", "read_only": false }
      ],
      "priority": 100,
      "health_check": {
        "endpoint": "gitnexus://repo/ai-lab/context",
        "interval_seconds": 300,
        "timeout_seconds": 10
      },
      "fallback": null,
      "status": "active"
    },
    {
      "id": "ailab-runtime-mcp",
      "name": "AI-LAB Runtime MCP",
      "description": "Read-only MCP tools for AI-LAB runtime observability",
      "version": "1.0.0",
      "protocol": "url",
      "url": "http://127.0.0.1:8091/mcp",
      "auth": { "type": "token", "token_var": "AILAB_MCP_TOKEN" },
      "tools": [
        { "name": "ailab_status", "description": "Gateway + router health", "read_only": true },
        { "name": "ailab_runtime_health", "description": "Detailed runtime health", "read_only": true },
        { "name": "ailab_route_preview", "description": "Heuristic route classification", "read_only": true },
        { "name": "ailab_operator_summary", "description": "NOC-ready operator summary", "read_only": true },
        { "name": "ailab_incidents_active", "description": "Active incident report", "read_only": true },
        { "name": "ailab_slo_status", "description": "SLO health + violations", "read_only": true },
        { "name": "ailab_health_latency", "description": "Latency stats + health score", "read_only": true },
        { "name": "ailab_memory_search", "description": "Semantic search Qdrant", "read_only": true }
      ],
      "priority": 90,
      "health_check": {
        "endpoint": "http://127.0.0.1:8091",
        "interval_seconds": 30,
        "timeout_seconds": 5
      },
      "fallback": null,
      "status": "active"
    },
    {
      "id": "filesystem",
      "name": "Filesystem Access",
      "description": "Local file read/write operations",
      "version": "1.0.0",
      "protocol": "url",
      "auth": { "type": "none" },
      "tools": [
        { "name": "read", "description": "Read files", "read_only": true },
        { "name": "glob", "description": "File pattern matching", "read_only": true },
        { "name": "grep", "description": "Content search", "read_only": true },
        { "name": "write", "description": "Write files", "read_only": false },
        { "name": "edit", "description": "Edit files", "read_only": false }
      ],
      "priority": 50,
      "health_check": null,
      "fallback": null,
      "status": "active"
    },
    {
      "id": "prometheus",
      "name": "Prometheus Metrics",
      "description": "Query Prometheus for runtime metrics and alerts",
      "version": "1.0.0",
      "status": "planned",
      "protocol": "url",
      "auth": { "type": "none" },
      "tools": [
        { "name": "prometheus_query", "description": "Instant query", "read_only": true },
        { "name": "prometheus_range", "description": "Range query", "read_only": true },
        { "name": "prometheus_targets", "description": "Scrape targets", "read_only": true },
        { "name": "prometheus_alerts", "description": "Active alerts", "read_only": true }
      ],
      "priority": 70,
      "health_check": {
        "endpoint": "http://192.168.1.40:9090/api/v1/query?query=up",
        "interval_seconds": 60,
        "timeout_seconds": 5
      },
      "fallback": null,
      "status": "planned"
    },
    {
      "id": "marketplace-mcp",
      "name": "Marketplace MCP",
      "description": "Rioja Marketplace read-only operations via GitNexus",
      "version": "1.0.0",
      "status": "planned",
      "protocol": "gitnexus",
      "auth": { "type": "none" },
      "tools": [],
      "priority": 60,
      "health_check": null,
      "fallback": "gitnexus",
      "status": "planned"
    }
  ]
}
```

### 3. Health Check Protocol

All MCP servers MUST:
1. Respond to a health check within timeout
2. Return HTTP 200 for URL-protocol servers
3. Return valid context for gitnexus-protocol servers
4. Report `degraded` if tools respond but latency > 2x baseline
5. Report `down` after 3 consecutive failures

---

## Impact

| Aspect | Before | After |
|--------|--------|-------|
| Discovery | Implicit in config files | Formal registry |
| Health checks | None | Mandatory per schema |
| Fallback | None | Formal fallback chain |
| Planned servers | Not documented | Explicit "planned" status |

## Status

**DRAFT** — Design approved for architecture phase. Implementation deferred to E-03.
