# MCP Registry — Hermes Enterprise

**Location:** `runtime/hermes/mcp/`
**Version:** 1.0.0
**Status:** DECLARATIVE — Skeleton only, no runtime enforcement
**Based on:** ADR-004-MCP-REGISTRY

## Purpose

The MCP Registry is the formal inventory of all MCP servers available to Hermes. Each server is a declarative YAML file specifying:

- **Identity:** id, name, description, version
- **Protocol:** stdio, url, or gitnexus-native
- **Tools:** full list of exposed tools with read_only flag
- **Connectivity:** URL, auth, health check config
- **Resilience:** priority, fallback chain
- **Status:** active, degraded, planned, deprecated

## Servers

| ID | Name | Protocol | Status | Priority |
|----|------|----------|--------|----------|
| `gitnexus` | GitNexus Code Intelligence | gitnexus | ✅ active | 100 |
| `ailab-runtime-mcp` | AI-LAB Runtime MCP | url | ✅ active | 90 |
| `filesystem` | Filesystem Access | url | ✅ active | 50 |
| `prometheus` | Prometheus Metrics | url | 📋 planned | 70 |
| `marketplace-mcp` | Marketplace MCP | gitnexus | 📋 planned | 60 |

## Files

| File | Purpose |
|------|---------|
| `mcp_server.schema.json` | JSON Schema validating all MCP server YAML files |
| `registry.yaml` | Registry metadata and server index |
| `gitnexus.yaml` | GitNexus Code Intelligence |
| `ailab-runtime.yaml` | AI-LAB Runtime MCP |
| `filesystem.yaml` | Filesystem Access |
| `prometheus.yaml` | Prometheus Metrics (planned) |
| `marketplace.yaml` | Marketplace MCP (planned) |
| `README.md` | This file |

## Governance

All servers are declarative-only. No enforcement, no health checks. YAML files must pass `mcp_server.schema.json` validation. Use `status: planned` for servers not yet deployed.

## References

- ADR-004: `docs/hermes/ADR-004-MCP-REGISTRY.md`
- Capability Registry: `runtime/hermes/capabilities/`
- Enterprise Design: `docs/hermes/HERMES-ENTERPRISE-DESIGN-01.md`
