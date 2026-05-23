---
title: "Blast Radius Review"
summary: "Procedimiento para revisar el blast radius de módulos del runtime antes de planificar cambios o priorizar refactors."
severity: "medium"
---

# Blast Radius Review

## Purpose

Identify which runtime modules have the widest impact radius to prioritize refactoring, testing, and governance attention.

## Steps

### 1. Fetch all blast radius results

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/blast-radius | jq '.results[] | select(.severity == "high")'
```

### 2. Review high-severity modules

For each module with `severity == "high"`:

- `module_path`: module location
- `total_impacted`: how many modules are transitively affected
- `affected_domains`: operational domains reached

### 3. Cross-reference with structural risks

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/risks | jq '.risks[] | select(.risk_type == "wide_blast_radius")'
```

### 4. Check hotspots

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/topology | jq '.hotspots'
```

### 5. Prioritize

| Condition | Action |
|---|---|
| blast radius high + hotspot | Highest priority — plan guided refactor |
| blast radius high only | High priority — increase test coverage |
| reverse coupling high | Medium priority — review interface stability |
| low blast radius + low coupling | Low priority — safe to change |

### 6. Document

Record findings in the relevant phase documentation. Update affected domains in the domain dependency matrix.
