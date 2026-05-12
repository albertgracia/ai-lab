# AI-LAB — Cognitive Router Phase 5

## Objetivo

Convertir el router OpenAI-compatible en un runtime cognitivo multi-agent grounded.

---

# Arquitectura actual

User Request
↓
FastAPI Router API
↓
Intent Router
↓
Agent Selection
↓
Skill Selection
↓
Context Loader
↓
LM Studio Node Routing
↓
LLM Inference
↓
OpenAI-compatible response

---

# Componentes principales

## Router API

Archivo:
runtime/llm/router_api.py

Funciones:
- OpenAI compatibility
- node routing
- context injection
- streaming
- reasoning control

---

## Intent Router

Archivo:
runtime/agent/intent_router.py

Funciones:
- detectar dominio
- seleccionar agente
- seleccionar skills
- detectar complejidad
- detectar multi-agent workflows

---

## Context Loader

Archivo:
runtime/agent/context_loader.py

Funciones:
- cargar OPENCODE
- cargar .agent
- cargar policies
- cargar memories
- truncado inteligente
- grounding operativo

---

## Runtime Memory

Directorios:
memory/semantic
memory/decisions
memory/tasks
memory/summaries

Objetivo:
- persistencia arquitectónica
- continuidad contextual
- grounding histórico

---

## Agent Layer

Directorio:
.agent/

Capas:
- agents
- skills
- workflows
- rules

---

# Capacidades actuales

- OpenAI-compatible API
- Multi-node LM Studio routing
- Dynamic context injection
- Runtime grounding
- Docker awareness
- Infrastructure awareness
- Semantic memory
- Agent specialization
- Workflow routing
- Policy enforcement

---

# Mejoras pendientes

## Phase 6

- weighted semantic routing
- selective context loading
- dynamic token budgeting
- workflow chaining
- multi-agent orchestration
- planner integration
- autonomous tool execution
- MCP integration

---

# Estado

Status:
EXPERIMENTAL BUT OPERATIONAL

Branch:
local-private

Tag:
phase-5-cognitive-agent-router
