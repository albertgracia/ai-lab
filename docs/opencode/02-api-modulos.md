# AI-LAB: REFERENCIA DE API Y MÓDULOS DEL RUNTIME
## Documentación técnica del código

---

## 1. ROUTER API (FastAPI)

### 1.1. Inicio del Servidor
```bash
# Desde /opt/ai-lab
uvicorn runtime.llm.router_api:app --host 0.0.0.0 --port 8000
# O como script:
python3 -m runtime.llm.router_api
```

### 1.2. Endpoints

#### GET /
Información del servicio.

**Respuesta:**
```json
{
  "service": "AI-LAB Router API",
  "status": "ok",
  "endpoints": ["/health", "/v1/models", "/v1/chat/completions"]
}
```

#### GET /health
Health check del router.

**Respuesta:**
```json
{
  "status": "ok",
  "service": "ai-lab-router-api"
}
```

#### GET /v1/models
Lista los modelos virtuales disponibles.

**Respuesta:**
```json
{
  "object": "list",
  "data": [
    {"id": "ailab-router/auto", "object": "model", "owned_by": "ai-lab"},
    {"id": "ailab-router/fast", "object": "model", "owned_by": "ai-lab"},
    {"id": "ailab-router/reasoning", "object": "model", "owned_by": "ai-lab"},
    {"id": "ailab-router/coding", "object": "model", "owned_by": "ai-lab"}
  ]
}
```

| Model ID | Comportamiento |
|----------|---------------|
| `ailab-router/auto` | Routing automático por detección de intención |
| `ailab-router/fast` | Fuerza nodo rápido (NAS) |
| `ailab-router/reasoning` | Fuerza nodo de razonamiento (RX7900XT) |
| `ailab-router/coding` | Fuerza nodo de código (RX7900XT) |

#### POST /v1/chat/completions
Chat completion con routing automático. Compatible con API de OpenAI.

**Request:**
```json
{
  "model": "ailab-router/auto",
  "messages": [{"role": "user", "content": "Hola"}],
  "max_tokens": 1200,
  "temperature": 0.2,
  "stream": false
}
```

**Response headers:**
- `X-AI-LAB-Selected-Node`: nombre del nodo
- `X-AI-LAB-Selected-Host`: IP del nodo
- `X-AI-LAB-Selected-Model`: modelo usado
- `X-AI-LAB-Capability`: capacidad asignada

**Error (502):**
```json
{
  "error": {
    "message": "Connection refused",
    "type": "ai_lab_router_upstream_error",
    "selected_node": { "name": "...", "host": "...", ... }
  }
}
```

### 1.3. Modelos Virtuales vs Reales

El Router API expone 4 modelos virtuales que mapean a nodos reales:

```
ailab-router/auto     →  select_node() → nodo óptimo según request
ailab-router/fast     →  NAS (.250): gemma-4-e4b
ailab-router/reasoning → RX7900XT (.60): qwen3-14b-reasoning
ailab-router/coding   →  RX7900XT (.60): qwen2.5-coder-32b
```

---

## 2. REFERENCIA DE MÓDULOS

### 2.1. `runtime/agent/`

#### `intent_router.py`
Clasifica la intención del usuario mediante keywords.

**Clases:**
- `RouteResult`: intent, mode, capabilities, context_tags, suggested_model, score

**Funciones:**
- `detect_intent(text: str) → RouteResult`: clasifica texto en intents predefinidos
- `INTENT_RULES`: diccionario con reglas para: coding, operations, research, architecture, security, documentation

#### `context_loader.py`
Carga contexto del sistema.

**Funciones:**
- `build_agent_context(user_request: str) → str`: construye contexto desde archivos de sistema

#### `selective_context.py`
Carga contexto selectivo basado en la ruta de la petición.

**Funciones:**
- `build_selective_context(request_text: str) → str`: carga contexto de .agent/agents/ y .agent/skills/
- `read_file(path: Path) → str`: lee archivos con límite de caracteres
- `load_agent_file(agent_name: str) → Path | None`: carga agente específico

#### `orchestrator.py`
Coordina el plan de orquestación.

**Funciones:**
- `build_orchestration_plan(user_request: str) → dict`: crea plan completo con intent, modo, capacidades, contexto, y registra en audit + episodio

### 2.2. `runtime/audit/`

#### `audit_logger.py`
Sistema de auditoría persistente.

**Archivo:** `runtime/state/governance_audit.jsonl`

**Funciones:**
- `audit_event(event_type: str, payload: dict) → dict`: escribe evento de auditoría

### 2.3. `runtime/distributed/`

#### `cognitive_cluster.py`
Gestión del estado del clúster distribuido.

**Archivo:** `runtime/state/cluster_state.json`

**Funciones:**
- `load_cluster_state() → dict`: carga estado del clúster
- `get_online_nodes(cluster) → list`: filtra nodos online
- `classify_nodes(nodes) → dict`: clasifica por capacidad

#### `task_router.py`
Enrutamiento de tareas distribuidas.

**Constantes:**
- `TASK_CAPABILITY_MAP`: mapea tarea → capacidades requeridas

**Funciones:**
- `select_node(task_type: str) → dict`: selecciona nodo óptimo para tarea

### 2.4. `runtime/execution/`

#### `sandbox_runner.py`
Ejecución controlada de comandos.

**Funciones:**
- `validate_profile_command(profile, command)`: valida comando contra perfil
- `run_safe_command(mode, command, profile_name, timeout) → dict`: ejecuta comando con validación completa

### 2.5. `runtime/llm/`

#### `model_router.py`
Enrutamiento de modelos.

**Constantes:**
- `DEFAULT_MODELS`: mapea capacidad → modelo por defecto

**Funciones:**
- `select_node(request_text, capability)`: selecciona nodo óptimo
- `infer_task(request_text, capability) → str`: infiere tipo de tarea

#### `router_api.py`
Servidor FastAPI (ver sección 1).

**Constantes:**
- `BASE_SYSTEM_CONTEXT`: system prompt base del router

**Funciones:**
- `openai_model_id(node) → str`: genera ID de modelo virtual
- `capability_from_model(model) → str`: extrae capacidad del model ID
- `extract_request_text(payload) → str`: extrae texto plano del payload

#### `invoke.py`
CLI de inferencia directa.

**Uso:**
```bash
python3 runtime/llm/invoke.py "tu pregunta aquí"
```

### 2.6. `runtime/memory/`

#### `episodic_memory.py`
Memoria episódica persistente.

**Archivo:** `runtime/state/episodic_memory.jsonl`

**Funciones:**
- `write_episode(event_type, summary, payload)`: escribe episodio
- `read_episodes(limit=10) → list`: lee últimos N episodios

#### `index_memory.py`
Indexación de memoria en Qdrant.

**Stack:** sentence-transformers + Qdrant

**Colección:** `ai_lab_memory` (vector size: 384, Distance: Cosine)

#### `search_memory.py`
Búsqueda semántica en Qdrant.

**Funciones:**
- `search_memory(query, limit=3) → list`: busca por similitud semántica

### 2.7. `runtime/modes/`

#### `registry.py`
Registro de modos operacionales.

**Modos disponibles:** plan, build, execute

**Funciones:**
- `get_mode(name) → dict`: obtiene configuración de modo
- `list_modes() → list`: lista modos disponibles
- `get_capabilities(name) → set`: obtiene capabilities de un modo

### 2.8. `runtime/nodes/`

#### `node_registry.py`
Registro de nodos del clúster.

**Archivo:** `runtime/nodes/nodes.json`

**Funciones:**
- `load_nodes() → list`: carga todos los nodos
- `enabled_nodes() → list`: carga solo nodos habilitados
- `nodes_with_capability(capability) → list`: filtra por capacidad

#### `healthcheck.py`
Health check del clúster.

**Archivo de salida:** `runtime/state/cluster_state.json`

**Funciones:**
- `check_node(node) → dict`: verifica estado de un nodo via API
- `build_cluster_state() → dict`: construye estado completo del clúster

#### `scheduler.py`
Selección de nodo basada en estado.

**Funciones:**
- `online_nodes() → list`: nodos online desde cluster_state
- `fallback_node(nodes) → dict`: selecciona fallback por latencia + prioridad
- `select_best_node(task) → dict`: selecciona mejor nodo para tarea

### 2.9. `runtime/planner/`

#### `task_planner.py`
Planificador de tareas.

**Clases:**
- `TaskStep`: order, title, mode, profile, capability_required, status
- `TaskPlan`: created_at, user_goal, intent, mode, profile, steps

**Funciones:**
- `infer_profile(mode, intent) → str`: infiere perfil según modo e intención
- `create_task_plan(user_goal) → TaskPlan`: crea plan completo
- `build_steps(user_goal, intent, mode, profile) → list`: construye pasos

#### `tool_planner.py`
Planificador de herramientas.

**Funciones:**
- `plan_tools(user_request) → list`: sugiere comandos según intención

### 2.10. `runtime/policies/`

#### `execution_policy.py`
Políticas de ejecución de comandos.

**Constantes:**
- `DANGEROUS_PATTERNS`: patrones de alto riesgo
- `REQUIRES_EXECUTE_MODE`: comandos que requieren modo execute

**Funciones:**
- `command_risk(command) → str`: clasifica riesgo (low/medium/high)
- `is_command_allowed(mode_name, command) → bool`: verifica si comando está permitido

### 2.11. `runtime/profiles/`

#### `loader.py`
Cargador dinámico de perfiles.

**Funciones:**
- `load_profile(name) → dict`: carga perfil por nombre (sandbox/pilot/production)

#### `sandbox.py`, `pilot.py`, `production.py`
Definiciones de perfiles (ver documento de seguridad para detalles).

### 2.12. `runtime/security/`

#### `capability_guard.py`
Guard de capacidades.

**Constantes:**
- `DANGEROUS_COMMANDS`: lista de comandos prohibidos globalmente

**Funciones:**
- `can_execute_shell(mode) → bool`: verifica si modo permite shell
- `validate_shell_command(mode, command) → bool`: valida comando contra modo

### 2.13. `runtime/state/`

#### `system_state.py`
Constructor de estado del sistema.

**Archivo de salida:** `runtime/state/system_snapshot.json`

**Funciones:**
- `build_system_state() → dict`: construye snapshot completo (Docker + LLM + GPU)

#### `docker_state.py`
**Funciones:** `get_docker_state() → dict`: estado de contenedores Docker

#### `lmstudio_state.py`
**Funciones:** `get_lmstudio_state() → list`: estado de nodos LM Studio

#### `gpu_state.py`
**Funciones:**
- `run_ssh(node, command) → dict`: ejecuta comando SSH en nodo Windows
- `get_gpu_utilization(node) → dict`: uso GPU via typeperf
- `get_vram_usage(node) → dict`: uso VRAM via typeperf
- `build_gpu_state() → list`: estado completo de GPUs

#### `live_state.py`
Loop continuo de snapshots.

### 2.14. `runtime/workflows/`

#### `workflow_engine.py`
Motor de workflows.

**Constantes:**
- `CAPABILITY_TO_DISTRIBUTED_TASK`: mapea capability → tarea distribuida

**Funciones:**
- `create_workflow(user_goal) → dict`: crea workflow completo con routing distribuido

### 2.15. `runtime/rag/`

#### `chunker.py`
Divide texto en chunks.

**Clase:** `Chunk`: source, chunk_id, content, start, end

**Funciones:**
- `split_text(text) → list`: divide texto en chunks con overlap
- `chunk_file(path) → list`: chunker un archivo completo

#### `embedder.py`
Generador de embeddings local.

**Modelo:** `nomic-ai/nomic-embed-text-v1.5`

**Funciones:**
- `embed_text(text) → list`: genera embedding

#### `embedding_pipeline.py`
Pipeline completo de embeddings a Qdrant.

### 2.16. `runtime/router/`

#### `router.py`
Router de agentes basado en keywords.

**Funciones:**
- `classify_agent(user_request) → str`: clasifica agente según texto
- `load_agent_prompt(agent_name) → str`: carga prompt de agente específico

### 2.17. `runtime/search/`

#### `search_agent.py`
Agente de búsqueda en Qdrant.

**Uso:**
```bash
python3 runtime/search/search_agent.py "consulta"
```

### 2.18. `runtime/tools/`

#### `shell_tool.py`
Ejecutor de comandos shell seguros.

**Funciones:**
- `is_safe(command) → bool`: verifica comando contra listas blanca/negra
- `execute(command) → dict`: ejecuta comando si es seguro

---

## 3. ARCHIVOS DE ESTADO DEL SISTEMA

| Archivo | Propósito | Formato |
|---------|-----------|---------|
| `runtime/state/system_snapshot.json` | Snapshot completo del sistema | JSON |
| `runtime/state/cluster_state.json` | Estado del clúster cognitivo | JSON |
| `runtime/state/governance_audit.jsonl` | Auditoría de gobernanza | JSONL |
| `runtime/state/episodic_memory.jsonl` | Memoria episódica | JSONL |
| `runtime/state/embedding_records.json` | Registro de embeddings | JSON |
| `runtime/nodes/nodes.json` | Registro de nodos | JSON |

---

## 4. CLI Y SCRIPTS ÚTILES

```bash
# Inferencia directa
python3 /opt/ai-lab/runtime/llm/invoke.py "pregunta"

# Health check del clúster
python3 /opt/ai-lab/runtime/nodes/healthcheck.py

# Estado del sistema
python3 /opt/ai-lab/runtime/state/system_state.py

# Búsqueda semántica
python3 /opt/ai-lab/runtime/search/search_agent.py "consulta"

# Test de gobernanza
python3 /opt/ai-lab/runtime/security/test_governance.py

# Pipeline de embeddings
python3 /opt/ai-lab/runtime/rag/embedding_pipeline.py

# Indexar conocimiento en Qdrant
python3 /opt/ai-lab/runtime/indexer/index_agent.py
```
