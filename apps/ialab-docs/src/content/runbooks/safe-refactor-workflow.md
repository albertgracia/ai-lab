---
title: "Safe Refactor Workflow"
summary: "Procedimiento para refactorizar código del runtime usando GitNexus blast radius y structural risk analysis antes de hacer cambios."
severity: "high"
---

# Safe Refactor Workflow

## Purpose

Before modifying any runtime module, verify blast radius, reverse coupling, and structural risks to avoid unexpected breakage.

## Prerequisites

- Gateway operational (`curl -s http://192.168.1.30:8008/health`)
- Codebase memory endpoints responding

## Steps

### 1. Identify target module

```
TARGET_MODULE="governance"
```

### 2. Check blast radius

```bash
curl -s "http://192.168.1.30:8008/runtime/codebase/blast-radius?module_path=${TARGET_MODULE}" | jq .
```

Review:
- `total_impacted`: how many modules change propagates to
- `affected_domains`: which operational domains are affected
- `severity`: low/medium/high

### 3. Check reverse coupling

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/risks | jq ".risks[] | select(.details.module == \"${TARGET_MODULE}\")"
```

If `risk_type == "high_reverse_coupling"`:
- Module is imported by 5+ other modules
- Changes require testing of all dependents

### 4. Check structural health

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/score | jq .
```

If `level == "critical"` (< 50):
- Proceed with extra caution
- Run full validation gate after change

### 5. Verify invariants before change

```bash
curl -s http://192.168.1.30:8008/runtime/validation/invariants | jq '.invariants[] | select(.name | startswith("INVARIANT-CODEBASE"))'
```

### 6. Make change

- Small, reversible, single-purpose
- Maintain existing patterns and conventions

### 7. Re-check after change

```bash
curl -s "http://192.168.1.30:8008/runtime/codebase/summary" | jq '.score'
```

Compare `structural_health_score` with pre-change value. A drop > 10 points indicates structural regression.

### 8. Run tests

```bash
python3 -m pytest tests/ -k "codebase" -v
```

### 9. Verify invariants

```bash
curl -s http://192.168.1.30:8008/runtime/validation/invariants | jq '.failures[] | select(.blocking)'
```

## Rollback

If invariants fail or structural health drops > 20 points:

```bash
git checkout -- <changed files>
git status --short
```

Re-verify health score returns to pre-change value.
