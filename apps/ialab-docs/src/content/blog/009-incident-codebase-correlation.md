---
title: "How AI-LAB Correlates Runtime Incidents with Source Code"
date: "2026-05-23"
summary: "AI-LAB bridges runtime incidents and codebase structure — mapping operational failures to source modules, blast radius, and ownership domains."
tags:
  - ai-lab
  - incidents
  - codebase
  - correlation
  - runtime
---

# How AI-LAB Correlates Runtime Incidents with Source Code

When a runtime incident fires — say, `INC-AUTHORITY-AUTHORITY-FRESHNESS-...` — the operator needs to know two things:

1. What caused it?
2. What else will it affect?

Before DEV-36X, AI-LAB could answer the first question via its incident intelligence engine (FASE 36A). But the second question required manual code inspection.

Now, incident reports include codebase context automatically.

## The Correlation

Incident intelligence reports (`build_incident_intelligence_summary()`) now include a `codebase` block:

```json
{
  "contract_version": "36A",
  "incidents": {
    "active_incidents_total": 3,
    "highest_severity": "high",
    "affected_domains": ["authority", "governance", "validation"]
  },
  "codebase": {
    "structural_health_score": 45.0,
    "structural_health_level": "critical",
    "modules_total": 62,
    "ownership_domains": 24,
    "hotspots": ["gateway(15)", "governance(12)", "authority(9)"]
  }
}
```

This allows the operator to see: "The authority module is failing, and it's a structural hotspot with 9 reverse dependencies — changes here will impact governance, validation, and reporting."

## How It Works

### Step 1: Codebase Incident Detection

`detect_codebase_incidents()` in `incident_intelligence.py` monitors the codebase structural health score:

```python
if shs < 50:
    # Fire INC-CODEBASE-CODEBASE-HEALTH-LOW
    # severity: critical if < 30, high if < 50

if high_risks > 3:
    # Fire INC-CODEBASE-CODEBASE-HIGH-RISKS
    # severity: high

# Wide blast radius entries
for r in risks_list:
    if r["risk_type"] == "wide_blast_radius":
        # Fire INC-CODEBASE-CODEBASE-WIDE-BLAST-RADIUS
        # severity: medium
```

These incidents merge with other domain incidents through the correlation engine.

### Step 2: Cross-Domain Correlation

If the codebase has a wide blast radius in `governance`, and an `INC-GOVERNANCE-GOVERNANCE-SCORE-LOW` is active, the correlation engine links them:

```python
correlation_results.append({
    "primary_domain": "codebase",
    "correlated_domain": "governance",
    "primary_signals_total": 2,
    "correlated_signals_total": 1,
    "worst_severity": "high",
    "correlation_type": "domain_dependency",
})
```

### Step 3: Enriched Reporting

The reporting engine (`build_incident_intelligence_summary()`) enriches incident data with codebase ownership and hotspots:

```python
codebase_enrichment = {
    "structural_health_score": ...,
    "structural_health_level": ...,
    "ownership_domains": ...,
    "hotspots": ...,
}
```

## Real Scenario

An operator sees this in a report:

```
INCIDENTS: 1 active (highest=high)
  - INC-GOVERNANCE-GOVERNANCE-SCORE-LOW (score: 32/100)
  - BLAST RADIUS: validation, authority, codebase

CODEBASE:
  - structural_health: 45/100 (critical)
  - ownership domains: 24
  - hotspots: gateway(15), governance(12), authority(9)
```

The operator can immediately infer:
- The governance score drop is not isolated — the codebase structural health is already critical
- `governance` is a hotspot with 12 reverse dependencies: fixing governance will also fix validation
- The `gateway` module (15 reverse deps) is the highest-risk module overall

## Cognitive Summary Integration

The cognitive compression engine surfaces codebase health in every runtime summary:

```
codebase: health=45/100 (critical), 62 modules, 274 edges, 4 high risks, 3 hotspots
```

If a wide blast radius exists:

```
wide blast radius: module runtime/governance impacts 12 modules on change
```

## Why This Matters

Without codebase correlation, incidents are isolated events. With it, every incident carries structural context:

- **Severity is contextual**: a governance failure in a module with 12 dependents is worse than the same failure in an isolated module
- **Remediation is guided**: the blast radius tells you what to test after a fix
- **Ownership is clear**: domain mapping tells you who to notify

This is not static documentation. It's live structural cognition — updated every 30 seconds via deterministic AST scanning.
