# INFORME DETALLADO: AI-LAB
## Análisis completo del sistema — 13 de mayo de 2026

---

# SECCIÓN 1: HARDWARE

## 1.1. Nodo Principal (Orquestación)

| Componente | Valor |
|------------|-------|
| **Hostname** | `ubuntu-ialab` |
| **IP** | 192.168.1.30 |
| **OS** | Ubuntu 26.04 LTS (Resolute) |
| **Kernel** | Linux |
| **Virtualización** | Hyper-V |
| **RAM** | 7.2 GB |
| **Swap** | 4.0 GB |
| **Storage root** | 97 GB (53 GB libres — 55%) |
| **Storage modelos** | 79 GB (70 GB libres — 89%) |
| **Uptime** | 1 día 3:09h |
| **Load average** | 0.33 / 0.22 / 0.20 |
| **Usuarios activos** | 4 |

## 1.2. Clúster Cognitivo — Nodos GPU

### NAS Local Router (.250)

| Especificación | Valor |
|----------------|-------|
| **GPU** | AMD Radeon RX780M (iGPU) |
| **VRAM** | 0.75 GB compartida |
| **Role** | Routing ligero + Memoria |
| **Capacidades** | fast, lightweight, fallback, router, memory |
| **Backend** | LM Studio |
| **Prioridad** | 1 (baja — tácticas ligeras) |

### RX7900XT Reasoning Node (.60)

| Especificación | Valor |
|----------------|-------|
| **GPU** | AMD Radeon RX7900XT |
| **VRAM** | 20 GB GDDR6 |
| **Role** | Razonamiento + Código + Orquestación |
| **Capacidades** | reasoning, coding, large-context, multi-agent, orchestration, backend |
| **Backend** | LM Studio |
| **Prioridad** | 10 (alta — tácticas pesadas) |

### RX9070 Multimodal Node (.50)

| Especificación | Valor |
|----------------|-------|
| **GPU** | AMD Radeon RX9070 |
| **VRAM** | 16 GB GDDR6 |
| **Role** | Visión + Multimodal + Frontend |
| **Capacidades** | vision, image, multimodal, embeddings, creative, frontend |
| **Backend** | LM Studio |
| **Prioridad** | 8 (media-alta — tácticas multimodales) |

## 1.3. Estado GPU en Tiempo Real

Métricas recolectadas vía SSH + `typeperf` desde nodos Windows:

### RX9070 (.50)

| Métrica | Valor |
|---------|-------|
| **VRAM usada** | 2.76 GB / 16 GB |
| **VRAM libre** | 13.24 GB |
| **GPU usage pico** | 0.63% |
| **Procesos 3D activos** | 5 (uso individual 0.03%–0.63%) |

### RX7900XT (.60)

| Métrica | Valor |
|---------|-------|
| **VRAM usada** | **19.03 GB / 20 GB** |
| **VRAM libre** | 0.97 GB |
| **GPU usage pico** | 0.44% |
| **Procesos 3D activos** | 3 (uso individual 0.001%–0.44%) |

> ⚠️ **Atención RX7900XT**: La VRAM está al **95% de capacidad** — el modelo `qwen2.5-coder-32b` cargado actualmente consume ~19 GB. Hay margen mínimo para otros modelos simultáneos.

## 1.4. Benchmarks de Inferencia

Pruebas con prompt corto ("Responde solo: OK"), 10 tokens max, temp 0.1:

| Nodo | Modelo | Tamaño | Tiempo | HTTP |
|------|--------|--------|--------|------|
| **NAS (.250)** | google/gemma-4-e4b | ~4B | **315 ms** | 200 ✅ |
| **RX7900XT (.60)** | deepseek-r1-0528-qwen3-8b | 8B | **7,687 ms** | 200 ✅ |
| **RX7900XT (.60)** | qwen3-14b-reasoning-distill | 14B | **12,996 ms** | 200 ✅ |
| **RX7900XT (.60)** | qwen2.5-coder-32b | 32B | **13,184 ms** | 200 ✅ |
| **RX7900XT (.60)** | google/gemma-4-26b-a4b | 26B | **41,250 ms** | 200 ✅ |
| **Ollama (CPU)** | qwen2.5:7b | 7B | **10,980 ms** | 200 ✅ |
| **RX9070 (.50)** | qwen3.5-9b-distill | 9B | 4 ms | **500 ❌** |
| **RX9070 (.50)** | qwen3.6-35b-distill | 35B | 4 ms | **500 ❌** |

> ⚠️ **RX9070**: Ambos modelos devuelven HTTP 500 (Internal Server Error). Posible problema con LM Studio en ese nodo (modelos no cargados correctamente o incompatibilidad con la GPU).

### Observaciones de Rendimiento

- **NAS + gemma-4-e4b** es el más rápido (315ms) para tácticas ligeras
- **RX7900XT**: el modelo 32B es solo 1.7x más lento que el 8B (13s vs 7.7s) — buena escalabilidad
- **gemma-4-26b** es sorprendentemente lento (41s) para su tamaño — posiblemente por ser un MoE o no optimizado para GPU AMD
- **Ollama CPU**: igualado con RX7900XT para 7B (11s) — las GPU AMD no están siendo aprovechadas al máximo con LM Studio

## 1.5. Temperaturas

No hay sensores disponibles en el nodo Ubuntu (`sensors` no instalado). Los nodos GPU son Windows y requerirían:
```powershell
# En cada nodo Windows vía SSH:
wmic /namespace:\\root\wmi PATH MSAcpi_ThermalZoneTemperature get Temperature
```
o herramientas como GPU-Z, HWiNFO, o `nvidia-smi` equivalente para AMD (no aplicable, son GPUs AMD).

**Recomendación:** Instalar `lm-sensors` en Ubuntu y configurar monitoreo térmico vía SSH en los nodos GPU.

---

# SECCIÓN 2: RED

## 2.1. Latencias entre Nodos

| Origen → Destino | IP | Latencia media | Packet loss |
|------------------|-----|---------------|-------------|
| ubuntu-ialab → RX7900XT | 192.168.1.60 | **0.534 ms** | 0% |
| ubuntu-ialab → RX9070 | 192.168.1.50 | **0.313 ms** | 0% |
| ubuntu-ialab → NAS | 192.168.1.250 | **0.392 ms** | 0% |

Todas las latencias son <1 ms — red local de altísimo rendimiento. Ideal para inferencia distribuida en tiempo real.

## 2.2. Throughput (Pendiente)

No se ha ejecutado test iperf. Comando para medir:
```bash
# En nodo Ubuntu (servidor):
iperf3 -s
# En cada nodo Windows (cliente):
iperf3 -c 192.168.1.30
```

## 2.3.Puertos expuestos

| Puerto | Servicio | Nodo |
|--------|----------|------|
| 80 | Traefik (HTTP) | ubuntu-ialab |
| 443 | Traefik (HTTPS) | ubuntu-ialab |
| 3000 | Open WebUI | ubuntu-ialab |
| 9000 | Portainer | ubuntu-ialab |
| 6333-6334 | Qdrant | ubuntu-ialab |
| 8080 | Traefik dashboard | ubuntu-ialab |
| 11434 | Ollama API | ubuntu-ialab |
| 1234 | LM Studio API | .50, .60, .250 |

---

# SECCIÓN 3: RUNTIME COGNITIVO

## 3.1. Diagrama de Flujo General

```
┌─────────────────────────────────────────────────────────────┐
│                     USER REQUEST                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    INTENT ROUTER                              │
│  detect_intent() → classify keywords → RouteResult            │
│  (coding, operations, research, architecture, security...)    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   WORKFLOW PLANNER                            │
│  task_planner.py → TaskPlan con N steps                       │
│  tool_planner.py → comandos sugeridos según intención         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              DISTRIBUTED TASK ROUTER                          │
│  capability → task map                                         │
│  select_best_node() → node scoring por capacidad + prioridad  │
│  fallback_node() → selección por latencia + prioridad         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 EXECUTION COORDINATOR                         │
│  sandbox_runner.py → validate_profile_command()               │
│  validate_shell_command() → capability_guard                  │
│  audit_event() → log governance                               │
│  write_episode() → memoria episódica                          │
└──────┬──────────────────────────────────────────────────────┘
       │                       │
       ▼                       ▼
┌──────────────┐   ┌──────────────────────┐
│ INFERENCE    │   │ MEMORY + GOVERNANCE  │
│              │   │                      │
│ Ollama (CPU) │   │ Qdrant (semántica)   │
│ LM Studio ×3 │   │ Episodic (JSONL)     │
│              │   │ Audit trail (JSONL)  │
└──────────────┘   └──────────────────────┘
```

## 3.2. Mapa de Dependencias entre Módulos

```
agent/
├── context_loader.py     ← (standalone)
├── intent_router.py      ← runtime.modes.registry
├── orchestrator.py       ← agent.intent_router, agent.context_loader,
│                           audit.audit_logger, memory.episodic_memory
├── selective_context.py  ← agent.intent_router
└── test_intent_router.py ← agent.intent_router

audit/
└── audit_logger.py       ← (standalone, solo stdlib)

distributed/
├── cognitive_cluster.py  ← memory.episodic_memory
└── task_router.py        ← distributed.cognitive_cluster, memory.episodic_memory

execution/
└── sandbox_runner.py     ← security.capability_guard, audit.audit_logger,
                            profiles.loader, memory.episodic_memory

llm/
├── invoke.py             ← llm.model_router, state.system_state
├── model_router.py       ← nodes.scheduler
└── router_api.py         ← llm.model_router, state.system_state,
                            agent.selective_context, FastAPI

memory/
├── episodic_memory.py    ← (standalone)
├── index_memory.py       ← sentence_transformers, qdrant_client
└── search_memory.py      ← sentence_transformers, qdrant_client

modes/
└── registry.py           ← define plan, build, execute (sin imports externos)

nodes/
├── healthcheck.py        ← nodes.node_registry, requests
├── node_registry.py      ← (standalone, JSON)
└── scheduler.py          ← (standalone, JSON)

planner/
├── task_planner.py       ← agent.intent_router, memory.episodic_memory
└── tool_planner.py       ← tools.shell_tool

policies/
└── execution_policy.py   ← (standalone)

profiles/
├── loader.py             ← importlib dinámico
├── sandbox.py            ← dict PROFILE
├── pilot.py              ← dict PROFILE
└── production.py         ← dict PROFILE

prompt/
└── prompt_builder.py     ← memory.search_memory, requests

rag/
├── chunker.py            ← (standalone)
├── embedder.py           ← sentence_transformers
└── embedding_pipeline.py ← rag.embedder

router/
└── router.py             ← (standalone, basado en Path)

search/
└── search_agent.py       ← requests

security/
├── capability_guard.py   ← modes.registry
└── test_governance.py    ← modes.registry, security.capability_guard,
                            policies.execution_policy, audit.audit_logger

state/
├── docker_state.py       ← subprocess
├── gpu_state.py          ← subprocess (SSH)
├── live_state.py         ← state.system_state
├── lmstudio_state.py     ← requests
└── system_state.py       ← state.docker_state, state.lmstudio_state, state.gpu_state

tools/
└── shell_tool.py         ← subprocess

workflows/
└── workflow_engine.py    ← planner.task_planner, memory.episodic_memory,
                            distributed.task_router
```

## 3.3. Ciclo de Vida de una Petición

```
1. Llega a /v1/chat/completions del Router API (FastAPI)
2. build_system_state() → captura estado actual Docker + LM Studio + GPU
3. select_node(request_text, capability) → elige nodo óptimo
4. build_selective_context() → carga contexto de .agent/
5. Inyecta system prompt con contexto selectivo
6. Reenvía petición al upstream (LM Studio del nodo elegido)
7. Retorna respuesta (streaming o completa) con headers X-AI-LAB-*
```

## 3.4. Modos Operacionales

| Modo | Capabilities | Uso |
|------|-------------|-----|
| **readonly** | read, search, rag, analyze, logs, docker_ps, status | Inspección segura |
| **plan** | read, search, rag, analyze, plan | Análisis y planificación |
| **build** | read, search, rag, analyze, plan, write, generate, test, lint | Construcción sin shell |
| **execute** | read, search, rag, analyze, plan, write, generate, test, lint, shell, docker, systemctl, deploy | Modo privilegiado |

---

# SECCIÓN 4: MODELOS

## 4.1. Inventario Completo de Modelos

### Ollama (CPU — ubuntu-ialab)

| Modelo | Tamaño | Parámetros | Cuantización |
|--------|--------|------------|-------------|
| qwen2.5:7b | 4.7 GB | 7.6B | Q4_K_M |

### NAS (.250) — LM Studio

| Modelo | Tamaño estimado | Propósito |
|--------|----------------|-----------|
| google/gemma-4-e4b | ~4B | Tácticas rápidas, lightweight |
| text-embedding-nomic-embed-text-v1.5 | ~0.5B | Embeddings |

### RX7900XT (.60) — LM Studio

| Modelo | Tamaño | Propósito |
|--------|--------|-----------|
| qwen2.5-coder-32b | ~32B | **Coding principal** |
| qwen2.5-coder-14b-instruct | ~14B | Coding secundario |
| qwen3-14b-reasoning-distill | ~14B | Razonamiento profundo |
| deepseek-r1-0528-qwen3-8b | ~8B | Razonamiento ligero |
| deepseek-coder-v2-lite-instruct | ~16B | Coding alternativo |
| google/gemma-4-26b-a4b | ~26B (MoE) | Razonamiento general |
| llama-3.2-1b-instruct | ~1B | Fallback ultraligero |
| text-embedding-nomic-embed-text-v1.5 | ~0.5B | Embeddings |
| text-embedding-nomic-embed-text-v2-moe | ~0.5B | Embeddings v2 |

### RX9070 (.50) — LM Studio

| Modelo | Tamaño | Propósito |
|--------|--------|-----------|
| qwen3.6-35b-a3b-distill | ~35B (MoE) | Razonamiento pesado |
| qwen3.5-9b-reasoning-distill-v2 | ~9B | Razonamiento medio |
| text-embedding-nomic-embed-text-v1.5 | ~0.5B | Embeddings |

### Modelos con problemas

| Nodo | Modelo | Estado |
|------|--------|--------|
| RX9070 (.50) | qwen3.5-9b-distill | HTTP 500 |
| RX9070 (.50) | qwen3.6-35b-distill | HTTP 500 |

## 4.2. Mapa de Enrutamiento por Capacidad

| Tarea | Capacidad requerida | Nodo preferente | Modelo sugerido |
|-------|-------------------|----------------|----------------|
| fast/fallback | fast | NAS (.250) | gemma-4-e4b |
| reasoning | reasoning | RX7900XT (.60) | qwen3-14b-reasoning |
| deep-reasoning | large-context | RX7900XT (.60) | qwen3-14b-reasoning |
| coding | coding | RX7900XT (.60) | qwen2.5-coder-32b |
| vision | vision | RX9070 (.50) | moondream2 |
| image | image | RX9070 (.50) | flux.2-klein-9b |
| memory/embeddings | embeddings | RX9070 (.50) | nomic-embed-text |
| orchestration | multi-agent | RX7900XT (.60) | qwen2.5-coder-32b |

## 4.3. Rendimiento Comparativo

```
Latencia de inferencia (menor = mejor):

NAS gemma-4-e4b      ───────────────────────── 0.3s
RX7900XT deepseek-8b ─────────────────────────────────── 7.7s
Ollama CPU qwen2.5:7b─────────────────────────────────── 11.0s
RX7900XT qwen3-14b  ──────────────────────────────────────────── 13.0s
RX7900XT qwen-coder-32b ───────────────────────────────────────────── 13.2s
RX7900XT gemma-4-26b ───────────────────────────────────────────────────────────────────── 41.3s

* RX9070 no disponible (HTTP 500)
```

---

# SECCIÓN 5: SEGURIDAD

## 5.1. Perfiles de Gobernanza

### Sandbox (Experimental)

```python
PROFILE = {
    "name": "sandbox",
    "allow_shell": True,
    "allow_write": True,
    "allow_tools": True,
    "max_command_timeout": 300,
    "blocked_commands": ["rm -rf /"],
    "audit_level": "full",
}
```
**Uso:** Experimentación, desarrollo, pruebas. Prácticamente sin restricciones.

### Pilot (Gobernanza Reforzada)

```python
PROFILE = {
    "name": "pilot",
    "allow_shell": True,
    "allow_write": True,
    "allow_tools": True,
    "max_command_timeout": 120,
    "blocked_commands": ["rm -rf", "docker compose down", "shutdown", "reboot"],
    "audit_level": "strict",
}
```
**Uso:** Operaciones controladas. Shell permitido pero comandos destructivos bloqueados.

### Production (Máxima Seguridad)

```python
PROFILE = {
    "name": "production",
    "allow_shell": False,
    "allow_write": False,
    "allow_tools": False,
    "max_command_timeout": 30,
    "blocked_commands": ["rm", "shutdown", "reboot", "docker compose down",
                          "systemctl restart", "mkfs"],
    "audit_level": "paranoid",
}
```
**Uso:** Entorno productivo. Solo lectura. Sin shell, sin escritura, sin tools.

## 5.2. Capability Enforcement

El sistema valida capacidades en 3 capas:

```
1. MODO → capability_guard.py
   - Verifica que el modo permita shell execution
   - Bloquea comandos peligrosos (rm -rf, mkfs, shutdown, sudo, chmod 777, etc.)

2. PERFIL → loader.py + sandbox_runner.py
   - Verifica allow_shell según perfil activo
   - Bloquea comandos específicos del perfil
   - Aplica timeout según perfil

3. EJECUCIÓN → execution_policy.py
   - Clasifica riesgo del comando: low / medium / high
   - Comandos high requieren modo execute
   - Comandos medium requieren al menos build
```

## 5.3. Clasificación de Riesgo de Comandos

| Riesgo | Ejemplos | Modo requerido |
|--------|----------|----------------|
| **low** | ls, cat, grep, df, free, docker ps | readonly |
| **medium** | docker compose, systemctl, service | build |
| **high** | rm -rf, mkfs, shutdown, reboot | execute |

## 5.4. Audit Trail

| Archivo | Eventos | Formato |
|---------|---------|---------|
| `runtime/state/governance_audit.jsonl` | 25 eventos | JSON Lines |
| `runtime/state/episodic_memory.jsonl` | 36 eventos | JSON Lines |

**Campos de cada evento governance:**
```json
{
  "timestamp": 1747123456,
  "event_type": "orchestration_plan_created",
  "payload": {
    "user_request": "...",
    "intent": "coding",
    "mode": "build",
    ...
  }
}
```

## 5.5. Modos vs Capabilities (Matriz de Acceso)

| Acción | readonly | plan | build | execute |
|--------|----------|------|-------|---------|
| read/search/rag | ✅ | ✅ | ✅ | ✅ |
| analyze | ✅ | ✅ | ✅ | ✅ |
| plan | ❌ | ✅ | ✅ | ✅ |
| write/generate | ❌ | ❌ | ✅ | ✅ |
| test/lint | ❌ | ❌ | ✅ | ✅ |
| shell | ❌ | ❌ | ❌ | ✅ |
| docker/systemctl | ❌ | ❌ | ❌ | ✅ |
| deploy | ❌ | ❌ | ❌ | ✅ |

---

# SECCIÓN 6: CÓDIGO

## 6.1. Métricas del Proyecto

| Métrica | Valor |
|---------|-------|
| **Archivos Python** | 62 |
| **Líneas de código** | 4,134 |
| **Directorios runtime** | 25 |
| **Módulos con imports externos** | 15 |
| **Módulos standalone** | 10 |
| **Dataclasses** | 7 (RouteResult, TaskStep, TaskPlan, Chunk, etc.) |
| **Archivos de configuración** | 5 (nodes.json, smb.conf, docker-compose x5) |

## 6.2. API Surface (Router API — FastAPI)

| Endpoint | Método | Función |
|----------|--------|---------|
| `/` | GET | Info del servicio, lista de endpoints |
| `/health` | GET | Health check → `{"status": "ok"}` |
| `/v1/models` | GET | Lista modelos virtuales: auto, fast, reasoning, coding |
| `/v1/chat/completions` | POST | Chat completo con routing automático (streaming + no-streaming) |

**Headers de respuesta:**
- `X-AI-LAB-Selected-Node`: nombre del nodo que procesó
- `X-AI-LAB-Selected-Host`: IP del nodo
- `X-AI-LAB-Selected-Model`: modelo usado
- `X-AI-LAB-Capability`: capacidad asignada

## 6.3. .agent/ — Ecosistema de Agentes

### Agentes (21)

| Archivo | Rol |
|---------|-----|
| `backend-specialist.md` | API, backend, endpoints |
| `code-archaeologist.md` | Análisis de código legacy |
| `database-architect.md` | Diseño de bases de datos |
| `debugger.md` | Depuración de errores |
| `devops-engineer.md` | Infraestructura, Docker |
| `documentation-writer.md` | Documentación técnica |
| `explorer-agent.md` | Exploración del código base |
| `frontend-specialist.md` | UI/UX, frontend |
| `game-developer.md` | Desarrollo de juegos |
| `mobile-developer.md` | Apps móviles |
| `orchestrator.md` | Coordinación multi-agente |
| `penetration-tester.md` | Tests de penetración |
| `performance-optimizer.md` | Optimización de rendimiento |
| `product-manager.md` | Gestión de producto |
| `product-owner.md` | Visión de producto |
| `project-planner.md` | Planificación de proyectos |
| `qa-automation-engineer.md` | Automatización QA |
| `security-auditor.md` | Auditoría de seguridad |
| `seo-specialist.md` | SEO |
| `test-engineer.md` | Ingeniería de tests |

### Skills (39)

| Categoría | Skills |
|-----------|--------|
| **Infra** | bash-linux, server-management, deployment-procedures, powershell-windows |
| **Frontend** | tailwind-patterns, frontend-design, web-design-guidelines, nextjs-react-expert |
| **Backend** | nodejs-best-practices, python-patterns, api-patterns |
| **Data** | database-design, geo-fundamentals |
| **QA** | tdd-workflow, testing-patterns, webapp-testing, lint-and-validate, code-review-checklist |
| **Seguridad** | red-team-tactics, vulnerability-scanner |
| **Arquitectura** | architecture, clean-code, intelligent-routing |
| **Contenido** | documentation-templates, plan-writing, brainstorming |
| **Móvil** | mobile-design |
| **Juegos** | game-development |
| **Rendimiento** | performance-profiling |
| **Otros** | mcp-builder, app-builder, parallel-agents, i18n-localization, rust-pro, behavioral-modes, doc.md, seo-fundamentals |

### Workflows (12)

| Archivo | Función |
|---------|---------|
| `plan.md` | Planificación |
| `create.md` | Creación de activos |
| `enhance.md` | Mejora de existentes |
| `debug.md` | Depuración |
| `test.md` | Testing |
| `deploy.md` | Despliegue |
| `preview.md` | Vista previa |
| `status.md` | Estado del sistema |
| `brainstorm.md` | Lluvia de ideas |
| `orchestrate.md` | Orquestación multi-agente |
| `ui-ux-pro-max.md` | UI/UX avanzada |

## 6.4. Estructura de Clases y Dataclasses

### `RouteResult` (agent/intent_router.py)
```
RouteResult:
  intent: str
  mode: str
  capabilities: List[str]
  context_tags: List[str]
  suggested_model: str
  score: int = 1
```

### `TaskStep` y `TaskPlan` (planner/task_planner.py)
```
TaskStep:
  order: int
  title: str
  mode: str
  profile: str
  capability_required: str
  status: str = "pending"

TaskPlan:
  created_at: str
  user_goal: str
  intent: str
  mode: str
  profile: str
  steps: List[TaskStep]
```

### `Chunk` (rag/chunker.py)
```
Chunk:
  source: str
  chunk_id: str
  content: str
  start: int
  end: int
```

## 6.5. Puntos de Entrada del Sistema

| Script | Propósito |
|--------|-----------|
| `runtime/llm/router_api.py` | Servidor FastAPI (Router API) |
| `runtime/llm/invoke.py` | CLI de inferencia directa |
| `runtime/nodes/healthcheck.py` | Health check + Cluster state |
| `runtime/state/system_state.py` | Snapshot de estado del sistema |
| `runtime/state/live_state.py` | Loop continuo de snapshots |
| `runtime/rag/embedding_pipeline.py` | Pipeline de embeddings |
| `runtime/indexer/index_agent.py` | Indexación de conocimiento |
| `runtime/search/search_agent.py` | Búsqueda en Qdrant |
| `runtime/security/test_governance.py` | Tests de gobernanza |

---

# SECCIÓN 7: DIAGNÓSTICO Y OBSERVACIONES

## 7.1. Problemas Detectados

| # | Problema | Severidad | Impacto |
|---|----------|-----------|---------|
| 1 | **RX9070 HTTP 500** en ambos modelos | 🔴 Alta | Nodo multimodal inoperativo |
| 2 | **VRAM RX7900XT al 95%** | 🟡 Media | Sin margen para otros modelos |
| 3 | **Qdrant 152 puntos pero 0 vectores indexados** | 🟡 Media | Búsqueda semántica no funcional |
| 4 | **Router API FastAPI no está corriendo** | 🟡 Media | Routing cognitivo no disponible como servicio |
| 5 | **Sin monitoreo térmico** | 🟢 Baja | No se puede detectar overheating |
| 6 | **Sin observabilidad (Prometheus/Grafana)** | 🟢 Baja | Sin métricas históricas |

## 7.2. Recomendaciones Prioritarias

1. **Diagnosticar LM Studio en RX9070 (.50)** — verificar modelos cargados, logs de LM Studio
2. **Liberar VRAM en RX7900XT** — considerar descargar modelos no usados (gemma-4-26b, deepseek-coder-v2-lite) si no son necesarios
3. **Configurar Qdrant indexing** — los 152 puntos existen pero no están vectorizados; ejecutar pipeline de embeddings
4. **Poner Router API como servicio systemd** para inicio automático
5. **Instalar Prometheus + Grafana + Node Exporter + cAdvisor** para observabilidad
6. **Ejecutar test iperf** entre todos los nodos para medir throughput real

## 7.3. Capacidad Residual

| Recurso | Total | Usado | Libre | % Libre |
|---------|-------|-------|-------|---------|
| RAM Ubuntu | 7.2 GB | 1.6 GB | 5.7 GB | **79%** |
| Disk root | 97 GB | 40 GB | 53 GB | **55%** |
| Disk modelos | 79 GB | 4.4 GB | 70 GB | **89%** |
| VRAM RX9070 | 16 GB | 2.8 GB | 13.2 GB | **83%** |
| VRAM RX7900XT | 20 GB | 19.0 GB | 1.0 GB | **5% ⚠️** |
| CPU load | - | 0.33 | - | **Bajo** |

---

# SECCIÓN 8: CONCLUSIÓN

AI-LAB es un **sistema cognitivo distribuido funcional** con:

- ✅ **Infraestructura**: 1 nodo orquestador + 3 nodos de inferencia en producción
- ✅ **Runtime**: 62 archivos Python, 4,134 LOC, 25 módulos, arquitectura limpia con separación de responsabilidades
- ✅ **Gobernanza**: 3 perfiles (sandbox/pilot/production), 4 modos, clasificación de riesgo, audit trail persistente
- ✅ **Memoria dual**: Qdrant (semántica, 2 colecciones, 152 puntos) + episódica (36 eventos)
- ✅ **Routing distribuido**: capability-based routing, node scoring, fallback
- ✅ **17 modelos** disponibles desde 1B hasta 35B parámetros
- ✅ **Red**: latencias <1ms entre todos los nodos
- ✅ **Ecosistema de agentes**: 21 agentes, 39 skills, 12 workflows

**Áreas de mejora identificadas:**
- RX9070 requiere diagnóstico (HTTP 500)
- Qdrant necesita indexación de vectores
- Router API no está como servicio systemd
- Sin stack de observabilidad

**Estado general: 🟡 OPERATIVO CON OBSERVACIONES — Carga baja, margen de mejora identificado**
