# INFORME TÉCNICO EXHAUSTIVO: AI-LAB
## Local-First Distributed Cognitive Infrastructure v1

---

## 1. RESUMEN EJECUTIVO

**AI-LAB** es una plataforma cognitiva operacional *local-first* diseñada para homelab, inferencia distribuida y automatización inteligente de infraestructura. Su núcleo es un **Distributed Cognitive Runtime** capaz de razonar sobre infraestructura, mantener memoria operacional, enrutar tareas cognitivas, coordinar workflows, ejecutar inferencia distribuida, aplicar gobernanza y automatizar operaciones. La arquitectura está orientada a evolucionar hacia un sistema multiagente autónomo.

**Estado actual:** Distributed Cognitive Runtime v1 — completamente funcional con routing distribuido, planificación de workflows, gobernanza por perfiles, memoria semántica y episódica, y orquestación en clúster heterogéneo.

**Filosofía rectora:** Local-first, modular, soberano, de crecimiento cognitivo incremental.

---

## 2. ARQUITECTURA DEL SISTEMA

### 2.1. Diagrama de Flujo Conceptual

```
User Request
    |
    v
Intent Router
    |
    v
Workflow Planner
    |
    v
Distributed Task Router
    |
    v
Execution Coordinator
    |
    v
Inference Nodes  (RX7900XT | RX9070 | NAS)
    |
    v
Memory + Audit + Governance  (capa transversal)
```

### 2.2. Capas de la Arquitectura

| Capa | Función | Tecnología |
|------|---------|------------|
| **Routing** | Enrutamiento de intención y tareas | Cognitive Intent Router + Capability-based Routing |
| **Planning** | Planificación de workflows | Workflow Planner Engine |
| **Distributed Execution** | Coordinación y ejecución distribuida | Execution Coordinator + Node Scoring |
| **Inference** | Ejecución de modelos | Ollama (CPU) + LM Studio (GPU) vía API OpenAI-compatible |
| **Memory** | Memoria semántica y episódica | Qdrant + sentence-transformers + JSONL persistente |
| **Governance** | Seguridad y control por perfiles | Governance Runtime con 3 perfiles operacionales |
| **Audit** | Trazabilidad completa | Persistent Audit Trail en JSONL |

---

## 3. INFRAESTRUCTURA FÍSICA Y VIRTUAL

### 3.1. Nodo Principal de Orquestación

| Componente | Valor |
|------------|-------|
| Host | Ubuntu Server (26.04) |
| Virtualización | Hyper-V |
| Nombre del nodo | `ubuntu-ialab` |
| IP | 192.168.1.30 |
| Repositorio principal | `/opt/ai-lab` |

### 3.2. Clúster Cognitivo Distribuido

| Nodo | IP | GPU | VRAM | Rol | Capacidades |
|------|-----|-----|------|-----|-------------|
| **NAS Local Router** | 192.168.1.250 | RX780M | 0.75 GB | Routing ligero + Memoria | `fast`, `fallback`, `router`, `memory` |
| **RX7900XT Reasoning** | 192.168.1.60 | RX7900XT | 20 GB | Razonamiento + Código + Orquestación | `reasoning`, `coding`, `orchestration`, `backend`, `multi-agent` |
| **RX9070 Multimodal** | 192.168.1.50 | RX9070 | 16 GB | Visión + Multimodal + Frontend | `vision`, `image`, `multimodal`, `embeddings`, `creative` |

### 3.3. Topología de Red

- Red local (192.168.1.0/24)
- Comunicación entre nodos vía API REST (OpenAI-compatible)
- Nodo NAS actúa como router ligero y almacenamiento persistente
- Nodos GPU expuestos como backends de inferencia independientes
- Traefik como reverse proxy unificado

---

## 4. RUNTIME COGNITIVO DISTRIBUIDO

### 4.1. Estructura del Runtime

```
/opt/ai-lab/runtime/
+-- agent/             → Lógica de agentes cognitivos
+-- distributed/       → Coordinación y routing distribuido
+-- execution/         → Ejecutor de tareas y orchestación
+-- memory/            → Sistemas de memoria (semántica + episódica)
+-- planner/           → Planificador de workflows
+-- profiles/          → Perfiles de gobernanza
+-- state/             → Estado operacional del runtime
+-- workflows/         → Definiciones de workflows
```

### 4.2. Governance Runtime

Tres perfiles operacionales con seguridad progresiva:

| Perfil | Propósito | Restricciones |
|--------|-----------|---------------|
| **sandbox** | Experimental | Mínimas, exploración libre |
| **pilot** | Gobernanza reforzada | Políticas de capacidad, shell restringido |
| **production** | Máxima seguridad | Validación total de ejecución, auditoría obligatoria |

**Características transversales:**
- Capability enforcement (verificación de capacidades antes de ejecución)
- Shell restrictions (restricciones de comandos según perfil)
- Audit trail persistente (cada acción queda registrada)
- Execution validation (validación pre y post ejecución)
- Profile-based security (seguridad adaptativa según perfil)

### 4.3. Distributed Workflow Engine

El motor de workflows distribuidos implementa:

1. **Workflow Planning** — Planificación de secuencias de tareas
2. **Distributed Routing** — Enrutamiento basado en capacidades
3. **Capability Matching** — Coincidencia tarea → nodo
4. **Node Scoring** — Puntuación de nodos para asignación óptima
5. **Orchestration Simulation** — Simulación antes de ejecución real
6. **Execution Trace Persistence** — Almacenamiento de trazas

**Ejemplo de enrutamiento por capacidades:**
| Tarea | Nodo Asignado | Motivo |
|-------|---------------|--------|
| reasoning | RX7900XT | 20 GB VRAM, alta capacidad de cómputo |
| coding | RX7900XT | Misma razón + rol de backend |
| vision | RX9070 | GPU multimodal especializada |
| memory | RX9070 | Capacidad de embeddings |
| fast / fallback | NAS Local | Baja latencia, tareas ligeras |

---

## 5. ARQUITECTURA DE MEMORIA

### 5.1. Memoria Semántica (RAG local)

**Stack tecnológico:**
- **Qdrant** — Base de datos vectorial
- **sentence-transformers** — Generación de embeddings locales
- **local embeddings** — Sin dependencia externa

**Usos:**
- Carga contextual para inferencia
- Aumento de workflows con conocimiento relevante
- Cognición operacional (el sistema "recuerda" cómo resolver problemas)
- Recuperación semántica de conocimiento

### 5.2. Memoria Episódica

**Archivo persistente:** `runtime/state/episodic_memory.jsonl`

**Registra:**
- Workflows ejecutados
- Decisiones de routing
- Eventos de orquestación
- Eventos de gobernanza
- Trazas de ejecución completas
- Decisiones distribuidas

**Formato:** JSON Lines, append-only, orientado a auditoría forense.

---

## 6. SERVICIOS Y STACK TECNOLÓGICO

### 6.1. Docker Stack (Servicios Base)

| Servicio | Propósito | Puerto |
|----------|-----------|--------|
| **Traefik** | Reverse proxy y balanceo | 80/443 |
| **Open WebUI** | Frontend unificado de IA | 3000 |
| **Ollama** | Runtime de inferencia local (CPU) | 11434 |
| **Qdrant** | Base de datos vectorial | 6333 |
| **Portainer** | Gestión de contenedores | 9000 |

### 6.2. AI Stack

| Componente | Propósito | Modo |
|------------|-----------|------|
| **Ollama** | Inferencia CPU local, embeddings, automatización, fallback | CPU |
| **LM Studio** | Backend de inferencia GPU externo | GPU (API OpenAI-compatible) |

**Integración:**
- API unificada compatible con OpenAI
- Routing cognitivo distribuido entre ambos runtimes
- Asignación de tareas basada en capacidades

---

## 7. OBSERVABILIDAD (EN PROGRESO)

### 7.1. Stack Planificado

| Componente | Función |
|------------|---------|
| Prometheus | Métricas y alertas |
| Grafana | Dashboards de visualización |
| Loki | Agregación de logs |
| Promtail | Recolección de logs |
| Node Exporter | Métricas de sistema |
| cAdvisor | Métricas de contenedores |

### 7.2. Objetivos de Observabilidad

- **Operational Reasoning** — El sistema razona sobre su propio estado
- **Anomaly Detection** — Detección de anomalías en infraestructura
- **Historical Analysis** — Análisis histórico de rendimiento
- **Telemetry-aware Orchestration** — Orquestación basada en telemetría en tiempo real

---

## 8. COGNICIÓN DISTRIBUIDA

### 8.1. Estado Actual (Implementado)

- Registro distribuido de nodos
- Enrutamiento consciente de capacidades
- Distribución cognitiva de cargas de trabajo
- Puntuación de nodos (node scoring)
- Orquestación de workflows
- Simulación distribuida

### 8.2. Próximas Fases (Planificado)

| Fase | Funcionalidad |
|------|---------------|
| **Phase 6** | Distributed Workflows, Execution Coordination, Task Aggregation, Failover Routing, Async Orchestration |
| **Phase 7** | Autonomous Remediation, Operational Reasoning, Infrastructure Cognition, Adaptive Workflows |
| **Phase 8** | Multi-Agent Coordination, Distributed Cognition Mesh, Cooperative Reasoning, Autonomous Planning |

### 8.3. Visión Multiagente Futura

```
planner-agent
    |
    +-- reasoning-agent
    +-- coding-agent
    +-- security-agent
    +-- documentation-agent
    +-- execution-agent
```

Coordinación autónoma distribuida entre agentes especializados.

---

## 9. ARQUITECTURA DE ALMACENAMIENTO

### 9.1. Modelos de IA

**Ruta:** `/mnt/ai-models`

**Contenido:**
- Modelos Ollama
- Embeddings
- Datasets
- Memoria cognitiva persistente

### 9.2. Repositorio Git

**Ruta:** `/opt/ai-lab`

**Incluye:**
- Runtime completo
- Definiciones de workflows
- Sistema de cognición distribuida
- Gobernanza
- Orquestación
- Sistemas de memoria

**Excluye (.gitignore):**
- Datasets
- Logs
- Artefactos de runtime
- Binarios de modelos

---

## 10. FILOSOFÍA DE DISEÑO

### 10.1. Principios Fundamentales

| Principio | Descripción |
|-----------|-------------|
| **Local First** | Todo el runtime ejecuta local, privado, auto-gestionado, soberano |
| **Modular** | Separación explícita entre cognición, memoria, ejecución, gobernanza, workflows, orquestación e infraestructura |
| **Crecimiento Cognitivo Incremental** | Evolución por capas progresivas |

### 10.2. Mapa de Evolución

```
1. Infrastructure      →  Hardware, red, virtualización
2. Knowledge           →  Modelos, datos, embeddings
3. Memory              →  Semántica + episódica
4. Governance          →  Perfiles, auditoría, seguridad
5. Workflows           →  Planificación, ejecución
6. Distributed Cog.    →  Routing, orquestación, coordinación  ← ACTUAL
7. Autonomous Ops.     →  Remedación, razonamiento operacional
8. Multi-Agent         →  Malla cognitiva, agentes especializados
```

---

## 11. HOJA DE RUTA

| Fase | Estado | Hito |
|------|--------|------|
| Infrastructure | ✅ Completado | Servidores, red, virtualización |
| Knowledge | ✅ Completado | Modelos, embeddings, datasets |
| Memory | ✅ Completado | Qdrant + episodic memory |
| Governance | ✅ Completado | 3 perfiles, audit trail |
| Workflows | ✅ Completado | Planner + engine |
| Distributed Cognition | ✅ Completado | Routing + orchestration |
| **Phase 6: Distributed Exec.** | 🔄 En progreso | Coordinador de ejecución distribuida |
| Phase 7: Autonomous Ops. | 📋 Planificado | Automatización autónoma |
| Phase 8: Multi-Agent | 📋 Planificado | Malla de agentes cognitivos |

**Hito actual:** Distributed Execution Coordinator

---

## 12. ESPECIFICACIONES TÉCNICAS CLAVE

### 12.1. Capacidad de Cómputo Total

| Recurso | Total |
|---------|-------|
| GPUs | 3 (RX780M + RX7900XT + RX9070) |
| VRAM total | ~36.75 GB |
| Nodos | 3 (NAS + 2 GPU) |
| Nodo de orquestación | 1 (Ubuntu Server) |

### 12.2. Stack de Software

| Categoría | Tecnologías |
|-----------|-------------|
| Contenerización | Docker + Portainer |
| Proxy | Traefik |
| Frontend IA | Open WebUI |
| Inferencia CPU | Ollama |
| Inferencia GPU | LM Studio (API OpenAI) |
| Vector DB | Qdrant |
| Embeddings | sentence-transformers |
| Observabilidad | Prometheus + Grafana + Loki (planificado) |
| Versionado | Git (self-hosted) |

---

## 13. CASOS DE USO ACTUALES

1. **Chat/Asistencia local** — Open WebUI + Ollama + LM Studio
2. **Razonamiento y generación de código** — RX7900XT
3. **Procesamiento multimodal/visión** — RX9070
4. **Búsqueda semántica RAG** — Qdrant + embeddings
5. **Automatización de infraestructura** — Workflows cognitivos
6. **Auditoría y trazabilidad** — Governance Runtime + Episodic Memory
7. **Orquestación distribuida** — Routing + Node Scoring

---

## 14. FORTALEZAS TÉCNICAS DIFERENCIADORAS

1. **Local-first soberano** — Sin dependencia de cloud externo, datos bajo control total
2. **Arquitectura cognitiva distribuida** — No es un monstruo, es un clúster cognitivo
3. **Gobernanza por perfiles** — Sandbox → Pilot → Production con trazabilidad total
4. **Memoria dual** — Semántica (RAG) + Episódica (eventos), capacidad de aprendizaje continuo
5. **Routing basado en capacidades** — Cada tarea al nodo óptimo automáticamente
6. **Coste energético y económico reducido** — Hardware heterogéneo aprovechado al máximo
7. **Evolución incremental** — Diseñado para crecer sin reescribir
8. **Stack 100% open source** — Sin licencias propietarias
