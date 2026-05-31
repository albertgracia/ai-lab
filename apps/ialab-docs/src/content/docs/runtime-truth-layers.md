---
title: "Capas de Verdad del Runtime"
summary: "Arquitectura de las tres capas de verdad del runtime AI-LAB: Prometheus, OperationalTruth y GitNexus. Separación de responsabilidades y correlación entre fuentes."
order: 10
---


AI-LAB opera sobre tres capas de verdad independientes, cada una con responsabilidades, fuentes y consumidores distintos.

## Las Tres Capas

```
┌─────────────────────────────────────────────────────────┐
│                 RUNTIME TRUTH LAYERS                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────┐  ┌────────────────────────┐  │
│  │    Prometheus        │  │    OperationalTruth     │  │
│  │  Runtime Authority   │  │  Semantic Runtime Truth │  │
│  │                      │  │                        │  │
│  │  • Gateway metrics   │  │  • Sensor fusion        │  │
│  │  • GPU metrics       │  │  • Runtime maturity     │  │
│  │  • Scrape targets    │  │  • Degradation state    │  │
│  │  • Alert rules       │  │  • Domain confidence    │  │
│  │  • TTFB/latency      │  │  • Evidence catalog     │  │
│  └──────────┬───────────┘  └───────────┬────────────┘  │
│             │                          │               │
│             └──────────┬───────────────┘               │
│                        │                               │
│             ┌──────────▼───────────┐                   │
│             │     GitNexus         │                   │
│             │  Codebase Structural │                   │
│             │      Truth           │                   │
│             │                      │                   │
│             │  • AST scanning      │                   │
│             │  • Dependency graph  │                   │
│             │  • Blast radius      │                   │
│             │  • Ownership mapping │                   │
│             │  • Structural risks  │                   │
│             └──────────────────────┘                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Responsabilidades de Cada Capa

### 1. Prometheus — Runtime Authority Truth

**Fuente**: Gateway (:8008/metrics), Router (:8083/metrics), Live API (:8084/metrics), GPU exporters (:9182, :9183), node_exporter (:9100)

**Responsabilidad**: Qué está pasando ahora mismo en el runtime.

- Conteos de requests, latencias, estadísticas de streaming
- Temperatura GPU, VRAM, carga
- Salud de scrape de todos los targets
- Evaluación de reglas de alerta

**Consumido por**: Grafana dashboards, alertmanager, sensor fusion, fastpath

**Contrato**: Formato estándar de exposición Prometheus. Sin interpretación semántica — datos numéricos raw.

### 2. OperationalTruth — Semantic Runtime Truth

**Fuente**: `runtime/semantics/runtime_maturity.py`, `runtime/context/sensor_fusion.py`, `runtime/governance/`, `runtime/validation/`

**Responsabilidad**: Qué sabe el runtime sobre sí mismo, semánticamente.

- Domain health confidence scores
- Estado de degradación (qué dominios, por qué)
- Catálogo de evidencia para decisiones de governance
- Nivel de madurez del runtime
- Inferencia de modo de topología

**Consumido por**: Reporting engine, cognitive compression, incidents, governance, operator UI

**Contrato**: Basado en dict con `freshness`, `confidence`, `determinant_signature`. Sin métricas raw — estado interpretado.

### 3. GitNexus — Codebase Structural Truth

**Fuente**: `runtime/codebase/` — AST scan de `/opt/ai-lab/runtime/`

**Responsabilidad**: Cómo es la codebase estructuralmente.

- Inventario de módulos (62 módulos)
- Grafo de dependencias (274 edges dirigidos)
- Blast radius por módulo (recorrido BFS)
- Ownership mapping (24 dominios)
- Riesgos estructurales (high coupling, reverse coupling, wide blast)
- Health score (0-100)

**Consumido por**: Validation invariants, governance registry, incident intelligence, cognitive compression, reporting

**Contrato**: JSON con `determinant_signature`. Misma codebase → mismo grafo → misma firma.

## Correlación Entre Capas

### Prometheus ↔ OperationalTruth

- Prometheus raw counters → sensor fusion → domain confidence
- GPU metrics → operational summaries → GPU health state

### OperationalTruth ↔ GitNexus

- Governance degradation alerts → codebase blast radius check
- Incident intelligence → codebase ownership y hotspot enrichment

### Prometheus ↔ GitNexus

- Pico en `ailab_governance_blocked_total` de Prometheus → verificación de reverse coupling del módulo governance en GitNexus
- Sin acoplamiento directo — se correlacionan via OperationalTruth

## Reglas de Diseño

### RULE-TL-1

Prometheus es la única fuente de runtime authority. Ninguna codebase memory puede sobrescribir métricas de Prometheus.

### RULE-TL-2

OperationalTruth es el único intérprete semántico. Las métricas raw de Prometheus pasan por sensor fusion antes de llegar a las capas cognitivas.

### RULE-TL-3

GitNexus es grounded, determinista y de solo lectura. Sin modificaciones autónomas. Sin indexación de runtime state.

### RULE-TL-4

La correlación entre capas es aditiva, no sustitutiva. Un incidente de governance enriquecido con blast radius de codebase no reemplaza el incidente — lo complementa.

### RULE-TL-5

Ninguna capa depende de otra para su funcionalidad core. Si GitNexus no está disponible, el runtime continúa operando con Prometheus + OperationalTruth.

## Stack de Capas

```
FastPath / Cognitive Summary
        │
  OperationalTruth (semantic interpretation)
        │
  Prometheus (raw metrics)  ───  GitNexus (structural codebase)
        │                              │
  GPU / Gateway / Router          AST scan / import graph
```

Cada capa es independientemente observable, independientemente testeable e independientemente versionada mediante `determinant_signature`.
