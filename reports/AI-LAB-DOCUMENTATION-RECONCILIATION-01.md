# AI-LAB-DOCUMENTATION-RECONCILIATION-01

## Executive Summary

**Result:** PASS WITH WARNINGS — 6 critical gaps found

AI-LAB documentation is severely fragmented and outdated. The canonical doc (AGENTS.md) covers Block 36B correctly but is missing Blocks 37-40. The conversation-history.md is 30+ phases behind. README.md, OPENCODE.md, docs/ARCHITECTURE.md, and docs/ROADMAP.md are obsolete. The .30 runtime repo and this workspace have diverged git histories for Block 37. 135 audit files in docs/audits need triage.

**Health Score: 38/100** (Critical)

---

## Documentation Health Score

| Category | Score | Status |
|----------|-------|--------|
| Workspace Rules (AGENTS.md) | 70 | PARTIAL |
| Agent Layer (.agent/) | 65 | PARTIAL |
| Git History Accuracy | 30 | OUTDATED |
| Roadmap Alignment | 10 | OBSOLETE |
| Architecture Docs | 15 | OBSOLETE |
| Session History | 5 | OUTDATED |
| Operational Docs | 85 | CURRENT |
| Runtime Alignment | 20 | DRIFT |
| **Composite** | **38** | **CRITICAL** |

---

## Document Status Table

| # | Document | Location | Status | Evidence | Action |
|---|----------|----------|--------|----------|--------|
| 1 | **AGENTS.md** | `/AGENTS.md` | **PARTIAL** | Covers CP-21B through CP-36B correctly. Roadmap section shows 37B/37C/37D as future but 39C/39E/40A tags exist on origin. Missing Blocks 37-40. | UPDATE |
| 2 | **conversation-history.md** | `/conversation-history.md` | **OUTDATED** | HEAD at `a1572e02`, claims 63 tags (39 real). Last phase: GITNEXUS-ARCHITECTURE-GOVERNANCE-01. Missing: Block 37C/37D/37E, Blocks 38A-38D, Blocks 39A-39E, Block 40A. | UPDATE |
| 3 | **docs/ROADMAP.md** | `docs/ROADMAP.md` | **OBSOLETE** | Only 4 generic phases (Phase 1-4). No relation to real CP numbering (CP-21B through CP-40A). | ARCHIVE |
| 4 | **README.md** | `/README.md` | **OUTDATED** | Claims `CP-29.4.2-REPORT-PRESENTATION-STABLE`, runtime generation FASE 29.4.2. Real state: CP-40A-POST-RELEASE-SLO-DRIFT-WATCH-01-STABLE. | UPDATE |
| 5 | **OPENCODE.md** | `/OPENCODE.md` | **OUTDATED** | References "CP-24" at bottom. Profile list references qwen2.5-coder-32b (DOWN) and qwen3.6-27b (DESACTIVADO). | UPDATE |
| 6 | **docs/ARCHITECTURE.md** | `docs/ARCHITECTURE.md` | **OBSOLETE** | 51 lines, generic components. Mentions Ollama (not used). No mention of actual architecture layers (precision, governance, validation, federation). | ARCHIVE |
| 7 | **.agent/ARCHITECTURE.md** | `.agent/ARCHITECTURE.md` | **OBSOLETE (AI-LAB)** | Describes generic "Antigravity Kit" — 20 generic agents, 36 skills. Not AI-LAB runtime architecture. | KEEP (agent layer) |
| 8 | **.agent/rules/GEMINI.md** | `.agent/rules/GEMINI.md` | **OBSOLETE (AI-LAB)** | Generic Antigravity Kit protocol. Agent routing, Socratic Gate, Tiers. Not AI-LAB specific. | KEEP (agent layer) |
| 9 | **WORKTREE_GOVERNANCE.md** | `/WORKTREE_GOVERNANCE.md` | **CURRENT** | Well-maintained. Covers git discipline, state policy, burn-in rules. | KEEP |
| 10 | **.agent/BOOTSTRAP.md** | `.agent/BOOTSTRAP.md` | **PARTIAL** | References OPENCODE.md (exists), .agent/ARCHITECTURE.md (generic). Agent routing guide valid. | KEEP |
| 11 | **.agent/OPENCODE_PROMPT.md** | `.agent/OPENCODE_PROMPT.md` | **PARTIAL** | Mixed AI-LAB specific instructions with generic. Architecture evidence protocol is specific. | KEEP |
| 12 | **AI-LAB — HITO CONSOLIDADO.md** | `/AI-LAB — HITO CONSOLIDADO.md` | **ARCHIVE** | Dated 14 May 2026. Historical milestone snapshot. | ARCHIVE |
| 13 | **AI-LAB-ARCHITECTURE-AND-OPERATIONS.md.txt** | Root | **ARCHIVE** | Legacy text dump. No date. | ARCHIVE |
| 14 | **AI-LAB — Arquitectura y Manual Operacional.odt** | Root | **ARCHIVE** | ODT binary, legacy. | ARCHIVE |
| 15 | **Core Infrastructure IALAB.odt** | Root | **ARCHIVE** | ODT binary, legacy. | ARCHIVE |
| 16 | **README.odt** | Root | **ARCHIVE** | ODT binary, legacy. | ARCHIVE |
| 17 | **plataforma cognitiva distribuida.odt** | Root | **ARCHIVE** | ODT binary, legacy. | ARCHIVE |
| 18 | **docs/ARCHITECTURE-PHASE8.md** | `docs/` | **ARCHIVE** | Phase 8 specific, legacy naming. | ARCHIVE |
| 19 | **docs/ARQUITECTURA_PUBLICO_PRIVADO.md** | `docs/` | **UNKNOWN** | Not read. Spanish title suggests hybrid infra doc. | REVIEW |
| 20 | **docs/RUNTIME-FLOW.md** | `docs/` | **UNKNOWN** | Not read. Possibly outdated. | REVIEW |
| 21 | **docs/INFRASTRUCTURE.md** | `docs/` | **UNKNOWN** | Not read. Possibly partially current. | REVIEW |
| 22 | **docs/architecture/ASTRO-DEPLOYMENT-GOVERNANCE.md** | `docs/architecture/` | **CURRENT** | Referenced by AGENTS.md as canonical for web surfaces. | KEEP |
| 23 | **docs/audits/** (135 files) | `docs/audits/` | **DUPLICATED/ARCHIVE** | Historical audit trail. 135 files. Many superseded. Should be reorganized into archive/ with index. | REORGANIZE |
| 24 | **reports/** (5 files) | `/reports/` | **CURRENT** | Session reports from July 1, 2026. Operational evidence. | KEEP |
| 25 | **.agent/agents/** (30 files) | `.agent/agents/` | **PARTIAL** | Generic Antigravity Kit agents. Some have AI-LAB specific rules (runtime-core, governance, observability). | KEEP |
| 26 | **.agent/workflows/** (11 files) | `.agent/workflows/` | **PARTIAL** | Generic workflow templates. | KEEP |
| 27 | **scripts/** (6 entries) | `/scripts/` | **CURRENT** | Runtime scripts (backup, gitnexus-health, phase-closure). | KEEP |

---

## Repository Health

### Git State

| Metric | Value |
|--------|-------|
| Total tags | 39 |
| Current HEAD | `665af5e9` (docs audit) |
| Branch | `main` |
| Ahead of origin/main | 3 commits |
| Behind origin/main | 160 commits |
| Uncommitted changes | 10 files (MCP tools + semantic gateway + tests) |
| Real commits behind (non-metrics) | 4 commits |
| Metrics-only behind | 156 commits |

### Tags Sequence (oldest → newest)

```
phase-1-stable → phase-2-stable → phase-2-gpu-telemetry → phase-3-grounded-opencode-runtime →
phase-4-opencode-router-live → phase-5-cognitive-agent-router → phase-6-weighted-intent-routing →
phase-6-distributed-cognition-v1 → phase8-cognitive-observability-stable →
phase12-supervised-self-optimization → CP-21B-STABLE → CP-22B-STABLE →
CP-23A-FOUNDATION → CP-23A-MEMORY-SAFE → CP-23A-MODEL-ALIAS-FIX → CP-23B-QUALITY-GATE →
CP-23B-RECALL-STABILITY → CP-24-ANALYTICS → CP-25-OPENCODE-PRODUCTION →
CP-26-OPENWEBUI-PRODUCTION → CP-26.1-OBSERVABILITY-v2 → CP-26.1.1-COMPLETION-FINALIZATION-FIX →
CP-26.1.2-REPORT-ROUTING-FIX → CP-26.2-UX-COGNITIVE-QUALITY → CP-27-RUNTIME-STABILIZATION →
CP-38A-RUNTIME-DEEP-AUDIT-01-STABLE → CP-38B-GATEWAY-SHUTDOWN-GRACEFUL-01-STABLE →
CP-38C-GITNEXUS-NAPI-ERROR-TRIAGE-01-STABLE → CP-38D-RUNTIME-STABILITY-SNAPSHOT-01-STABLE →
CP-39A-OPENCODE-GATEWAY-CONTRACT-HARDENING-01-STABLE →
CP-39B-RUNTIME-OBSERVABILITY-ALERTS-01-STABLE →
CP-39C-COGNITIVE-HEALTH-FOLLOWUP-01-STABLE →
CP-39E-RUNTIME-STABILIZATION-RELEASE-CLOSE-01-STABLE →
CP-40A-POST-RELEASE-SLO-DRIFT-WATCH-01-STABLE →
CP-DOC-AUTOMATION-STABLE → CP-DOCS-AILAB-MCP-INFRASTRUCTURE-UPDATE-01-STABLE →
CP-DOCS-ASTRO-ARCHITECTURE-UPDATE-01-STABLE → CP-MCP-OPENCODE-WINDOWS-CONNECTION-01-STABLE →
CP-MCP-SEMANTIC-GATEWAY-01-STABLE
```

**Missing from local:** Tags CP-28.x through CP-36B are NOT present as tags (they exist as code but were never tagged). The conversation-history.md mentions them but they lack git tags.

### Critical Git Issue

This workspace and the .30 runtime have **diverged git histories** for Block 37:

| Source | Block 37 commits | Status |
|--------|-----------------|--------|
| This workspace | `665af5e`, `10ebf51`, `c8692cc`, `60d501c` | 3 ahead, PUSHED TO ORIGIN? NO |
| .30 runtime (origin) | `31b5bd59`, `8c6f92d`, `00ef680d`, `62ce126d` | Pushed to origin, deployed |
| Code deployed on .30 | Weighted scoring with `structural_health_score: 48.0` | VERIFIED via /runtime/precision/evidence |

The 37D code change is the SAME (weighting formula), but the commit history diverged. This workspace has the code change in `60d501c`, .30 has it in `00ef680d`.

---

## Workspace Alignment

| Check | Result | Detail |
|-------|--------|--------|
| Same git remote? | YES | Both point to `https://github.com/albertgracia/ai-lab.git` |
| Same HEAD? | NO | Workspace: `665af5e9`, .30: `31b5bd59` (on origin/main) |
| 37D code deployed? | YES (.30), NOT DEPLOYED (workspace) | .30 has weighted scoring live |
| Uncommitted MCP changes? | YES | 10 files modified in workspace (MCP tools + gateway) |
| Runtime health score 0.0? | YES (pre-existing bug) | Not related to 37D |
| Documentation drift? | SEVERE | conversation-history.md 30+ phases behind |

---

## Roadmap Consistency

The **real** roadmap recovered from git tags and .30 runtime state:

```
Phase numbering divergence: The CP tag sequence has a GAP between CP-27 and CP-38A.
Blocks 28.x through 36B were never tagged (code exists but no git checkpoint).

CP-27-RUNTIME-STABILIZATION
↓ (untagged: 28.x, 29.x, 30A-G, 30H, 30I, 31B, 31C, 31E, 31D, 32A, 32B, 33A, 33B, 28.4, 35C, 35D, 36A, DEV-36X, DOC-36X, 35D-HF1, 36B)
↓ CP-36C-A (validation score investigation - docs audit)
↓ CP-37A (cognitive health layer - docs audit)
↓ CP-PC-01 (phase closure protocol - docs audit)
↓ 37B (validation authority recovery - on .30)
↓ 37C (codebase health analysis - on .30)
↓ CP-37D (structural health scoring - DEPLOYED on .30)
↓ 37E (test portability - on .30)
↓ CP-38A (runtime deep audit)
↓ CP-38B (gateway shutdown graceful)
↓ CP-38C (gitnexus napi error triage)
↓ CP-38D (runtime stability snapshot)
↓ CP-39A (opencode gateway contract hardening)
↓ CP-39B (runtime observability alerts)
↓ CP-39C (cognitive health followup)
↓ CP-39E (runtime stabilization release close)
↓ CP-40A (post-release SLO drift watch)
↓
[Next: Hermes → Operator Intent → Autonomous Observability Triage → 
 Validation Authority → Multi-GPU → Marketplace → AnythingLLM → Cloudflare Workers AI]
```

**Note:** The gap between CP-27 and CP-38A represents ~15 phases (28.x through 36B) that were implemented but never tagged. Their code exists in runtime/ but there are no git checkpoint tags for them.

---

## Architecture Consistency

| Document | AI-LAB Architecture Coverage | Verdict |
|----------|------------------------------|---------|
| AGENTS.md | Detailed (1092 lines). Covers: routing, SLO, profiles, models, observability, precision, governance. Missing Block 37-40 updates. | BEST SINGLE SOURCE |
| docs/ARCHITECTURE.md | 51 lines, generic. Mentions Ollama (not used). | OBSOLETE |
| .agent/ARCHITECTURE.md | Antigravity Kit (agent routing), not AI-LAB architecture. | NOT APPLICABLE |
| docs/architecture/ASTRO-DEPLOYMENT-GOVERNANCE.md | Specific to Astro/Cloudflare deployment. | CURRENT |

**Conclusion:** AGENTS.md IS the de-facto architecture document. No other architecture file comes close.

---

## Bootstrap Consistency

The bootstrap chain in `.agent/BOOTSTRAP.md` prioritizes:

```
1. OPENCODE.md → EXISTS (stale, CP-24 reference)
2. .agent/ARCHITECTURE.md → EXISTS (generic Antigravity Kit, not AI-LAB)
3. .agent/rules/GEMINI.md → EXISTS (generic Antigravity Kit rules)
4-7. agents/ → skills/ → workflows/ → memory/semantic/
```

**Issue:** Step 2 references `.agent/ARCHITECTURE.md` which is generic Antigravity Kit, not AI-LAB runtime. An agent new to AI-LAB following this chain would get zero AI-LAB context until step 4 (agents/).

**Recommendation:** Add AI-LAB-specific bootstrap reference before or after the Antigravity chain.

---

## Agent Rules Consistency

The `.agent/agents/` directory contains 30 agent files. These are a mix of:
- **Generic Antigravity Kit agents** (20 standard: frontend-specialist, backend-specialist, etc.)
- **AI-LAB specific agents** (10: runtime-core, governance, observability, incidents, authority, contracts, semantic, gitnexus, astro-docs, infra)

The AI-LAB specific agents have contextualized instructions. The generic ones may not be AI-LAB aware.

**Issue:** No clear separation between generic and AI-LAB agents. An agent loading `backend-specialist` would get zero AI-LAB context.

---

## Operational Documentation

| Item | Status | Detail |
|------|--------|--------|
| AGENTS.md procedures | CURRENT | Verify health, restart services, burn-in, debug metrics, memory injection, uvicorn rogue |
| /reports/ (5 files) | CURRENT | July 1, 2026 session reports |
| WORKTREE_GOVERNANCE.md | CURRENT | Git discipline, state policy, burn-in rules |
| scripts/ | CURRENT | backup, gitnexus-health, phase-closure |

---

## Historical Documentation

| File | Type | Verdict |
|------|------|---------|
| AI-LAB — HITO CONSOLIDADO.md | Historic milestone (May 14) | ARCHIVE |
| AI-LAB-ARCHITECTURE-AND-OPERATIONS.md.txt | Legacy text dump | ARCHIVE |
| AI-LAB — Arquitectura y Manual Operacional.odt | ODT binary | ARCHIVE |
| Core Infrastructure IALAB.odt | ODT binary | ARCHIVE |
| README.odt | ODT binary | ARCHIVE |
| plataforma cognitiva distribuida.odt | ODT binary | ARCHIVE |
| docs/ARCHITECTURE-PHASE8.md | Phase 8 specific | ARCHIVE |
| docs/ARQUITECTURA_PUBLICO_PRIVADO.md | Pre-2026 architecture | REVIEW |
| docs/RUNTIME-FLOW.md | Pre-2026 flow | REVIEW |
| docs/ROADMAP.md | 4-phase generic | ARCHIVE |
| docs/ARCHITECTURE.md | 51-line generic | ARCHIVE |

---

## Duplicate Documentation

| Topic | Files | Action |
|-------|-------|--------|
| Architecture | AGENTS.md (1092 lines) vs docs/ARCHITECTURE.md (51 lines) vs .agent/ARCHITECTURE.md (288 lines, generic) | AGENTS.md wins. Archive others. |
| Roadmap | AGENTS.md roadmap section vs docs/ROADMAP.md vs ROADMAP.md (missing at root) | AGENTS.md wins. Archive docs/ROADMAP.md. |
| Bootstrap | .agent/BOOTSTRAP.md (95 lines) vs .agent/OPENCODE_PROMPT.md (126 lines) vs OPENCODE.md (24 lines) | All serve different purposes. KEEP all but clarify hierarchy. |
| Audits | 135 audit files in docs/audits/ | REORGANIZE into archive/ with index |

---

## Archive Candidates

| File | Reason |
|------|--------|
| AI-LAB — HITO CONSOLIDADO.md | Historic snapshot (May 14, 2026) |
| AI-LAB-ARCHITECTURE-AND-OPERATIONS.md.txt | Legacy text dump |
| AI-LAB — Arquitectura y Manual Operacional.odt | ODT binary, superseded by AGENTS.md |
| Core Infrastructure IALAB.odt | ODT binary, legacy |
| README.odt | ODT binary, legacy |
| plataforma cognitiva distribuida.odt | ODT binary, legacy |
| docs/ROADMAP.md | 4-phase generic, superseded |
| docs/ARCHITECTURE.md | 51-line generic, superseded by AGENTS.md |
| docs/ARCHITECTURE-PHASE8.md | Phase 8 specific, legacy |
| docs/audits/* (135 files) | Move to docs/archive/audits/ |

---

## Missing Documentation

| Topic | Required | Priority |
|-------|----------|----------|
| ROADMAP-2026.md | Recovered roadmap aligned with real CP tags | HIGH |
| conversation-history.md update | Current HEAD, tags, phases through CP-40A | HIGH |
| AGENTS.md update | Add Blocks 37-40 completion | HIGH |
| README.md update | Current checkpoint (CP-40A range) | MEDIUM |
| OPENCODE.md update | Current profile routing truth | MEDIUM |

---

## Final Answers

### 1. Where is AI-LAB today?

**Runtime:** CP-40A-POST-RELEASE-SLO-DRIFT-WATCH-01-STABLE (deployed on 192.168.1.30)
**This workspace:** HEAD at `665af5e9` — 160 commits behind origin/main, 3 ahead. Block 37 work diverged from .30 runtime.
**Last deployed phase on .30:** 37D (structural health scoring) verified LIVE with score 48.0. Tags up to CP-40A exist on origin but some gap between CP-27 and CP-38A (untagged phases 28.x-36B).

### 2. What documentation is authoritative?

- **AGENTS.md** — Best single source for AI-LAB operational knowledge (CURRENT up to CP-36B)
- **WORKTREE_GOVERNANCE.md** — Git discipline and state policy (CURRENT)
- **docs/architecture/ASTRO-DEPLOYMENT-GOVERNANCE.md** — Web surface deployment (CURRENT)
- **.agent/BOOTSTRAP.md** — Agent entry point and routing (PARTIAL)
- **runtime/code/** — Ultimate source of truth (per SOURCE OF TRUTH priority)

### 3. What documentation is obsolete?

- **conversation-history.md** — 30+ phases behind, wrong tag count (63 vs 39), wrong HEAD
- **README.md** — Claims CP-29.4.2, real state is CP-40A
- **docs/ROADMAP.md** — 4 generic phases, no relation to reality
- **docs/ARCHITECTURE.md** — 51 lines, mentions Ollama (not used)
- **OPENCODE.md** — References CP-24 at bottom

### 4. Which files should be archived?

- All 6 ODT/text legacy files at root → `docs/archive/`
- `docs/ROADMAP.md` → `docs/archive/roadmap-legacy.md`
- `docs/ARCHITECTURE.md` → `docs/archive/architecture-legacy.md`
- `docs/ARCHITECTURE-PHASE8.md` → `docs/archive/`
- `AI-LAB — HITO CONSOLIDADO.md` → `docs/archive/`
- `AI-LAB-ARCHITECTURE-AND-OPERATIONS.md.txt` → `docs/archive/`
- 135 audit files in `docs/audits/` → `docs/archive/audits/` (with INDEX.md)

### 5. Which files should be merged?

- No files need merging. The issue is hierarchy and classification, not content overlap.

### 6. Which files require immediate update?

| Priority | File | Action |
|----------|------|--------|
| HIGH | conversation-history.md | Full rewrite: current HEAD (665af5e9), 39 tags, CP-40A chain |
| HIGH | AGENTS.md | Add Blocks 37-40 to phase list and roadmap |
| HIGH | `ROADMAP-2026.md` (NEW) | Create with recovered real roadmap |
| MEDIUM | README.md | Update checkpoint to CP-40A |
| MEDIUM | OPENCODE.md | Update profile truth |
| LOW | docs/ARCHITECTURE.md | Archive (replace with pointer to AGENTS.md) |
| LOW | docs/ROADMAP.md | Archive (replace with pointer to ROADMAP-2026.md) |

### 7. What should become the official documentation hierarchy?

```
ROOT/
├── AGENTS.md ← REPLACES ROADMAP.md + PARTIAL ARCHITECTURE + WORKSPACE RULES
│
├── ROADMAP-2026.md (NEW) ← Recovered real checkpoint chain from git tags
│
├── .agent/
│   ├── BOOTSTRAP.md ← Agent entry point + routing
│   ├── OPENCODE_PROMPT.md ← Agent behavior (AI-LAB specific)
│   ├── ARCHITECTURE.md ← CURRENT (generic Antigravity Kit — NOT AI-LAB arch)
│   ├── agents/ ← 30 specialist agents (10 AI-LAB specific)
│   ├── workflows/ ← 11 workflow files
│   └── rules/GEMINI.md ← Universal agent rules
│
├── docs/
│   ├── architecture/
│   │   └── ASTRO-DEPLOYMENT-GOVERNANCE.md ← Canonical web surface doc
│   ├── governance/
│   │   └── phase-closure-protocol.md ← Phase closure procedure
│   ├── operations/ ← Runbooks, procedures, operational docs
│   ├── roadmap/ ← ROADMAP-2026.md + future roadmap docs
│   ├── runbooks/ ← Operational runbooks
│   ├── integrations/ ← AnythingLLM, Qdrant, Cloudflare, etc.
│   └── archive/
│       ├── audits/ ← Historical audit trail (135 files) + INDEX.md
│       └── legacy/ ← Old architecture/roadmap/consolidated docs
│
├── reports/ ← Session reports (operational evidence)
│
└── runtime/ ← Code (source of truth)
    ├── gateway/
    ├── precision/
    ├── governance/
    ├── validation/
    ├── codebase/
    └── ...
```

### 8. Is the OpenCode workspace synchronized with the runtime repository?

**NO.** Critical divergence:

| Aspect | Workspace (E:\opencode\ai-lab) | Runtime (.30: /opt/ai-lab) |
|--------|-------------------------------|---------------------------|
| HEAD | `665af5e9` | `31b5bd59` (origin/main) |
| Ahead of origin | 3 commits | 0 commits |
| Behind origin | 160 commits | 0 commits |
| 37D deployed? | Code exists but commit not pushed | YES (verified live) |
| MCP changes | 10 uncommitted files | Different set of MCP changes |

### 9. Can AI-LAB documentation become the official Source of Truth?

**Not yet.** The documentation is fragmented across multiple files with conflicting information. AGENTS.md is the closest to being authoritative (covers up to CP-36B), but needs:
- Blocks 37-40 phase completion data
- Current roadmap replacing the stale "Próxima fase: 37B" section
- Alignment with .30 runtime's actual deployed state (CP-40A)
- Archive of superseded docs
- Updated conversation-history.md

Once these 5 actions are completed, AGENTS.md + ROADMAP-2026.md + WORKTREE_GOVERNANCE.md can become the Source of Truth.

### 10. Prioritized execution plan

**Phase A — Critical (HIGH impact, low effort):**
1. Update conversation-history.md (current HEAD, 39 tags, CP-40A chain)
2. Create ROADMAP-2026.md (recovered from git tags)
3. Archive root ODT/text legacy files to docs/archive/legacy/
4. Archive docs/ROADMAP.md, docs/ARCHITECTURE.md, docs/ARCHITECTURE-PHASE8.md

**Phase B — Documentation Update (MEDIUM impact, medium effort):**
5. Update AGENTS.md phase list (add Blocks 37-40)
6. Update AGENTS.md roadmap section (replace "Próxima fase: 37B" with real chain)
7. Update README.md checkpoint to CP-40A
8. Update OPENCODE.md (remove CP-24 reference, update profile list)

**Phase C — Audit Reorganization (LOW impact, high effort):**
9. Create docs/archive/audits/INDEX.md categorizing 135 files
10. Move docs/audits/ to docs/archive/audits/
11. Remove duplicate docs that have clear successors

**Phase D — Workspace Alignment (MEDIUM impact, needs authorization):**
12. Resolve 160-behind gap (git pull/rebase)
13. Resolve 3-ahead divergence (merge or abandon duplicate commits)
14. Commit/push uncommitted MCP changes or reset them
15. Verify workspace matches .30 runtime state
