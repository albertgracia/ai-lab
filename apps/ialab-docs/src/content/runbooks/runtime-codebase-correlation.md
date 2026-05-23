---
title: "Runtime-Codebase Correlation"
summary: "Procedimiento para correlacionar métricas de runtime con estructura del codebase usando los tres truth layers."
severity: "info"
---

# Runtime-Codebase Correlation

## Purpose

Cross-reference runtime operational metrics with codebase structural data to identify root causes and impact scope.

## Steps

### 1. Identify runtime signal

From a Grafana dashboard or incident report, identify an anomalous metric:

```bash
curl -s http://192.168.1.30:8008/metrics | grep "ailab_governance_blocked_total"
```

### 2. Map to codebase domain

The metric prefix indicates the domain (e.g., `governance` → `runtime/governance/`).

### 3. Check module blast radius

```bash
curl -s "http://192.168.1.30:8008/runtime/codebase/blast-radius?module_path=governance" | jq .
```

### 4. Check ownership

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/ownership | jq '.domains[] | select(.domain == "governance")'
```

### 5. Check structural risks

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/risks | jq '.risks[] | select(.domain == "governance")'
```

### 6. Correlate

| If runtime shows | And codebase shows | Conclusion |
|---|---|---|
| governance_blocked > 0 | governance reverse_coupling high | Governance hub change — test all dependents |
| validation score < 50 | validation wide blast radius | Validation change cascading — check upstream |
| observability stale | observability low coupling | Isolated observability issue — safe fix |

### 7. Generate cross-layer report

```bash
curl -s http://192.168.1.30:8008/runtime/report/codebase | jq .
```

### 8. Document

Record the correlation finding in the relevant incident or change log.
