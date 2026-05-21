---
title: "Runtime Observability Fabric"
summary: "Arquitectura del tejido de observabilidad del runtime: Prometheus como sistema nervioso, sensor fusion, evidence pipeline y topología dinámica."
order: 15
---

## Visión

La Runtime Observability Fabric es la capa arquitectónica que conecta la infraestructura física (GPUs, servidores, redes) con la cognición del LLM. No es un dashboard: es el sistema nervioso del runtime.

```
Infraestructura → Prometheus → Sensor Fusion → OBSERVED_RUNTIME → LLM
```

## Principios de diseño

### 1. Prometheus como source of truth único

Todo lo que el runtime sabe de sí mismo viene de Prometheus. No hay archivos de configuración duplicados, no hay defaults hardcoded, no hay heurísticas.

### 2. observed vs derived separation

Los datos crudos (observed_data) y las inferencias (derived_state) viven en espacios separados. El LLM puede ver ambos, pero el runtime sabe cuál es cuál.

### 3. Confidence per-domain

Un fallo en un sensor AUXILIAR no degrada la confianza de un sensor CRITICAL. El confidence scoring es granular.

### 4. Freshness sobre disponibilidad

Prefiero un dato stale etiquetado como tal que un dato "actual" que en realidad es un default sintético.

### 5. Cache con límite de daño

TTL de 5s con timeout de 2s para Prometheus. Si Prometheus no responde, el runtime usa el último dato conocido con freshness label. Nunca bloquea una request.

## Arquitectura en capas

```
┌─────────────────────────────────────────────────────┐
│                   CAPA COGNITIVA                      │
│  LLM (qwen2.5-14b) recibe OBSERVED_RUNTIME          │
│  Evidence guard sanitiza respuesta                   │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────┐
│               CAPA DE FUSIÓN                          │
│  SensorFusionEngine                                  │
│  ├── collect(): 13 dominios                          │
│  ├── observed vs derived                             │
│  ├── domain confidence                               │
│  └── topology derivation                             │
│                                                       │
│  OperationalSummaryBuilder                           │
│  ├── route-family-aware                              │
│  └── gpu_summary, routing, slo, storage              │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────┐
│               CAPA DE ADQUISICIÓN                     │
│  PrometheusQueryClient                               │
│  ├── query_instant()                                 │
│  ├── get_target_up()                                 │
│  ├── gpu_metrics() → dynamic discovery               │
│  ├── cache TTL 5s                                    │
│  └── timeout 2s                                      │
│                                                       │
│  LM Studio API Client                                │
│  └── /v1/models → model availability                 │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────┐
│               CAPA FÍSICA                             │
│  Prometheus 192.168.1.40:9090                        │
│  ├── 17 targets                                      │
│  ├── 15 UP                                           │
│  ├── 2 DOWN (expected)                               │
│  └── 100+ métricas ailab_*                           │
│                                                       │
│  LM Studio 192.168.1.50:1234                         │
│  └── 3 modelos activos                               │
└─────────────────────────────────────────────────────┘
```

## Flujo completo de una request

```mermaid
sequenceDiagram
    participant C as Cliente
    participant G as Gateway (:8008)
    participant SF as SensorFusionEngine
    participant P as Prometheus (:9090)
    participant LM as LM Studio (:1234)
    participant LLM as qwen2.5-14b
    
    C->>G: POST /v1/chat/completions
    G->>SF: inject_agent_context()
    SF->>P: query_instant() x13 dominios
    SF->>P: get_target_up() x17 targets
    SF->>P: query_gpu_metrics() x7 métricas
    SF->>LM: GET /v1/models
    P-->>SF: target status + metrics
    LM-->>SF: model list
    
    SF->>SF: classify_topology()
    SF->>SF: compute_confidence()
    SF->>SF: build_evidence_catalog()
    
    SF-->>G: RuntimeSensorFusionSnapshot
    G->>G: build OBSERVED_RUNTIME (≤16KB)
    G->>LLM: inject OBSERVED_RUNTIME + prompt
    LLM-->>G: response
    G->>G: evidence_guard sanitize
    G-->>C: 200 response
```

## Mapa de dominios y dependencias

```mermaid
flowchart TD
    subgraph CRITICAL
        G[gateway 8008]
        R[router 8083]
        GN[gpu_nodes]
    end
    
    subgraph IMPORTANT
        CP[control_plane]
        LA[live_api 8084]
        SN[system_node 9100]
        SM[smartctl]
        LMM[lmstudio_models]
    end
    
    subgraph AUXILIARY
        CT[containers 8081]
        DK[docker]
        WE[windows_exporters]
        UN[unifi]
        CF[cloudflare_tunnel]
    end
    
    P[Prometheus 192.168.1.40:9090] --> G
    P --> R
    P --> GN
    P --> CP
    P --> LA
    P --> SN
    P --> SM
    P --> CT
    P --> DK
    P --> WE
    P --> UN
    P --> CF
    
    LM_API[LM Studio API] --> LMM
    
    GN --> GPU1[RX9070 192.168.1.50]
    GN --> GPU2[RX7900XT 192.168.1.60]
    GPU2 -.->|expected offline| INV[Inventory]
```

## Evolución de la arquitectura

```
FASE 29 (SLO enforcement)
├── Observabilidad reactiva
├── Métricas de rendimiento
└── Alertas de degradación

FASE 30H (Evidence enforcement)
├── Catálogo de evidencia sintético
├── Denylists y sanitización
└── NO DISPONIBLE para no observado

FASE 30I (Sensor fusion) ← ESTAMOS AQUÍ
├── Prometheus como source of truth
├── 13 dominios observados
├── Confidence per-domain
├── Topología dinámica
└── GPU metrics en vivo

FASE 31A (Multi-GPU)
├── Scheduler sensor-aware
├── Warm pool basado en métricas
└── Routing con confidence scores
```

## Ver también

- [Runtime Sensor Topology](/docs/architecture/runtime-sensor-topology/)
- [Runtime Evidence Pipeline](/docs/architecture/runtime-evidence-pipeline/)
- [FASE 30I — Runtime Sensor Fusion](/docs/runtime/30i-runtime-sensor-fusion/)
- [Prometheus Runtime Integration](/docs/observability/prometheus-runtime-integration/)
