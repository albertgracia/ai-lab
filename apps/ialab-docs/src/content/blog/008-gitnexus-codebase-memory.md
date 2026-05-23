---
title: "Dando a AI-LAB Memoria Estructural de la Codebase con GitNexus"
date: "2026-05-23"
summary: "Cómo AI-LAB integra GitNexus como memoria estructural del código fuente — dependency graphs, blast radius analysis, ownership cognition y deterministic structural risk scoring."
tags:
  - ai-lab
  - gitnexus
  - codebase
  - cognition
  - architecture
---

# Dando a AI-LAB Memoria Estructural de la Codebase con GitNexus

AI-LAB ha evolucionado de un LLM gateway simple a un runtime con cognición operacional. Se monitoriza a sí mismo via Prometheus, razona sobre su estado mediante sensor fusion y toma decisiones de governance basadas en evidencia.

Pero había un vacío: **AI-LAB no tenía comprensión estructural de su propio código fuente.**

Cuando el runtime detectaba un governance drift en el módulo `authority`, no podía razonar sobre qué otros módulos dependían de él. Cuando un validation invariant fallaba en `tool_registry.py`, no había forma de trazar qué execution flows se romperían.

GitNexus cierra ese vacío.

## Las Tres Capas de Verdad

AI-LAB opera ahora sobre tres capas de verdad independientes, cada una con una responsabilidad distinta:

```
Prometheus        →  Runtime authority truth   (qué está pasando ahora)
OperationalTruth  →  Semantic runtime truth    (qué sabe el runtime)
GitNexus          →  Codebase structural truth (cómo es el código fuente)
```

Estas tres capas son independientes pero correlacionables. Un pico en `ailab_governance_blocked_total` desde Prometheus se puede cruzar con GitNexus para determinar qué módulo tiene el blast radius más amplio y qué deploy debería priorizarse.

## Cómo se Integra GitNexus

### Escaneo AST Local, Sin Dependencias Externas

El módulo de codebase memory en `runtime/codebase/gitnexus_memory.py` escanea el AST de Python en `/opt/ai-lab/runtime/`. Parsea sentencias `import`, construye un grafo dirigido de dependencias y deriva propiedades estructurales — todo de forma determinista.

```python
modules = _scan_runtime_modules()       # 62 módulos descubiertos
edges   = _build_import_graph(modules)  # ~274 edges dirigidos
```

### Mapeo de Ownership

Cada módulo se asigna a un dominio operacional via `OWNERSHIP_DOMAINS`:

```python
OWNERSHIP_DOMAINS = {
    "authority":     ["runtime/authority"],
    "governance":    ["runtime/governance"],
    "gateway":       ["runtime/gateway"],
    "codebase":      ["runtime/codebase"],
    "incidents":     ["runtime/incidents"],
    ...
}
```

Esto significa que un import desde `runtime/governance/` hacia `runtime/authority/` es una dependencia cross-domain — governance depende de authority.

### Blast Radius via BFS

Cuando un módulo cambia, el motor de blast radius recorre el grafo de dependencias mediante BFS:

```python
def _build_blast_radius(modules, edges):
    # Para cada módulo, BFS para encontrar todos los módulos impactados
    # Severidad: 1-2 = baja, 3-5 = media, 6+ = alta
```

Si `runtime/gateway/openai_gateway.py` cambia, el blast radius revela qué módulos de `runtime/llm/`, `runtime/router/` y `runtime/telemetry/` se ven afectados transitivamente.

### Detección de Riesgos Estructurales

Se detectan tres tipos de riesgo:

- **High Coupling**: el módulo importa 5+ otros módulos
- **High Reverse Coupling**: el módulo es importado por 5+ otros módulos
- **Wide Blast Radius**: el módulo impacta 6+ otros módulos al cambiar

Esto produce un **structural health score** (0-100):

```python
score = base (100)
       - high_risks * 5
       - medium_risks * 2
       - edge_density penalty
```

## Gateway Endpoints

La codebase memory se expone mediante ocho endpoints del runtime:

| Endpoint | Descripción |
|---|---|
| `GET /runtime/codebase/summary` | Resumen de salud estructural |
| `GET /runtime/codebase/modules` | Inventario de módulos con dominios |
| `GET /runtime/codebase/dependencies` | Lista completa de edges de dependencia |
| `GET /runtime/codebase/blast-radius` | Blast radius por módulo |
| `GET /runtime/codebase/ownership` | Mapa de ownership por dominio |
| `GET /runtime/codebase/topology` | Topología módulo-dominio |
| `GET /runtime/codebase/risks` | Inventario de riesgos estructurales |
| `GET /runtime/codebase/score` | Health score determinista |

Todos los endpoints devuelven JSON con un `determinant_signature` para reproducibilidad.

## Puntos de Integración

### Governance

El registry de governance incluye `codebase_memory_health` como dominio monitorizado. Si el structural health cae por debajo de 50, governance lo marca como degradación.

### Validation

Cuatro invariantes DEV-36X validan la integridad de la codebase memory:

| Invariant | Propósito |
|---|---|
| `INVARIANT-CODEBASE-MEMORY-GROUNDED` | Módulos y edges deben ser no-zero |
| `INVARIANT-NO-PHANTOM-MODULES` | Todos los módulos deben ser directorios reales |
| `INVARIANT-BLAST-RADIUS-DETERMINISM` | Misma codebase → mismo blast radius |
| `INVARIANT-NO-RUNTIME-STATE-CONTAMINATION` | Sin `runtime/state/` en el grafo de codebase |

### Incident Intelligence

La detección de incidentes para el dominio `codebase` se activa cuando:

- Structural health score < 50 (severidad alta)
- High-risk count > 3 (severidad alta)
- Wide blast radius detectado (severidad media)

### Cognitive Compression

El cognitive summarizer incluye `compress_codebase_signals()` que muestra el codebase health, high risks, hotspots y wide blast radius en el resumen operacional.

## Métricas

Seis counters de Prometheus trackean la salud estructural de la codebase:

- `ailab_codebase_modules_total`
- `ailab_codebase_dependency_edges_total`
- `ailab_codebase_structural_health_score`
- `ailab_codebase_hotspots_total`
- `ailab_codebase_risks_total`
- `ailab_codebase_ownership_domains_total`
- `ailab_codebase_memory_freshness_seconds`

## ¿Por Qué No Una Integración IDE Completa?

GitNexus no es una plataforma de análisis de código. Es una **capa de memoria estructural**. No necesita entender semántica, execution paths ni data flow. Responde tres preguntas:

1. ¿Cómo es la codebase estructuralmente?
2. ¿Qué se rompe si cambio X?
3. ¿Quién es dueño de qué?

Eso es todo lo que el runtime necesita para cognición operacional.

## Estado Actual

- **Índice**: 460 archivos, 10,145 nodos, 15,369 edges (GitNexus v1.6.5)
- **Módulos**: 62 módulos del runtime, ~274 edges de dependencia
- **Score**: varía según el estado de la codebase, típicamente 20-80
- **Caché**: TTL de 30 segundos con invalidación determinista
- **Tests**: 31 tests, todos pasan deterministamente
