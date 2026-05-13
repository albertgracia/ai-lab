# AI-LAB
## Local-First Distributed Cognitive Infrastructure

AI-LAB es una plataforma cognitiva operacional local-first diseñada para homelab, inferencia distribuida y automatización inteligente de infraestructura.

El objetivo del proyecto no es únicamente ejecutar modelos LLM locales, sino construir un:

> Distributed Cognitive Runtime

capaz de:

- razonar sobre infraestructura;
- mantener memoria operacional;
- enrutar tareas cognitivas;
- coordinar workflows;
- ejecutar inferencia distribuida;
- aplicar governance;
- automatizar operaciones;
- evolucionar hacia una arquitectura multiagente autónoma.

---

# Current Status

## Distributed Cognitive Runtime v1

Estado actual del sistema:

- Distributed Task Routing
- Workflow Engine
- Governance Runtime
- Semantic Memory
- Episodic Memory
- Distributed Cognition
- Capability-based Routing
- Execution Profiles
- Sandbox Runtime
- Multi-node Inference
- Persistent Audit Trail
- Operational Cognitive Context

---

# Core Architecture

```text
User Request
    ?
Intent Router
    ?
Workflow Planner
    ?
Distributed Task Router
    ?
Execution Coordinator
    ?
Inference Nodes
    ?
Memory + Audit + Governance
```

---

# Infrastructure

## Main Orchestration Node

| Component | Value |
|---|---|
| Host | Ubuntu Server |
| Virtualization | Hyper-V |
| Main Node | ubuntu-ialab |
| IP | 192.168.1.30 |
| Repository | /opt/ai-lab |

---

# Distributed Cognitive Cluster

## Active Nodes

### NAS Local Router Node

| Property | Value |
|---|---|
| Host | 192.168.1.250 |
| GPU | RX780M |
| VRAM | 0.75 GB |
| Role | Lightweight Routing + Memory |
| Capabilities | fast, fallback, router, memory |

### RX7900XT Reasoning Node

| Property | Value |
|---|---|
| Host | 192.168.1.60 |
| GPU | RX7900XT |
| VRAM | 20 GB |
| Role | Reasoning + Coding + Orchestration |
| Capabilities | reasoning, coding, orchestration, backend, multi-agent |

### RX9070 Multimodal Node

| Property | Value |
|---|---|
| Host | 192.168.1.50 |
| GPU | RX9070 |
| VRAM | 16 GB |
| Role | Vision + Multimodal + Frontend |
| Capabilities | vision, image, multimodal, embeddings, creative |

---

# Current Runtime Components

## Governance Runtime

AI-LAB implementa un sistema de governance cognitiva con perfiles operacionales:

| Profile | Purpose |
|---|---|
| sandbox | entorno experimental |
| pilot | governance reforzada |
| production | máxima seguridad |

Características:

- capability enforcement
- shell restrictions
- audit trail
- execution validation
- profile-based security

---

# Distributed Workflow Engine

El runtime ya soporta:

- workflow planning
- distributed routing
- capability matching
- node scoring
- orchestration simulation
- execution trace persistence

Ejemplo:

```text
reasoning      -> RX7900XT
coding         -> RX7900XT
vision         -> RX9070
memory         -> RX9070
fast/fallback  -> NAS local
```

---

# Memory Architecture

## Semantic Memory

Motor RAG local basado en:

- Qdrant
- sentence-transformers
- local embeddings
- semantic retrieval

Usado para:

- contextual loading
- workflow augmentation
- operational cognition
- knowledge retrieval

---

## Episodic Memory

Sistema persistente de eventos cognitivos:

```text
runtime/state/episodic_memory.jsonl
```

Registra:

- workflows
- routing
- orchestration
- governance events
- execution traces
- distributed decisions

---

# Cognitive Runtime

## Runtime Structure

```text
runtime/
+-- agent/
+-- distributed/
+-- execution/
+-- memory/
+-- planner/
+-- profiles/
+-- state/
+-- workflows/
```

---

# Current Services

## Docker Stack

| Service | Purpose |
|---|---|
| Traefik | Reverse Proxy |
| Open WebUI | Unified AI Frontend |
| Ollama | Local Inference |
| Qdrant | Vector Database |
| Portainer | Docker Management |

---

# AI Stack

## Ollama

Local CPU inference runtime.

Current usage:

- lightweight models
- embeddings
- automation
- fallback inference

---

## LM Studio

External GPU inference backend.

Integrated using:

- OpenAI-compatible APIs
- distributed cognitive routing
- capability-based task assignment

---

# Observability (In Progress)

Planned stack:

- Prometheus
- Grafana
- Loki
- Promtail
- Node Exporter
- cAdvisor

Future objectives:

- operational reasoning
- anomaly detection
- infrastructure cognition
- historical analysis
- telemetry-aware orchestration

---

# Distributed Cognition

AI-LAB ya implementa:

- distributed node registry
- capability-aware routing
- cognitive workload distribution
- node scoring
- workflow orchestration
- distributed simulation

Próximas fases:

- real remote execution
- async execution queues
- failover engine
- execution aggregation
- autonomous workflows

---

# Multi-Agent Vision

Objetivo futuro:

```text
planner-agent
    ?
reasoning-agent
    ?
coding-agent
    ?
security-agent
    ?
documentation-agent
    ?
execution-agent
```

Con coordinación autónoma distribuida.

---

# Storage Architecture

## AI Models Storage

```text
/mnt/ai-models
```

Usado para:

- Ollama models
- embeddings
- datasets
- persistent cognitive memory

---

# Git Infrastructure

Repository:

```text
/opt/ai-lab
```

Incluye:

- runtime
- workflows
- distributed cognition
- governance
- orchestration
- memory systems

Excluye:

- datasets
- logs
- runtime artifacts
- model binaries

---

# Philosophy

## Local First

Todo el runtime está diseñado para ejecutarse:

- local
- private
- self-hosted
- sovereign

---

## Modular Architecture

Separación explícita entre:

- cognition
- memory
- execution
- governance
- workflows
- orchestration
- infrastructure

---

## Incremental Cognitive Growth

La evolución del proyecto sigue capas progresivas:

```text
Infrastructure
    ?
Knowledge
    ?
Memory
    ?
Governance
    ?
Workflows
    ?
Distributed Cognition
    ?
Autonomous Operations
```

---

# Current Roadmap

## Phase 6 — Distributed Cognitive Runtime
- distributed workflows
- execution coordination
- task aggregation
- failover routing
- async orchestration

## Phase 7 — Autonomous Operations
- autonomous remediation
- operational reasoning
- infrastructure cognition
- adaptive workflows

## Phase 8 — Multi-Agent Coordination
- specialized agents
- distributed cognition mesh
- cooperative reasoning
- autonomous planning

---

# Final Objective

Construir una:

> Local-First Operational Cognitive Platform

capaz de:

- razonar sobre infraestructura;
- mantener memoria persistente;
- coordinar agentes;
- ejecutar workflows;
- automatizar operaciones;
- aprender del estado del sistema;
- operar como un verdadero AI Operations Brain.

---

# Project Status

## Current Level

```text
Distributed Cognitive Infrastructure
```

## Next Major Milestone

```text
Distributed Execution Coordinator
```
