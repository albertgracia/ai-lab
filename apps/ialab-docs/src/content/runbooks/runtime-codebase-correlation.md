---
title: "Runtime-Codebase Correlation"
summary: "Procedimiento para correlacionar métricas de runtime con estructura del codebase usando los tres truth layers."
severity: "info"
---


## Propósito

Cruzar métricas operacionales del runtime con datos estructurales de la codebase para identificar causas raíz y alcance del impacto.

## Pasos

### 1. Identificar señal del runtime

Desde un dashboard de Grafana o un reporte de incidentes, identificar una métrica anómala:

```bash
curl -s http://192.168.1.30:8008/metrics | grep "ailab_governance_blocked_total"
```

### 2. Mapear al dominio de codebase

El prefijo de la métrica indica el dominio (ej., `governance` → `runtime/governance/`).

### 3. Verificar blast radius del módulo

```bash
curl -s "http://192.168.1.30:8008/runtime/codebase/blast-radius?module_path=governance" | jq .
```

### 4. Verificar ownership

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/ownership | jq '.domains[] | select(.domain == "governance")'
```

### 5. Verificar riesgos estructurales

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/risks | jq '.risks[] | select(.domain == "governance")'
```

### 6. Correlacionar

| Si el runtime muestra | Y la codebase muestra | Conclusión |
|---|---|---|
| governance_blocked > 0 | governance reverse_coupling alto | Cambio en hub de governance — probar todos los dependientes |
| validation score < 50 | validation wide blast radius | Cambio en validation en cascada — verificar upstream |
| observability stale | observability coupling bajo | Issue aislado de observability — fix seguro |

### 7. Generar reporte cross-layer

```bash
curl -s http://192.168.1.30:8008/runtime/report/codebase | jq .
```

### 8. Documentar

Registrar el hallazgo de correlación en el incidente o change log correspondiente.
