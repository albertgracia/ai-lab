---
title: "Incident-to-Module Analysis"
summary: "Procedimiento para correlacionar incidentes activos con módulos del codebase afectados, usando GitNexus blast radius y ownership."
severity: "high"
---

# Incident-to-Module Analysis

## Purpose

Map runtime incidents to source code modules using codebase structural data, enabling targeted remediation.

## Steps

### 1. Get active incidents

```bash
curl -s http://192.168.1.30:8008/runtime/incidents | jq '.active_incidents[] | {incident_id, primary_domain, severity, title}'
```

### 2. For each incident, map domain to codebase

Using `OWNERSHIP_DOMAINS` mapping:

| Incident domain | Codebase module path |
|---|---|
| authority | `runtime/authority/` |
| governance | `runtime/governance/` |
| validation | `runtime/validation/` |
| observability | `runtime/observability/` |

### 3. Check blast radius

```bash
curl -s "http://192.168.1.30:8008/runtime/codebase/blast-radius?module_path=<domain>" | jq '.results[] | {module_path, total_impacted, severity}'
```

### 4. Check if module is a hotspot

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/topology | jq '.hotspots'
```

### 5. Determine remediation priority

| Incident severity | Blast radius | Hotspot | Priority |
|---|---|---|---|
| critical | high | yes | IMMEDIATE |
| high | high | yes | HIGH |
| high | medium | no | MEDIUM |
| medium | low | no | LOW |

### 6. Plan fix

- If hotspot + wide blast: staged fix with integration tests
- If low blast: direct fix, unit tests sufficient
- If high reverse coupling: interface-compatible fix only

### 7. Verify after fix

```bash
# Re-check structural health
curl -s http://192.168.1.30:8008/runtime/codebase/score | jq '.score.structural_health_score'

# Re-check incidents
curl -s http://192.168.1.30:8008/runtime/incidents | jq '.incident_count'
```

### 8. Close incident

Confirm remediation in the incident tracker and update related runbooks if applicable.
