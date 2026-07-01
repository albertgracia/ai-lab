# AI-LAB Documentation Hierarchy

> **Version:** 1.0
> **Date:** 2026-07-01
> **Status:** CURRENT
> **Owner:** Runtime Governance

---

## Overview

This document defines the official AI-LAB documentation hierarchy, ownership, and update policy. Every document in the repository is classified and belongs to exactly one level.

---

## Hierarchy

### Level 1 — Operational Entry Point

| Document | Purpose | Owner |
|----------|---------|-------|
| `AGENTS.md` | Project overview, architecture, operational rules, phase summary, pointers to detailed docs | Runtime Governance |

The single file every engineer and agent reads first. Contains the minimum context needed to operate.

---

### Level 2 — Technical Reference

| Document | Purpose | Owner |
|----------|---------|-------|
| `docs/ARCHITECTURE.md` | Complete technical architecture — Gateway, Router, Live API, GitNexus, Hermes, MCP, Observability, Inference, Memory, Operator Reasoning | Runtime Architecture |
| `docs/DOCUMENTATION-HIERARCHY.md` | (this file) — document classification, ownership, update policy | Runtime Governance |

The detailed reference for how AI-LAB works.

---

### Level 3 — Operations

| Document | Purpose | Owner |
|----------|---------|-------|
| `.agent/BOOTSTRAP.md` | Agent bootstrap — how OpenCode loads and uses the `.agent` knowledge layer | Agent Layer |
| `docs/ROADMAP-2026.md` | Official roadmap — completed phases, current phase, future phases, dependencies | Runtime Governance |

Operational guides for deployment, recovery, and planning.

---

### Level 4 — Historical & Audit

| Document | Purpose | Owner |
|----------|---------|-------|
| `conversation-history.md` | Historical timeline of all phases — milestones, tags, reports. NOT operational documentation. | Runtime Governance |
| `docs/audits/` | All phase audit reports, organized by year and domain | Runtime Governance |
| `docs/archive/` | Deprecated or obsolete documentation, preserved for traceability | Runtime Governance |

The historical record. Not required for daily operation.

---

## Document Classification

Every document in the repository carries one of these classifications:

| Class | Meaning | Color |
|-------|---------|-------|
| **CURRENT** | Active source of truth. Reflects the deployed runtime. | ✅ |
| **ARCHIVED** | Preserved for history. No longer reflects current state. | 📦 |
| **DEPRECATED** | Superseded by a newer document. Do not use as reference. | ⚠️ |
| **GENERATED** | Auto-generated (metrics, audit snapshots). Read-only. | 🤖 |
| **LEGACY** | Historical planning documents from early phases. Archived. | 🏛️ |

---

## Document Inventory

### AGENTS.md

| Field | Value |
|-------|-------|
| Classification | **CURRENT** |
| Level | 1 |
| Update cadence | Per-phase closure or configuration change |
| Location | Root `/AGENTS.md` |

### docs/ARCHITECTURE.md

| Field | Value |
|-------|-------|
| Classification | **CURRENT** |
| Level | 2 |
| Update cadence | When architecture changes |
| Location | `docs/ARCHITECTURE.md` |

### docs/ROADMAP-2026.md

| Field | Value |
|-------|-------|
| Classification | **CURRENT** |
| Level | 3 |
| Update cadence | Per-phase closure |
| Location | `docs/ROADMAP-2026.md` |

### .agent/BOOTSTRAP.md

| Field | Value |
|-------|-------|
| Classification | **CURRENT** |
| Level | 3 |
| Update cadence | When agent layer changes |
| Location | `.agent/BOOTSTRAP.md` |

### conversation-history.md

| Field | Value |
|-------|-------|
| Classification | **CURRENT** |
| Level | 4 |
| Update cadence | Per-phase closure (milestones only) |
| Location | Root `/conversation-history.md` |

### docs/audits/

| Field | Value |
|-------|-------|
| Classification | **GENERATED** / **ARCHIVED** |
| Level | 4 |
| Update cadence | Per-phase (new audit) |
| Location | `docs/audits/{year}/{domain}/` |

### docs/archive/

| Field | Value |
|-------|-------|
| Classification | **ARCHIVED** / **LEGACY** |
| Level | 4 |
| Update cadence | On deprecation |
| Location | `docs/archive/` |

---

## Classification of Existing Documents

### Root Level

| File | Class | Action |
|------|-------|--------|
| `AGENTS.md` | **CURRENT** | Keep |
| `README.md` | **CURRENT** | Updated this session |
| `conversation-history.md` | **CURRENT** | Rewritten this session |
| `AI-LAB-ARCHITECTURE-AND-OPERATIONS.md.txt` | **LEGACY** | Moved to `docs/archive/` |
| `OPENCODE.md` | **DEPRECATED** | Content merged into AGENTS.md |

### .agent/

| File | Class | Action |
|------|-------|--------|
| `.agent/BOOTSTRAP.md` | **CURRENT** | Keep |
| `.agent/ARCHITECTURE.md` | **DEPRECATED** | Not AI-LAB architecture (generic agent layer) |
| `.agent/OPENCODE_PROMPT.md` | **CURRENT** | Keep (agent behavior rules) |

### docs/

| File | Class | Action |
|------|-------|--------|
| `docs/ARCHITECTURE.md` | **CURRENT** | Rewritten this session |
| `docs/ROADMAP-2026.md` | **CURRENT** | Created this session |
| `docs/DOCUMENTATION-HIERARCHY.md` | **CURRENT** | (this file) |
| `docs/ARCHITECTURE-PHASE8.md` | **LEGACY** | Moved to `docs/archive/` |
| `docs/ARQUITECTURA_PUBLICO_PRIVADO.md` | **LEGACY** | Moved to `docs/archive/` |
| `docs/ASTRO_CLOUDFLARE_GITHUB.md` | **LEGACY** | Superseded by AGENTS.md Astro rules |
| `docs/AUTOMATIZACION_CI_CD.md` | **ARCHIVED** | Moved to `docs/archive/` |
| `docs/COGNITIVE_ROUTER_PHASE5.md` | **LEGACY** | Moved to `docs/archive/` |
| `docs/CLOUDFLARE_PAGES_REDIRECTS.md` | **LEGACY** | Moved to `docs/archive/` |
| `docs/DEBUGGING.md` | **LEGACY** | Moved to `docs/archive/` |
| `docs/EVENT-BUS.md` | **LEGACY** | Moved to `docs/archive/` |
| `docs/IA-LAB — Estado actual...` | **ARCHIVED** | Moved to `docs/archive/` |
| `docs/INFRASTRUCTURE.md` | **ARCHIVED** | Moved to `docs/archive/` |
| `docs/OPENCODE_AGENT_LAYER.md` | **LEGACY** | Moved to `docs/archive/` |
| `docs/OPENWEBUI_CONEXION_ROUTER.md` | **LEGACY** | Moved to `docs/archive/` |
| `docs/ROADMAP.md` | **DEPRECATED** | Superseded by `docs/ROADMAP-2026.md` |
| `docs/RUNBOOK_CLOUDFLARE_PAGES.md` | **LEGACY** | Content in AGENTS.md |
| `docs/RUNTIME_ANALYTICS.md` | **LEGACY** | Moved to `docs/archive/` |
| `docs/RUNTIME_ANALYTICS_CORRECCION.md` | **LEGACY** | Moved to `docs/archive/` |
| `docs/RUNTIME-FLOW.md` | **LEGACY** | Moved to `docs/archive/` |
| `docs/TOPOLOGY-LAYER.md` | **LEGACY** | Moved to `docs/archive/` |
| `docs/blog-analytics-implementation.md` | **LEGACY** | Moved to `docs/archive/` |

### docs/architecture/

| File | Class | Action |
|------|-------|--------|
| `AILAB-DUAL-PATH-ARCHITECTURE-DOC-01.md` | **CURRENT** | Content integrated into `docs/ARCHITECTURE.md` |

### docs/mcp/

| File | Class | Action |
|------|-------|--------|
| All MCP docs | **CURRENT** | Keep |

### docs/opencode/

| File | Class | Action |
|------|-------|--------|
| All OpenCode config docs | **CURRENT** | Keep |

### docs/quarantine/

| File | Class | Action |
|------|-------|--------|
| All quarantine items | **ARCHIVED** | Move to `docs/archive/` |

### docs/releases/

| File | Class | Action |
|------|-------|--------|
| All release docs | **CURRENT** | Keep |

### docs/runtime/

| File | Class | Action |
|------|-------|--------|
| All runtime docs | **CURRENT** | Keep |

### docs/audits/

| File | Class | Action |
|------|-------|--------|
| 135+ audit reports | **GENERATED** | Reorganize into subdirectories |

---

## Update Policy

1. **Level 1 (AGENTS.md):** Updated per-phase closure. Must reflect the exact deployed state.
2. **Level 2 (ARCHITECTURE.md):** Updated when Gateway, Router, Live API, or core infrastructure changes.
3. **Level 3 (ROADMAP.md, BOOTSTRAP.md):** Updated per-phase closure or configuration change.
4. **Level 4 (conversation-history.md, audits, archive):** Appended per-phase. Never rewritten — only compressed when explicitly requested.

## Priority Rules

If documentation contradicts runtime:

> **Runtime wins.**

If Level 1 contradicts Level 2:

> **Level 1 wins.** (AGENTS.md is the binding operational document.)

If git history contradicts documentation:

> **Git history wins.** (Tags and commits are the authoritative record.)

If GitNexus contradicts git history:

> **Git history wins.** (GitNexus may be stale.)

---

## Quick Reference

```
AI-LAB Documentation
├── AGENTS.md                              (Level 1 — READ FIRST)
├── README.md                              (Project card)
│
├── docs/
│   ├── ARCHITECTURE.md                    (Level 2 — technical reference)
│   ├── DOCUMENTATION-HIERARCHY.md         (Level 2 — this file)
│   ├── ROADMAP-2026.md                    (Level 3 — roadmap)
│   │
│   ├── architecture/                      (Current architecture details)
│   ├── mcp/                               (MCP documentation)
│   ├── opencode/                          (OpenCode configuration)
│   ├── releases/                          (Release documentation)
│   ├── runtime/                           (Runtime documentation)
│   │
│   ├── audits/                            (Level 4 — phase audit reports)
│   │   └── {year}/{domain}/
│   │
│   └── archive/                           (Level 4 — deprecated docs)
│
├── .agent/
│   ├── BOOTSTRAP.md                       (Level 3 — agent bootstrap)
│   └── ...                                (Agent layer)
│
└── conversation-history.md                (Level 4 — historical timeline)
```
