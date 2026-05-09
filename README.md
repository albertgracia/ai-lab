# AI Lab Homelab

Laboratorio local de IA para homelab.

Componentes previstos:
- Traefik
- Ollama
- Open WebUI
- Qdrant
- PostgreSQL
- Grafana
- Prometheus
- Loki
AI Lab — Arquitectura, Estado Actual y Roadmap Futuro
? Visión del Proyecto
El objetivo del AI Lab no es simplemente ejecutar modelos LLM locales, sino construir una:
Plataforma Cognitiva Operacional para Homelab
Un sistema capaz de:
    • ejecutar inferencia IA local; 
    • mantener memoria operacional; 
    • razonar sobre infraestructura; 
    • cargar capacidades dinámicamente; 
    • automatizar workflows; 
    • aprender del estado del sistema; 
    • operar como un “AI Operations Brain”. 

?? Arquitectura Actual
Infraestructura Base
Host
Windows 11
??? Hyper-V
VM Principal
Ubuntu Server 24.04 LTS
Virtualización
Hyper-V VM dedicada

? Stack Base Docker
Reverse Proxy
Traefik
Funciones:
    • reverse proxy central; 
    • routing dinámico; 
    • dashboard; 
    • futura terminación TLS; 
    • integración Docker labels. 
Endpoints futuros:
openwebui.local
grafana.local
qdrant.local
portainer.local

Gestión Docker
Portainer
Funciones:
    • gestión visual; 
    • logs; 
    • stacks; 
    • redes; 
    • debugging; 
    • administración de contenedores. 

? Stack IA Actual
Open WebUI
Rol:
Frontend unificado IA
Funciones:
    • interfaz chat; 
    • multi-model; 
    • conexiones API; 
    • futura knowledge base; 
    • futura integración RAG. 

Ollama
Rol:
Motor local de inferencia CPU
Uso:
    • modelos ligeros; 
    • embeddings; 
    • inferencia persistente; 
    • automatización. 
Modelos previstos:
qwen2.5
mistral
deepseek-coder
llama3

LM Studio
Rol:
Motor GPU externo
Arquitectura:
Windows GPU Workstation
??? OpenAI-compatible API
Integración:
Open WebUI
? LM Studio API

? Arquitectura de Storage
Sistema
LVM
Distribución:
ubuntu-lv     ? sistema operativo
ai-models LV  ? modelos IA

Volumen IA
/mnt/ai-models
Uso:
    • modelos Ollama; 
    • embeddings; 
    • futuros datasets; 
    • memoria persistente. 

? Acceso y Gestión
SSH
Administración principal.

SMB
Share Windows:
\\192.168.1.30\ai-lab
Permite:
    • edición desde VSCode; 
    • gestión de compose; 
    • workflows; 
    • skills; 
    • runtime. 

? Git Infrastructure
Repositorio:
/opt/ai-lab
Contiene:
docker stacks
configs
runtime cognitivo
skills
workflows
Excluye:
data/
logs/
modelos/
runtime artifacts

? Arquitectura Cognitiva
Runtime .agent
Tu .agent ya constituye una:
Arquitectura Cognitiva Modular

Estructura Actual
.agent/
??? agents/
??? skills/
??? workflows/
??? rules/
??? scripts/
??? ARCHITECTURE.md

? Agents
Especialistas cognitivos:
backend-specialist
frontend-specialist
debugger
security-auditor
devops-engineer
orchestrator
...
Responsabilidad:
    • razonamiento especializado; 
    • identidad operacional; 
    • coordinación multiagente futura. 

? Skills
Capacidades modulares cargables dinámicamente.
Ejemplos:
docker-expert
systematic-debugging
deployment-procedures
bash-linux
database-design
performance-profiling
Objetivo futuro:
semantic skill loading

? Workflows
Procesos ejecutables.
Ejemplos:
/debug
/deploy
/orchestrate
/test
/plan

? Rules
Gobernanza global:
GEMINI.md
Funciones:
    • restricciones; 
    • políticas; 
    • alignment; 
    • comportamiento persistente. 

? Estado Cognitivo Actual
Actualmente:
.agent = knowledge layer
Todavía NO:
    • routing dinámico; 
    • selección automática; 
    • ejecución multiagente; 
    • orchestration runtime. 

? Roadmap Futuro
FASE 1 — Consolidación (Actual)
? VM Ubuntu
? Docker
? Traefik
? Portainer
? Open WebUI
? Ollama
? LM Studio Integration
? SMB
? Git
? LVM IA
? Runtime .agent

FASE 2 — Knowledge & RAG
Objetivo
Convertir .agent en conocimiento semántico vivo.

Componentes
Qdrant
Rol:
Vector Database
Funciones:
    • embeddings; 
    • búsqueda semántica; 
    • memoria contextual. 

Embeddings
Modelo previsto:
nomic-embed-text-v1.5

Flujo
User Prompt
    ?
Embedding
    ?
Vector Search
    ?
Relevant Skills
    ?
Prompt Augmentation
    ?
LLM

FASE 3 — Agent Runtime
Objetivo
Crear runtime cognitivo real.

Arquitectura prevista
Open WebUI
    ?
Agent Runtime API
    ?
Semantic Router
    ?
Workflow Engine
    ?
LLM Backend

Nuevos módulos
runtime/
??? router.py
??? orchestrator.py
??? workflow_engine.py
??? loader.py
??? embeddings.py
??? memory.py

FASE 4 — Observabilidad
Stack previsto
Prometheus
Grafana
Loki
Promtail
Node Exporter
cAdvisor

Objetivo
Permitir:
    • análisis histórico; 
    • correlación eventos; 
    • reasoning operacional; 
    • detección anomalías. 

FASE 5 — Knowledge Graph
Objetivo
Memoria relacional persistente.

Tecnología prevista
Neo4j

Ejemplo
Traefik
 ??? USES_PORT ? 443
 ??? DEPENDS_ON ? docker network
 ??? EXPOSES ? Open WebUI

FASE 6 — MCP Integration
Objetivo
Dar herramientas reales al runtime.

Herramientas futuras
filesystem
docker
git
grafana
prometheus
shell
browser automation
proxmox

FASE 7 — Multi-Agent Orchestration
Objetivo
Coordinación real entre agentes especializados.

Ejemplo
planner-agent
    ?
devops-agent
    ?
security-agent
    ?
testing-agent
    ?
documentation-agent

? Objetivo Final
Construir una:
Plataforma Cognitiva Operacional Local
capaz de:
    • razonar sobre infraestructura; 
    • cargar capacidades dinámicamente; 
    • mantener memoria persistente; 
    • ejecutar workflows; 
    • automatizar operaciones; 
    • aprender del estado del sistema; 
    • operar como un “AI Operations Brain”. 

? Filosofía del Proyecto
Principios
Modularidad
Separar:
knowledge
behavior
execution
policy
memory
workflow

Local First
Todo ejecutado:
local
private
self-hosted

Incremental Growth
Construir por capas:
infraestructura
? conocimiento
? memoria
? runtime
? automatización
? inteligencia operacional

? Estado Actual del Proyecto
Nivel actual
AI Infrastructure Foundation
Próximo gran salto
Semantic Knowledge + Agent Runtime

