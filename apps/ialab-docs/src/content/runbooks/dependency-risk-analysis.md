---
title: "Dependency Risk Analysis"
summary: "Análisis de riesgos estructurales del grafo de dependencias del runtime usando GitNexus."
severity: "medium"
---

# Dependency Risk Analysis

## Purpose

Identify structural risks in the runtime dependency graph — high coupling, reverse coupling, and authority dependency spread.

## Steps

### 1. Fetch all structural risks

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/risks | jq '.risks'
```

### 2. Analyze by risk type

#### High Coupling

Modules importing 5+ other modules:

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/risks | jq '.risks[] | select(.risk_type == "high_coupling")'
```

**Implication**: These modules have wide surface area and are sensitive to changes in many upstream modules.

#### High Reverse Coupling

Modules imported by 5+ other modules:

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/risks | jq '.risks[] | select(.risk_type == "high_reverse_coupling")'
```

**Implication**: These modules are structural hubs. Breaking changes propagate to many dependents.

#### Wide Blast Radius

Modules impacting 6+ other modules on change:

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/risks | jq '.risks[] | select(.risk_type == "wide_blast_radius")'
```

**Implication**: High-risk changes. Require comprehensive testing and staged rollout.

### 3. Check domain dependency matrix

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/topology | jq '.domain_dependency_matrix'
```

### 4. Calculate risk score

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/score | jq .
```

### 5. Remediation

| Risk | Remediation |
|---|---|
| High reverse coupling | Stabilize interfaces, reduce public surface |
| High coupling | Abstract dependencies, split module |
| Wide blast radius | Introduce indirection layer, add integration tests |
| Authority spread | Review authority contracts, reduce direct imports |

### 6. Track over time

Compare scores across versions:

```bash
# Before refactor
curl -s http://192.168.1.30:8008/runtime/codebase/score | jq '.score.structural_health_score'

# After refactor
curl -s http://192.168.1.30:8008/runtime/codebase/score | jq '.score.structural_health_score'
```

A sustained improvement of 10+ points validates the refactoring.
