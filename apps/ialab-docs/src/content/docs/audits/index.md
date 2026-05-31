---
title: "Audits"
summary: "Curated audit index for AI-LAB architecture, operations, observability and governance reports."
order: 1
---

This page provides a curated summary of all AI-LAB audits. It does not replicate the full reports. The original technical documents remain in `docs/audits/` at the repository root.

## Executive Summary

| Category | Count | Description |
|----------|-------|-------------|
| Public summaries (A) | 9 | Reports suitable for documentation reference |
| Referencible (B) | 7 | Operational reports linked from this index |
| Internal only (C) | 12 | Technical reports maintained outside Starlight |
| Sanitized candidates (D) | 0 | None identified |

**Total audits inventoried: 28**

## Public Reports (Category A)

Reports related to documentation architecture, observability recovery, and runtime summaries. Suitable for general reference.

| Report | Theme | Summary |
|--------|-------|---------|
| AI-LAB-ASTRO-CONSOLIDATION-PHASES-01-MANIFEST.md | Documentation | Manifest of 43 historical phase documents consolidated into `historical/phases/` |
| AI-LAB-ASTRO-CONSOLIDATION-PHASES-01.md | Documentation | Execution report of the consolidation phase (43 files moved, 3 links fixed) |
| AI-LAB-ASTRO-DOCUMENTATION-CLEANUP-APPLY-01.md | Documentation | Cleanup execution: 7 archived, 1 quarantined |
| AI-LAB-ASTRO-DOCUMENTATION-CLEANUP-PLAN-01.md | Documentation | Cleanup plan with 30 actions across 5 categories |
| AI-LAB-ASTRO-DOCUMENTATION-INVENTORY-01.md | Documentation | Full inventory of 307 documentation files |
| AI-LAB-ASTRO-INFORMATION-ARCHITECTURE-01.md | Documentation | Information architecture blueprint with 6 target sections |
| AI-LAB-ASTRO-SIDEBAR-REALIGNMENT-01.md | Documentation | Sidebar realignment to 5-section structure |
| AI-LAB-OBSERVABILITY-RECOVERY-SUMMARY-01.md | Observability | Multi-phase recovery summary covering 4 observability phases |
| RUNTIME-DEEP-AUDIT-01-SUMMARY.md | Runtime | Executive summary of runtime deep audit |

## Referencible Reports (Category B)

Operational reports with detailed technical content. Referenced here for discoverability but maintained in `docs/audits/`.

| Report | Theme | Description |
|--------|-------|-------------|
| AI-LAB-DASHBOARD-DRIFT-AUDIT-01.md | Observability | Drift audit of 5 Grafana dashboards (156 panels, 134 PromQL queries) |
| AI-LAB-GRAFANA-PROVISIONING-VALIDATION-01.md | Observability | Validation of Grafana provisioning configuration |
| AI-LAB-HEALTH-SCORE-DASHBOARD-ALIGNMENT-01.md | Observability | Alignment of health score dashboards with SLO definitions |
| AI-LAB-HEALTH-SCORE-DRIFT-RULE-01.md | Observability | Drift detection rule for health score metrics |
| AI-LAB-HEALTH-SCORE-SOURCE-OF-TRUTH-01.md | Observability | Source of truth definition for health score computation |
| AI-LAB-PROMETHEUS-RUNTIME-HEALTH-RECORDING-RULE-01.md | Observability | Prometheus recording rules for runtime health |
| AI-LAB-PROMETHEUS-RUNTIME-HEALTH-RECORDING-RULE-FIX-01.md | Observability | Fix for recording rule PromQL issues |

## Internal-Only Reports (Category C)

The following 12 reports contain operational triage, incident details, release tracking, and infrastructure-specific data. They are maintained exclusively in `docs/audits/` and are not exposed through this documentation site.

- GITNEXUS-EXECSTARTPRE-NAPI-ERROR-TRIAGE-01.md
- GITNEXUS-GOVERNED-RUNTIME-CHANGE-POLICY-01.md
- INCIDENTS-GOVERNANCE-SCHEMA-01.md
- INCIDENTS-WATCHDOG-DEDUP-01.md
- MEMORY-INJECTION-QDRANT-PERSISTENCE-FIX-01.md
- MEMORY-INJECTION-TELEMETRY-01.md
- QDRANT-MEMORY-GOVERNANCE-POLICY-01.md
- POST-RELEASE-SLO-DRIFT-WATCH-40A.md
- RELEASE-CLOSE-39E.md
- RUNTIME-DEEP-AUDIT-01.md
- RUNTIME-STABILITY-SNAPSHOT-01.md
- RUNTIME-STABILITY-SNAPSHOT-38D.md

## Maintenance Policy

- Operational audits live in `docs/audits/` at the repository root.
- Starlight maintains only this curated index page.
- Full reports must not be copied into `src/content/docs/audits/` without prior sensitivity review.
- New audits should be classified (A/B/C/D) before being added to this index.
- Category C reports exist but are not detailed here by policy.
