---
title: "Safe Refactor Workflow"
summary: "Procedimiento para refactorizar código del runtime usando GitNexus blast radius y structural risk analysis antes de hacer cambios."
severity: "high"
---


## Propósito

Antes de modificar cualquier módulo del runtime, verificar blast radius, reverse coupling y riesgos estructurales para evitar roturas inesperadas.

## Prerrequisitos

- Gateway operativo (`curl -s http://192.168.1.30:8008/health`)
- Endpoints de codebase memory respondiendo

## Pasos

### 1. Identificar el módulo objetivo

```
TARGET_MODULE="governance"
```

### 2. Verificar blast radius

```bash
curl -s "http://192.168.1.30:8008/runtime/codebase/blast-radius?module_path=${TARGET_MODULE}" | jq .
```

Revisar:
- `total_impacted`: a cuántos módulos se propaga el cambio
- `affected_domains`: qué dominios operacionales están afectados
- `severity`: baja/media/alta

### 3. Verificar reverse coupling

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/risks | jq ".risks[] | select(.details.module == \"${TARGET_MODULE}\")"
```

Si `risk_type == "high_reverse_coupling"`:
- El módulo es importado por 5+ otros módulos
- Los cambios requieren pruebas de todos los dependientes

### 4. Verificar salud estructural

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/score | jq .
```

Si `level == "critical"` (< 50):
- Proceder con precaución extra
- Ejecutar validation gate completo después del cambio

### 5. Verificar invariantes antes del cambio

```bash
curl -s http://192.168.1.30:8008/runtime/validation/invariants | jq '.invariants[] | select(.name | startswith("INVARIANT-CODEBASE"))'
```

### 6. Hacer el cambio

- Pequeño, reversible, de un solo propósito
- Mantener patrones y convenciones existentes

### 7. Re-verificar después del cambio

```bash
curl -s "http://192.168.1.30:8008/runtime/codebase/summary" | jq '.score'
```

Comparar `structural_health_score` con el valor pre-cambio. Una caída > 10 puntos indica regresión estructural.

### 8. Ejecutar tests

```bash
python3 -m pytest tests/ -k "codebase" -v
```

### 9. Verificar invariantes

```bash
curl -s http://192.168.1.30:8008/runtime/validation/invariants | jq '.failures[] | select(.blocking)'
```

## Rollback

Si los invariantes fallan o el structural health baja > 20 puntos:

```bash
git checkout -- <archivos modificados>
git status --short
```

Re-verificar que el health score retorna al valor pre-cambio.
