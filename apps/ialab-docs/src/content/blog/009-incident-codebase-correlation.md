---
title: "Cómo AI-LAB Correlaciona Incidentes del Runtime con el Código Fuente"
date: "2026-05-23"
summary: "AI-LAB puentea incidentes del runtime con la estructura del código fuente — mapeando fallos operacionales a módulos, blast radius y dominios de ownership."
tags:
  - ai-lab
  - incidents
  - codebase
  - correlation
  - runtime
---


Cuando se dispara un incidente del runtime — por ejemplo, `INC-AUTHORITY-AUTHORITY-FRESHNESS-...` — el operador necesita saber dos cosas:

1. ¿Qué lo causó?
2. ¿Qué más va a afectar?

Antes de DEV-36X, AI-LAB podía responder la primera pregunta mediante su motor de incident intelligence (FASE 36A). Pero la segunda requería inspección manual del código.

Ahora, los reportes de incidentes incluyen contexto de la codebase automáticamente.

## La Correlación

Los reportes de incident intelligence (`build_incident_intelligence_summary()`) ahora incluyen un bloque `codebase`:

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

Esto permite al operador ver: "El módulo authority está fallando, y es un hotspot estructural con 9 reverse dependencies — los cambios aquí impactarán governance, validation y reporting."

## Cómo Funciona

### Paso 1: Detección de Incidentes en la Codebase

`detect_codebase_incidents()` en `incident_intelligence.py` monitoriza el structural health score:

```python
if shs < 50:
    # Disparar INC-CODEBASE-CODEBASE-HEALTH-LOW
    # severity: critical si < 30, high si < 50

if high_risks > 3:
    # Disparar INC-CODEBASE-CODEBASE-HIGH-RISKS
    # severity: high

# Wide blast radius entries
for r in risks_list:
    if r["risk_type"] == "wide_blast_radius":
        # Disparar INC-CODEBASE-CODEBASE-WIDE-BLAST-RADIUS
        # severity: medium
```

Estos incidentes se fusionan con otros incidentes de dominio a través del motor de correlación.

### Paso 2: Correlación Cross-Domain

Si la codebase tiene un wide blast radius en `governance`, y un `INC-GOVERNANCE-GOVERNANCE-SCORE-LOW` está activo, el motor de correlación los enlaza:

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

### Paso 3: Reporting Enriquecido

El motor de reporting (`build_incident_intelligence_summary()`) enriquece los datos de incidentes con ownership de codebase y hotspots:

```python
codebase_enrichment = {
    "structural_health_score": ...,
    "structural_health_level": ...,
    "ownership_domains": ...,
    "hotspots": ...,
}
```

## Escenario Real

Un operador ve esto en un reporte:

```
INCIDENTS: 1 activo (highest=high)
  - INC-GOVERNANCE-GOVERNANCE-SCORE-LOW (score: 32/100)
  - BLAST RADIUS: validation, authority, codebase

CODEBASE:
  - structural_health: 45/100 (critical)
  - ownership domains: 24
  - hotspots: gateway(15), governance(12), authority(9)
```

El operador puede inferir inmediatamente:
- La caída del governance score no está aislada — el structural health de la codebase ya es crítico
- `governance` es un hotspot con 12 reverse dependencies: arreglar governance también arreglará validation
- El módulo `gateway` (15 reverse deps) es el módulo de mayor riesgo en general

## Integración con Cognitive Compression

El motor de cognitive compression muestra el codebase health en cada resumen del runtime:

```
codebase: health=45/100 (critical), 62 modules, 274 edges, 4 high risks, 3 hotspots
```

Si existe un wide blast radius:

```
wide blast radius: module runtime/governance impacts 12 modules on change
```

## Por Qué Esto Importa

Sin correlación de codebase, los incidentes son eventos aislados. Con ella, cada incidente lleva contexto estructural:

- **La severidad es contextual**: un fallo de governance en un módulo con 12 dependientes es peor que el mismo fallo en un módulo aislado
- **La remediación está guiada**: el blast radius te dice qué probar después de un fix
- **El ownership está claro**: el domain mapping te dice a quién notificar

Esto no es documentación estática. Es cognición estructural en vivo — actualizada cada 30 segundos mediante escaneo AST determinista.
