# ADR-003: Operator Registry

**Status:** DRAFT — Design only
**Date:** 2026-07-03
**Based on:** ADR-001 (SOUL), ADR-002 (Capability Registry)

---

## Context

Hermes currently has workflows in `.agent/workflows/` (11 workflow files) and modes in `runtime/modes/` (5 modes). However:
- No formal distinction between a "workflow" and an "operator"
- No input/output contracts for operations
- No tools/MCP requirements per operation
- No standardized report format

## Decision

Create `runtime/hermes/operators/` with a formal Operator Registry. An operator is a **structured, repeatable workflow** that Hermes executes against a capability.

---

## Design

### 1. What is an Operator?

An **operator** is a structured workflow that:
- Belongs to exactly one **capability** (from Capability Registry)
- Has explicit **inputs** and **outputs**
- Requires specific **tools**, **MCP servers**, and **skills**
- Has **restrictions** (read-only, requires approval, etc.)
- Produces a standardized **report**

Operators replace ad-hoc execution with contracts. They are discoverable and observable.

### 2. Operator Schema (`operator_schema.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["id", "name", "version", "capability", "inputs", "outputs"],
  "properties": {
    "id": { "type": "string", "description": "Unique operator identifier" },
    "name": { "type": "string" },
    "version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
    "description": { "type": "string" },
    "capability": { "type": "string", "description": "Capability ID this operator belongs to" },
    "read_only": { "type": "boolean", "default": true },
    "requires_approval": { "type": "boolean", "default": false },
    "inputs": {
      "type": "object",
      "patternProperties": {
        "^.*$": {
          "type": "object",
          "required": ["type", "description"],
          "properties": {
            "type": { "type": "string" },
            "description": { "type": "string" },
            "required": { "type": "boolean", "default": true },
            "default": {}
          }
        }
      }
    },
    "outputs": {
      "type": "object",
      "required": ["report_format"],
      "properties": {
        "report_format": { "type": "string", "description": "Template file for the output report" },
        "artifacts": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    },
    "tools_required": {
      "type": "array",
      "items": { "type": "string" }
    },
    "mcp_required": {
      "type": "array",
      "items": { "type": "string" }
    },
    "skills_required": {
      "type": "array",
      "items": { "type": "string" }
    },
    "steps": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "description"],
        "properties": {
          "id": { "type": "string" },
          "description": { "type": "string" },
          "tool": { "type": "string" },
          "mcp": { "type": "string" },
          "expected_output": { "type": "string" }
        }
      }
    },
    "hooks": {
      "type": "array",
      "items": { "type": "string" }
    }
  }
}
```

### 3. Example Operators (`registry.json`)

```json
{
  "version": "1.0.0",
  "operators": [
    {
      "id": "runtime-health-check",
      "name": "Runtime Health Check",
      "version": "1.0.0",
      "description": "Check all AI-LAB runtime services health",
      "capability": "ai-lab-runtime",
      "read_only": true,
      "requires_approval": false,
      "inputs": {
        "target": {
          "type": "string",
          "description": "Specific service to check (gateway|router|live-api|all)",
          "required": false,
          "default": "all"
        }
      },
      "outputs": {
        "report_format": "operator_status",
        "artifacts": ["health-snapshot.json"]
      },
      "tools_required": ["curl"],
      "mcp_required": ["ailab-runtime-mcp"],
      "skills_required": [],
      "steps": [
        { "id": "gateway", "description": "Check :8008/health", "mcp": "ailab-runtime-mcp", "expected_output": "health JSON" },
        { "id": "router", "description": "Check :8083/health", "mcp": "ailab-runtime-mcp", "expected_output": "health JSON" },
        { "id": "slo", "description": "Check /slo/health", "mcp": "ailab-runtime-mcp", "expected_output": "SLO state" },
        { "id": "models", "description": "Check LM Studio models", "tool": "curl", "expected_output": "model list" }
      ],
      "hooks": ["before_request", "after_request"]
    },
    {
      "id": "marketplace-audit",
      "name": "Marketplace Audit",
      "version": "1.0.0",
      "description": "Audit marketplace frontend, API, and GitNexus digital twin",
      "capability": "marketplace-operator",
      "read_only": true,
      "requires_approval": false,
      "inputs": {
        "scope": {
          "type": "string",
          "description": "Audit scope (full|frontend|api|code)",
          "required": false,
          "default": "full"
        }
      },
      "outputs": {
        "report_format": "marketplace_audit",
        "artifacts": ["marketplace-snapshot.json"]
      },
      "tools_required": ["webfetch"],
      "mcp_required": ["gitnexus"],
      "skills_required": [],
      "steps": [
        { "id": "frontend", "description": "Check marketplace.labrazahome.com", "tool": "webfetch", "expected_output": "HTTP 200 + content" },
        { "id": "api", "description": "Check /api/v1/wines", "tool": "webfetch", "expected_output": "product list" },
        { "id": "gitnexus", "description": "Query GitNexus for recent changes", "mcp": "gitnexus", "expected_output": "code analysis" }
      ],
      "hooks": []
    },
    {
      "id": "impact-analysis",
      "name": "GitNexus Impact Analysis",
      "version": "1.0.0",
      "description": "Run pre-change impact analysis on a target symbol",
      "capability": "gitnexus-analysis",
      "read_only": true,
      "requires_approval": false,
      "inputs": {
        "target": {
          "type": "string",
          "description": "Symbol name to analyze",
          "required": true
        },
        "direction": {
          "type": "string",
          "description": "upstream|downstream",
          "required": false,
          "default": "upstream"
        }
      },
      "outputs": {
        "report_format": "gitnexus_impact_report",
        "artifacts": []
      },
      "tools_required": [],
      "mcp_required": ["gitnexus"],
      "skills_required": [],
      "steps": [
        { "id": "context", "description": "Get symbol context", "mcp": "gitnexus", "expected_output": "symbol details" },
        { "id": "impact", "description": "Run impact analysis", "mcp": "gitnexus", "expected_output": "blast radius" },
        { "id": "detect", "description": "Detect uncommitted changes", "mcp": "gitnexus", "expected_output": "change scope" }
      ],
      "hooks": []
    },
    {
      "id": "deployment-review",
      "name": "Deployment Readiness Review",
      "version": "1.0.0",
      "description": "Review deployment readiness before release",
      "capability": "deployment-review",
      "read_only": true,
      "requires_approval": true,
      "inputs": {
        "target": {
          "type": "string",
          "description": "What to review (runtime|docs|marketplace)",
          "required": true
        }
      },
      "outputs": {
        "report_format": "deployment_review",
        "artifacts": []
      },
      "tools_required": ["bash", "read"],
      "mcp_required": ["ailab-runtime-mcp", "gitnexus"],
      "skills_required": ["deployment-procedures"],
      "steps": [
        { "id": "health", "description": "Check runtime health", "mcp": "ailab-runtime-mcp", "expected_output": "all green" },
        { "id": "git-status", "description": "Check git status", "tool": "bash", "expected_output": "clean tree" },
        { "id": "tests", "description": "Check test status", "tool": "bash", "expected_output": "tests passing" },
        { "id": "impact", "description": "Check change impact", "mcp": "gitnexus", "expected_output": "low risk" }
      ],
      "hooks": ["before_request", "on_error"]
    },
    {
      "id": "incident-triage",
      "name": "Incident Triage",
      "version": "1.0.0",
      "description": "Triage a runtime incident with evidence-based diagnosis",
      "capability": "incident-response",
      "read_only": true,
      "requires_approval": false,
      "inputs": {
        "incident_id": {
          "type": "string",
          "description": "Incident identifier",
          "required": true
        },
        "symptoms": {
          "type": "string",
          "description": "Observed symptoms",
          "required": true
        }
      },
      "outputs": {
        "report_format": "incident_report",
        "artifacts": ["incident-evidence.json"]
      },
      "tools_required": [],
      "mcp_required": ["ailab-runtime-mcp"],
      "skills_required": [],
      "steps": [
        { "id": "verify", "description": "Verify incident from runtime state", "mcp": "ailab-runtime-mcp", "expected_output": "current state" },
        { "id": "timeline", "description": "Get incident timeline from metrics", "mcp": "ailab-runtime-mcp", "expected_output": "timeline" },
        { "id": "diagnose", "description": "Diagnose root cause", "tool": "read", "expected_output": "diagnosis" },
        { "id": "report", "description": "Generate incident report", "expected_output": "report" }
      ],
      "hooks": ["on_incident"]
    }
  ]
}
```

---

## Impact

| Aspect | Before | After |
|--------|--------|-------|
| Workflow definition | Ad-hoc .md files | Formal JSON schema with contracts |
| Input/output | Not specified | Explicit typed I/O |
| Tool/MCP requirements | Implicit | Explicit per-operator |
| Report format | Inconsistent | Standardized via templates |

## Status

**DRAFT** — Design approved for architecture phase. Implementation deferred to E-02.
