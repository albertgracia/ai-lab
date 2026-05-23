---
title: "Incident-to-Module Analysis"
summary: "Procedimiento para correlacionar incidentes activos con módulos del codebase afectados, usando GitNexus blast radius y ownership."
severity: "high"
---

# Incident-to-Module Analysis

## Propósito

Mapear incidentes del runtime a módulos de código fuente usando datos estructurales de la codebase, permitiendo remediación dirigida.

## Pasos

### 1. Obtener incidentes activos

```bash
curl -s http://192.168.1.30:8008/runtime/incidents | jq '.active_incidents[] | {incident_id, primary_domain, severity, title}'
```

### 2. Para cada incidente, mapear dominio a codebase

Usando el mapping de `OWNERSHIP_DOMAINS`:

| Dominio del incidente | Ruta del módulo en codebase |
|---|---|
| authority | `runtime/authority/` |
| governance | `runtime/governance/` |
| validation | `runtime/validation/` |
| observability | `runtime/observability/` |

### 3. Verificar blast radius

```bash
curl -s "http://192.168.1.30:8008/runtime/codebase/blast-radius?module_path=<dominio>" | jq '.results[] | {module_path, total_impacted, severity}'
```

### 4. Verificar si el módulo es un hotspot

```bash
curl -s http://192.168.1.30:8008/runtime/codebase/topology | jq '.hotspots'
```

### 5. Determinar prioridad de remediación

| Severidad del incidente | Blast radius | Hotspot | Prioridad |
|---|---|---|---|
| critical | alto | sí | INMEDIATA |
| high | alto | sí | ALTA |
| high | medio | no | MEDIA |
| medium | bajo | no | BAJA |

### 6. Planificar fix

- Si hotspot + wide blast: fix por fases con integration tests
- Si blast bajo: fix directo, unit tests suficientes
- Si high reverse coupling: fix solo compatible con interfaz existente

### 7. Verificar después del fix

```bash
# Re-verificar salud estructural
curl -s http://192.168.1.30:8008/runtime/codebase/score | jq '.score.structural_health_score'

# Re-verificar incidentes
curl -s http://192.168.1.30:8008/runtime/incidents | jq '.incident_count'
```

### 8. Cerrar incidente

Confirmar la remediación en el tracker de incidentes y actualizar los runbooks relacionados si aplica.
