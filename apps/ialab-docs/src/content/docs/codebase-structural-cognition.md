---
title: "Cognición Estructural de la Codebase"
summary: "Documentación técnica de la integración GitNexus como memoria estructural del código fuente: dependency graphs, blast radius, ownership mapping, structural risks y cognitive pipeline."
order: 35
---

# Cognición Estructural de la Codebase

## Overview

El módulo de cognición estructural de la codebase de AI-LAB (`runtime/codebase/`) proporciona comprensión determinista y grounded de la estructura del código fuente del propio runtime. Responde tres preguntas operacionales:

1. **¿Cómo es la codebase estructuralmente?** — inventario de módulos, grafo de dependencias, topología de dominios
2. **¿Qué se rompe si cambio X?** — blast radius analysis mediante recorrido BFS
3. **¿Quién es dueño de qué?** — ownership mapping desde rutas de módulos a dominios operacionales

## Acceso a GitNexus UI

Si accedes a la UI de GitNexus desde un PC remoto y ves **“Waiting for server to start”**, revisa:

- `docs/codebase/gitnexus-local-access.md`

## Arquitectura

```
runtime/codebase/
├── __init__.py              # Public API exports
├── contracts.py             # Dataclasses, OWNERSHIP_DOMAINS, constants
└── gitnexus_memory.py       # AST scanner, graph builder, risk engine
```

### Separación de Verdad

AI-LAB mantiene tres capas de verdad independientes:

| Capa | Fuente | Responsabilidad |
|---|---|---|
| **Prometheus** | Gateway :8008/metrics | Runtime authority truth — qué está pasando ahora |
| **OperationalTruth** | Sensor fusion + maturity | Semantic runtime truth — qué sabe el runtime |
| **GitNexus** | `runtime/codebase/` AST scan | Codebase structural truth — cómo es el código |

### Determinista por Construcción

Cada llamada a codebase memory produce un `determinant_signature` — un hash SHA-256 de la lista de módulos, la lista de edges y el inventario de riesgos. Misma codebase → misma firma. Esto permite:

- Análisis de blast radius reproducible
- Detección de cambios mediante comparación de firmas
- Invariantes de validación que verifican el determinismo

### Capa de Caché

Una caché basada en TTL (por defecto 30 segundos) evita re-escaneos en cada petición. El estado de la caché se expone via `get_codebase_cache_state()`.

## Escaneo de Módulos

### Parsing de AST de Imports

`_parse_imports()` lee cada archivo `.py`, parsea su AST y extrae todas las sentencias `import` y `from ... import`:

```python
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        for alias in node.names:
            targets.append(alias.name)
    elif isinstance(node, ast.ImportFrom):
        if node.module:
            targets.append(node.module)
```

Los edges se filtran para incluir solo imports `runtime.*` entre módulos trackeados.

### Ownership Domains

Cada ruta de módulo se asigna a un dominio operacional via `OWNERSHIP_DOMAINS`:

| Domain | Module Paths |
|---|---|
| `authority` | `runtime/authority` |
| `governance` | `runtime/governance` |
| `validation` | `runtime/validation` |
| `gateway` | `runtime/gateway` |
| `incidents` | `runtime/incidents` |
| `codebase` | `runtime/codebase` |
| `observability` | `runtime/observability` |
| `reporting` | `runtime/reporting` |
| `telemetry` | `runtime/telemetry` |
| `infrastructure` | `runtime/infrastructure` |
| ... | ... (24 dominios en total) |

## Blast Radius Engine

El blast radius se calcula mediante recorrido BFS a través de los reverse dependency edges:

```python
for each module:
    impacted = {module}
    queue = [module]
    while queue:
        current = queue.pop(0)
        for dependent, deps in dep_map.items():
            if current in deps and dependent not in visited:
                visited.add(dependent)
                impacted.add(dependent)
                queue.append(dependent)
```

Clasificación de severidad:

| Módulos impactados | Severidad |
|---|---|
| 1-2 | baja |
| 3-5 | media |
| 6+ | alta |

## Detección de Riesgos Estructurales

Se identifican tres tipos de riesgo automáticamente:

### High Coupling
El módulo importa 5+ otros módulos. Indica que el módulo tiene dependencias externas de amplio alcance.

### High Reverse Coupling
El módulo es importado por 5+ otros módulos. Indica que el módulo es un hub — los cambios aquí se propagan ampliamente.

### Wide Blast Radius
Un cambio en el módulo impacta 6+ otros módulos mediante cadenas de dependencias transitivas.

### Authority Dependency Spread
Se detecta cuando el módulo authority es importado por 3+ dominios distintos — indicando concentración de dependencia operacional.

## Structural Health Score

La fórmula del score:

```
base = 100
base -= high_risks * 5      (max -50)
base -= medium_risks * 2     (max -30)
base -= edge_density penalty (max -15 if density > 5.0)
score = max(10, min(100, base))
```

Niveles:

| Score | Nivel |
|---|---|
| >= 80 | healthy |
| 50-79 | degraded |
| < 50 | critical |

## Gateway API

Todos los endpoints bajo `GET /runtime/codebase/*` devuelven JSON con `determinant_signature`.

### Summary

```
GET /runtime/codebase/summary
Response: { contract_version, summary, score, freshness, gitnexus_stats, determinant_signature }
```

### Modules

```
GET /runtime/codebase/modules
Response: { contract_version, modules: [{ path, module_name, domain, file_count }], ... }
```

### Dependencies

```
GET /runtime/codebase/dependencies
Response: { contract_version, edges: [{ source, target, edge_type }], modules, ... }
```

### Blast Radius

```
GET /runtime/codebase/blast-radius?module_path=gateway
Response: { results: [{ module_path, affected_domains, total_impacted, severity }], ... }
```

### Ownership

```
GET /runtime/codebase/ownership
Response: { domains: [{ domain, paths, file_count }], ... }
```

### Topology

```
GET /runtime/codebase/topology
Response: { modules_total, domains_total, edges_total, hotspots, domain_dependency_matrix }
```

### Risks

```
GET /runtime/codebase/risks
Response: { risks: [{ risk_type, domain, severity, description }], score, ... }
```

### Score

```
GET /runtime/codebase/score
Response: { score: { structural_health_score, level, modules_total, ... } }
```

## Métricas

Seis counters de Prometheus trackean la codebase memory:

| Métrica | Tipo | Descripción |
|---|---|---|
| `ailab_codebase_modules_total` | Gauge | Total de módulos escaneados |
| `ailab_codebase_dependency_edges_total` | Gauge | Total de edges de dependencia |
| `ailab_codebase_structural_health_score` | Gauge | Health score actual (0-100) |
| `ailab_codebase_hotspots_total` | Gauge | Módulos con >= 3 dependencias |
| `ailab_codebase_risks_total` | Gauge | Total de riesgos estructurales |
| `ailab_codebase_ownership_domains_total` | Gauge | Dominios de ownership únicos |
| `ailab_codebase_memory_freshness_seconds` | Gauge | Segundos desde la última generación de memoria |

## Puntos de Integración

### Integración con Governance

El registry de governance incluye `codebase_memory_health` como dominio monitorizado. Un structural health score < 50 dispara un flag de degradación en governance.

### Integración con Validation

Cuatro invariantes aseguran la integridad de la codebase memory:

| Invariant | Blocking | Descripción |
|---|---|---|
| `INVARIANT-CODEBASE-MEMORY-GROUNDED` | No | Pass si modules > 0 y edges > 0 |
| `INVARIANT-NO-PHANTOM-MODULES` | No | Pass si level != unknown o modules > 0 |
| `INVARIANT-BLAST-RADIUS-DETERMINISM` | No | Pass si misma firma en strict mode |
| `INVARIANT-NO-RUNTIME-STATE-CONTAMINATION` | Sí | Fail-blocking si algún module path contiene `runtime/state` |

### Incident Intelligence

`detect_codebase_incidents()` se dispara cuando:
- Structural health score < 50 (high/critical)
- High-risk count > 3 (high)
- Wide blast radius detectado (medium)

Los reportes de incidentes se enriquecen con ownership de codebase y hotspots.

### Cognitive Compression

`compress_codebase_signals()` en `cognitive_compression.py` expone:
- Structural health score y nivel
- High risk count
- Módulos hotspot
- Wide blast radius entries

### Reporting Operacional

`build_codebase_memory_summary()` en `reporting_engine.py` expone:
- `structural_health_score`
- `modules_total`, `edges_total`
- `high_risks`, `medium_risks`
- `hotspots`, `domain_dependencies`
- `freshness`

## Runbooks

Ver:

- [Safe Refactor Workflow](/runbooks/safe-refactor-workflow)
- [Blast Radius Review](/runbooks/blast-radius-review)
- [Dependency Risk Analysis](/runbooks/dependency-risk-analysis)
- [Runtime-Codebase Correlation](/runbooks/runtime-codebase-correlation)
- [Incident-to-Module Analysis](/runbooks/incident-to-module-analysis)
