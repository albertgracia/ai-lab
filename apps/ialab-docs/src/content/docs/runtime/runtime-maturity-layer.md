---
title: "Capa de Madurez del Runtime"
summary: "FASES 30A-30H: runtime state foundation, model state awareness, degraded mode, governance visibility, route semantics, reporting discipline y evidence enforcement."
order: 20
---

## Visión general

La capa de madurez del runtime (FASE 30) proporciona la semántica operacional necesaria para que AI-LAB conozca su propio estado, lo reporte con precisión y no invente lo que no observa. Es el requisito previo para Multi-GPU.

```
FASE 30A → Runtime State Foundation (maturity descriptors, runtime_generation, TemporalState)
FASE 30B → Model State Awareness (active/loaded/discoverable/disabled)
FASE 30C → Single-Node Explicit Degraded Mode (GREEN/YELLOW/RED con reglas)
FASE 30D → Topology Role & Failure Domain Taxonomy
FASE 30E → Governance Visibility (refinamiento de decisiones governance)
FASE 30F → Cognitive Route Semantics (semántica operacional por route-family)
FASE 30G → Operational Reporting Discipline (reportes NOC con semántica)
FASE 30H → Runtime Evidence Enforcement (catálogo de evidencia, NO DISPONIBLE)
```

## FASE 30A — Runtime State Foundation

Checkpoint: **CP-30A-RUNTIME-STATE-FOUNDATION-STABLE**

Introduce:
- `runtime_generation` — descriptor de la generación actual del runtime
- `TemporalState` — estados temporales del runtime con timestamps
- Maturity descriptors: fase, modo, degradación
- Endpoint `/runtime/maturity`

## FASE 30B — Model State Awareness

Checkpoint: **CP-30B-MODEL-STATE-AWARE-STABLE**

Introduce:
- `ModelStatusTracker` con TTL, alias normalization, DISABLED priority
- Estados: active, loaded, discoverable, disabled, unknown
- Reglas:
  - RULE-30B-1: Un modelo DISABLED prevalece sobre cualquier otro estado
  - RULE-30B-2: active implica loaded, pero loaded no implica active
  - RULE-30B-3: discoverable no implica ni loaded ni active
  - RULE-30B-4: unknown es el estado por defecto
  - RULE-30B-5: TTL para limpiar estados stale (300s)
  - RULE-30B-6: Los alias se normalizan al nombre canónico

## FASE 30C — Degraded Mode Explicit

Checkpoint: **CP-30C-DEGRADED-MODE-EXPLICIT-STABLE**

Estado degradado explícito en nodo único:
- GREEN: operación normal
- YELLOW: degradación parcial (TTFB elevado, GPU sobrecargada)
- RED: degradación crítica (timeouts, errores)
- Reglas de transición con anti-flapping

## FASE 30D — Topology & Failure Domain

Checkpoint: **CP-30D-TOPOLOGY-FAILURE-DOMAIN-STABLE**

- Rol del nodo en la topología
- Clasificación de dominios de fallo
- Endpoint `/runtime/topology`

## FASE 30E — Governance Visibility

Checkpoint: **CP-30E-GOVERNANCE-VISIBILITY-STABLE**

- Visibilidad explícita de decisiones governance
- Endpoint `/runtime/governance`
- Por qué se bloqueó/bloqueó una acción

## FASE 30F — Route Semantics

Checkpoint: **CP-30F-ROUTE-SEMANTICS-STABLE**

- Semántica operacional por route-family
- route family existence != active
- Endpoint `/runtime/routes/semantics`

## FASE 30G — Operational Reporting

Checkpoint: **CP-30G-OPERATIONAL-REPORTING-STABLE**

- Reportes NOC con semántica operacional
- Disciplina de reportes: no afirmar lo no observado
- Endpoint `/runtime/reports/discipline`

## FASE 30H — Evidence Enforcement

Checkpoint: **CP-30H-RUNTIME-EVIDENCE-ENFORCEMENT-STABLE**

- Catálogo de evidencia observada del runtime
- Strict evidence mode (default: true)
- MAX_UNVERIFIED_CLAIMS = 5
- Denylists: modelos prohibidos, GPUs no observadas, security tools, plataformas externas
- Hallucination suppression via sanitización post-hoc
- NO DISPONIBLE para datos no observados
- Endpoint `/runtime/reports/evidence`
- 4 métricas Prometheus nuevas

### Reglas epistemológicas

```
RULE-30H-1: Todo dato técnico debe estar respaldado por OBSERVED_RUNTIME
RULE-30H-2: Si un dato no aparece en OBSERVED_RUNTIME, usar NO DISPONIBLE
RULE-30H-3: Prohibido inventar GPUs, vendors, modelos, hosts, puertos, versiones
RULE-30H-4: Prohibido inventar servicios, porcentajes, latencias, OS
RULE-30H-5: Prohibido inventar herramientas de seguridad o plataformas externas
RULE-30H-6: Modelos solo del model state runtime; nodos solo de runtime topology
```

### Arquitectura del evidence guard

```
evidence_guard.py
├── build_evidence_catalog()     → catálogo de 6 categorías
├── sanitize_unverified_claims() → sanitización post-hoc
├── report_evidence_score        → 1.0 - (0.15 × unverified_claims)
└── Denylists
    ├── PROHIBITED_MODELS        → GPT-4, Claude, Gemini, etc.
    ├── UNOBSERVED_GPUS          → A100, H100, H200, MI300X, etc.
    ├── SECURITY_TOOLS           → SELinux, AppArmor, Falco, etc.
    ├── EXTERNAL_PLATFORMS       → AWS, GCP, Azure, etc.
    ├── UNKNOWN_MODELS           → patrones de modelos no observados
    └── UNKNOWN_HOSTS            → IPs y hostnames no observados
```

## FASE 30I — Runtime Sensor Fusion

Checkpoint: **CP-30I-RUNTIME-SENSOR-FUSION-STABLE**

Nueva fase fundacional del runtime observacional. Introduce:

- `PrometheusQueryClient` — cliente Prometheus con cache TTL 5s, timeout 2s
- `SensorFusionEngine` — fusión de 13 dominios con confidence per-domain
- `RuntimeSensorFusionSnapshot` — observed_data + derived_state separados
- `RuntimeTopologyState` — topología derivada de targets Prometheus
- `OperationalSummaryBuilder` — resúmenes route-family-aware
- Endpoint `/runtime/sensors` — always-on 200
- GPU metrics dinámicas: temperatura, carga, potencia, ventilador, reloj
- 4 métricas Prometheus nuevas

### Cambio conceptual

Antes de 30I, OBSERVED_RUNTIME se construía desde archivos de estado (sintético). Después de 30I, se construye desde Prometheus (evidencia viva).

### Relación con otras fases

- **30A** → runtime_generation + TemporalState (30I añade sensor_generation y freshness)
- **30D** → taxonomía de dominios de fallo (30I implementa topología dinámica)
- **30H** → evidence guard con datos sintéticos (30I reemplaza fuente con Prometheus)

### Ver también

- [FASE 30I — Runtime Sensor Fusion](/docs/runtime/30i-runtime-sensor-fusion/) — documentación detallada
- [Trust Boundaries](/docs/governance/runtime-trust-boundaries/) — límites de confianza
- [Evidence Enforcement](/docs/governance/evidence-enforcement/) — documentación detallada de FASE 30H
