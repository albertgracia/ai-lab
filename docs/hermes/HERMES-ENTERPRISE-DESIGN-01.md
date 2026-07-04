# HERMES Enterprise Design v1

**Version:** 1.0.0
**Status:** DRAFT — Design only, no implementation
**Based on:** HERMES-ENTERPRISE-ARCHITECTURE-AUDIT-01 (PASS)
**Date:** 2026-07-03

---

## 1. Design Philosophy

### Principles

1. **Observability over intuition** — all state must be observable via health endpoints, metrics, or logs. No hidden state.
2. **Contracts over convention** — every capability, operator, MCP server, and hook has a formal contract.
3. **Read-only by default** — write operations require explicit governance level escalation.
4. **Evidence-first** — every operational claim must cite its source and confidence level.
5. **Minimal viable layers** — no layer exists without a demonstrated need from the audit.

### Design Constraints

| Constraint | Source |
|-----------|--------|
| No modification to existing runtime code | Audit scope |
| Backward compatible with AGENTS.md rules | Constitution |
| All registries must be file-based (JSON) | Git-friendly, no DB dependency |
| All hooks must be observable via Prometheus | Observability mandate |
| All MCP servers must have health checks | Rule #8 (always-on) |

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        HERMES ENTERPRISE                         │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  SOUL — System Ontological Unified Layer                  │   │
│  │  ├── identity.json    → Who Hermes is                     │   │
│  │  ├── mission.json     → What Hermes does                  │   │
│  │  ├── truth_model.md   → How Hermes knows                  │   │
│  │  ├── protocols.md     → How Hermes acts                   │   │
│  │  ├── boundaries.json  → What Hermes must NOT do           │   │
│  │  ├── authority.json   → What Hermes CAN do                │   │
│  │  └── domains.json     → What Hermes oversees              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  REGISTRIES                                              │   │
│  │                                                          │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐         │   │
│  │  │ CAPABILITY │  │  OPERATOR  │  │    MCP     │         │   │
│  │  │ REGISTRY   │  │  REGISTRY  │  │  REGISTRY  │         │   │
│  │  │ capabilities│  │ operators  │  │ servers    │         │   │
│  │  │ .json      │  │ .json      │  │ .json      │         │   │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘         │   │
│  └────────┼───────────────┼───────────────┼─────────────────┘   │
│           │               │               │                      │
│  ┌────────▼───────────────▼───────────────▼─────────────────┐   │
│  │  SUBSYSTEMS                                              │   │
│  │                                                          │   │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────────┐   │   │
│  │  │ HOOKS      │  │ GOVERNANCE │  │   TEMPLATES      │   │   │
│  │  │ hook_      │  │ modes.json │  │   .md templates  │   │   │
│  │  │ registry   │  │ + resolve  │  │   for reports    │   │   │
│  │  └────────────┘  └────────────┘  └──────────────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Folder Structure

```
runtime/hermes/                          # Enterprise layer (design only)
├── soul/                                # ADR-001
│   ├── identity.json
│   ├── mission.json
│   ├── truth_model.md
│   ├── protocols.md
│   ├── boundaries.json
│   ├── authority.json
│   └── domains.json
├── capabilities/                        # ADR-002
│   ├── registry.json
│   └── schemas/
│       └── capability_schema.json
├── operators/                           # ADR-003
│   ├── registry.json
│   ├── schemas/
│   │   └── operator_schema.json
│   └── reports/
├── mcp/                                 # ADR-004
│   ├── registry.json
│   ├── schemas/
│   │   └── mcp_server_schema.json
│   └── health/
├── hooks/                               # ADR-005
│   ├── registry.json
│   ├── schemas/
│   │   └── hook_schema.json
│   └── lifecycle.json
├── governance/                          # ADR-006
│   ├── modes.json
│   ├── rules.json
│   └── resolver.py
├── templates/                           # Design only
│   ├── incident_report.md
│   ├── deployment_review.md
│   ├── gitnexus_impact_report.md
│   ├── marketplace_audit.md
│   └── operator_status.md
└── schemas/                             # Shared schemas
    ├── base_types.json
    └── evidence.json

docs/hermes/
├── HERMES-ENTERPRISE-DESIGN-01.md       # This document
├── ADR-001-SOUL.md
├── ADR-002-CAPABILITY-REGISTRY.md
├── ADR-003-OPERATOR-REGISTRY.md
├── ADR-004-MCP-REGISTRY.md
├── ADR-005-HOOK-SYSTEM.md
└── ADR-006-DYNAMIC-GOVERNANCE.md
```

---

## 4. Data Flow

```
Request (Operator intent)
    │
    ▼
┌────────────────┐
│  GOVERNANCE    │─── resolve_mode() ──► NORMAL | DEGRADED | ELEVATED | LOCKDOWN
│  RESOLVER      │
└───────┬────────┘
        │ allowed?
        │
   ┌────┴────┐
   │   YES   │   NO ──► Blocked + audit log
   └────┬────┘
        │
        ▼
┌────────────────┐
│  HOOKS         │─── before_request() ──► validate identity, check boundaries
│  before_*      │─── before_tool()    ──► validate tool against capability
└───────┬────────┘
        │
        ▼
┌────────────────┐
│  OPERATOR      │─── execute workflow
│  (workflow)    │    ├── MCP call ──► MCP Registry ──► server
│                │    ├── tool call ──► validated by governance
│                │    └── evidence    ──► logged with confidence
└───────┬────────┘
        │
        ▼
┌────────────────┐
│  HOOKS         │─── after_request() ──► log result, emit metrics
│  after_*       │─── on_error()      ──► incident hook
└────────────────┘
```

---

## 5. Evidence Model

Every operational claim must carry:

```json
{
  "claim": "LM Studio is available at 192.168.1.50:1234",
  "source": "health_endpoint",
  "confidence": "high",
  "type": "observed",
  "timestamp": "2026-07-03T12:00:00Z",
  "ttl_seconds": 300
}
```

**Evidence chain of custody:**
```
observed    → health endpoint, metrics, API response
inferred    → code analysis, GitNexus, logs pattern
supposed    → documentation, reports, past state
```

---

## 6. Security Model

| Layer | Auth | Transport |
|-------|------|-----------|
| MCP servers | Token (AILAB_MCP_TOKEN) | mTLS or localhost |
| Gateway | None (internal) | Internal network |
| Hook system | Governance level | In-process |
| File registries | Git commit signing | Local FS |

---

## 7. Risks

| # | Risk | Mitigation |
|---|------|------------|
| R1 | SOUL creates identity conflicts with existing AGENTS.md | SOUL must defer to AGENTS.md for all constitutional rules |
| R2 | Registry files drift from reality | Add validation scripts + CI check |
| R3 | Hook system adds latency to hot path | Hooks are async by default; sync hooks require explicit opt-in |
| R4 | Governance levels become stale | Governance resolver must poll control_plane state |
| R5 | ADRs are not implemented before next phase | Prioritize ADR-001 (SOUL) and ADR-006 (Governance) as they are pre-requisites |

---

## 8. Implementation Phases

| Phase | ADRs | Effort | Dependencies |
|-------|------|--------|-------------|
| **E-01** | ADR-001 (SOUL) + ADR-006 (Governance) | 3-4d | None — pure design + file creation |
| **E-02** | ADR-002 (Capability) + ADR-003 (Operator) | 2-3d | E-01 (SOUL defines domains) |
| **E-03** | ADR-004 (MCP Registry) | 1-2d | E-02 (capabilities need MCP) |
| **E-04** | ADR-005 (Hook System) | 2-3d | E-01 (governance mode needed for hook auth) |
| **E-05** | Templates + schemas | 1d | E-02 (templates match operators) |
| **E-06** | Folder structure + validation scripts | 1d | All ADRs |
