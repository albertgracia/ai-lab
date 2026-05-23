---
title: "Blast Radius Review"
summary: "Procedimiento para revisar el blast radius de módulos del runtime antes de planificar cambios o priorizar refactors."
severity: "medium"
---

# Blast Radius Review

## Propósito

Identificar qué módulos del runtime tienen el radio de impacto más amplio para priorizar refactoring, testing y atención de governance.

## Pasos

### 1. Obtener todos los resultados de blast radius

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/blast-radius | jq '.results[] | select(.severity == "high")'
```

### 2. Revisar módulos de severidad alta

Para cada módulo con `severity == "high"`:

- `module_path`: ubicación del módulo
- `total_impacted`: cuántos módulos están afectados transitivamente
- `affected_domains`: dominios operacionales alcanzados

### 3. Cruzar con riesgos estructurales

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/risks | jq '.risks[] | select(.risk_type == "wide_blast_radius")'
```

### 4. Verificar hotspots

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/topology | jq '.hotspots'
```

### 5. Priorizar

| Condición | Acción |
|---|---|
| blast radius alto + hotspot | Prioridad máxima — planificar refactor guiado |
| blast radius alto solamente | Prioridad alta — aumentar cobertura de tests |
| reverse coupling alto | Prioridad media — revisar estabilidad de interfaces |
| blast radius bajo + coupling bajo | Prioridad baja — seguro de cambiar |

### 6. Documentar

Registrar los hallazgos en la documentación de fase correspondiente. Actualizar los dominios afectados en la domain dependency matrix.
