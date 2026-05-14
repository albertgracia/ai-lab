# AI-LAB: ECOSISTEMA .AGENT
## Agentes, Skills y Workflows

---

## 1. VISIÓN GENERAL

El directorio `.agent/` contiene el ecosistema de conocimiento del runtime cognitivo. Está organizado en tres categorías:

```
.agent/
├── agents/       → 21 prompts de agentes especializados
├── skills/       → 39 skills de conocimiento
└── workflows/    → 12 workflows operacionales
```

Estos archivos son cargados por el `selective_context.py` del runtime para proporcionar contexto relevante al modelo de lenguaje según la intención del usuario.

---

## 2. AGENTES (21)

Los agentes son prompts especializados que definen el rol, contexto y comportamiento para diferentes tipos de tareas.

### 2.1. Lista Completa

| # | Agente | Propósito | Keywords |
|---|--------|-----------|----------|
| 1 | **backend-specialist** | APIs, endpoints, backend | api, backend, endpoint, database |
| 2 | **code-archaeologist** | Análisis de código heredado | legacy, refactor, old code |
| 3 | **database-architect** | Diseño de bases de datos | database, schema, query, postgres |
| 4 | **debugger** | Depuración de errores | debug, error, broken, crash, logs |
| 5 | **devops-engineer** | Infraestructura, Docker | deploy, docker, compose, traefik, server |
| 6 | **documentation-writer** | Documentación técnica | docs, documentation, readme |
| 7 | **explorer-agent** | Exploración del código base | explore, codebase, structure |
| 8 | **frontend-specialist** | UI/UX, frontend | frontend, ui, css, react, vue |
| 9 | **game-developer** | Desarrollo de juegos | game, unity, godot |
| 10 | **mobile-developer** | Apps móviles | mobile, ios, android, flutter |
| 11 | **orchestrator** | Coordinación multi-agente | orchestrate, multi-agent, workflow, coordinate |
| 12 | **penetration-tester** | Tests de penetración | pentest, security test, vulnerability |
| 13 | **performance-optimizer** | Optimización de rendimiento | performance, slow, optimization, bottleneck |
| 14 | **product-manager** | Gestión de producto | product, roadmap, backlog |
| 15 | **product-owner** | Visión de producto | vision, stakeholder, requirements |
| 16 | **project-planner** | Planificación de proyectos | plan, roadmap, architecture, design |
| 17 | **qa-automation-engineer** | Automatización QA | qa, test automation, cypress, selenium |
| 18 | **security-auditor** | Auditoría de seguridad | security, vulnerability, audit, cve |
| 19 | **seo-specialist** | SEO | seo, search engine, ranking |
| 20 | **test-engineer** | Ingeniería de tests | test, unittest, pytest, coverage |

### 2.2. Ejemplo de Contenido

```markdown
# debugger.md
Eres un debugger experto en sistemas distribuidos.

## Capacidades
- Analizar logs de Docker
- Identificar errores de conexión
- Diagnosticar problemas de red
- Encontrar cuellos de botella

## Contexto
El sistema AI-LAB está compuesto por 5 contenedores Docker
y 3 nodos GPU externos conectados via red local.

## Instrucciones
Cuando recibas un error:
1. Identifica el tipo de error (red, recurso, código, configuración)
2. Revisa logs relevantes
3. Propone solución paso a paso
```

---

## 3. SKILLS (39)

Las skills son bloques de conocimiento reutilizables que los agentes pueden cargar según necesidad.

### 3.1. Lista Completa por Categoría

#### Infraestructura y Sistemas
| Skill | Descripción |
|-------|-------------|
| **bash-linux** | Comandos bash, scripting Linux |
| **server-management** | Administración de servidores |
| **deployment-procedures** | Procedimientos de despliegue |
| **powershell-windows** | Scripting PowerShell en Windows |
| **intelligent-routing** | Enrutamiento inteligente del sistema |

#### Frontend y Diseño
| Skill | Descripción |
|-------|-------------|
| **tailwind-patterns** | Patrones de diseño Tailwind CSS |
| **frontend-design** | Diseño de interfaces |
| **web-design-guidelines** | Guías de diseño web |
| **nextjs-react-expert** | Experto en Next.js y React |
| **mobile-design** | Diseño de apps móviles |

#### Backend y APIs
| Skill | Descripción |
|-------|-------------|
| **nodejs-best-practices** | Mejores prácticas Node.js |
| **python-patterns** | Patrones de Python |
| **api-patterns** | Patrones de diseño de APIs |

#### Datos y Bases de Datos
| Skill | Descripción |
|-------|-------------|
| **database-design** | Diseño de bases de datos |
| **geo-fundamentals** | Fundamentos geoespaciales |

#### Calidad y Testing
| Skill | Descripción |
|-------|-------------|
| **tdd-workflow** | Workflow TDD (Test Driven Development) |
| **testing-patterns** | Patrones de testing |
| **webapp-testing** | Testing de aplicaciones web |
| **lint-and-validate** | Linting y validación |
| **code-review-checklist** | Checklist de code review |
| **systematic-debugging** | Depuración sistemática |

#### Seguridad
| Skill | Descripción |
|-------|-------------|
| **red-team-tactics** | Tácticas de equipo rojo |
| **vulnerability-scanner** | Escaneo de vulnerabilidades |

#### Arquitectura y Diseño
| Skill | Descripción |
|-------|-------------|
| **architecture** | Arquitectura de software |
| **clean-code** | Código limpio |
| **behavioral-modes** | Modos de comportamiento del sistema |

#### Contenido y Documentación
| Skill | Descripción |
|-------|-------------|
| **documentation-templates** | Plantillas de documentación |
| **plan-writing** | Redacción de planes |
| **brainstorming** | Técnicas de lluvia de ideas |
| **doc.md** | Documentación general |

#### Juegos
| Skill | Descripción |
|-------|-------------|
| **game-development** | Desarrollo de videojuegos |

#### Rendimiento
| Skill | Descripción |
|-------|-------------|
| **performance-profiling** | Perfilado de rendimiento |

#### Móvil
| Skill | Descripción |
|-------|-------------|
| **mobile-design** | Diseño móvil |

#### Otros
| Skill | Descripción |
|-------|-------------|
| **mcp-builder** | Constructor MCP |
| **app-builder** | Constructor de aplicaciones |
| **parallel-agents** | Agentes paralelos |
| **i18n-localization** | Internacionalización |
| **rust-pro** | Experto en Rust |
| **seo-fundamentals** | Fundamentos SEO |

### 3.2. Ejemplo de Contenido

```markdown
# .agent/skills/bash-linux/SKILL.md
# Bash Linux

## Descripción
Comandos esenciales para administración de sistemas Linux.

## Comandos Básicos
- `ls -la` — listar archivos con detalles
- `grep -r "pattern" /path/` — buscar texto recursivamente
- `df -h` — espacio en disco en formato legible
- `free -h` — uso de memoria RAM
- `ps aux | grep proceso` — buscar proceso activo
- `journalctl -xe` — logs del sistema

## Docker
- `docker ps` — contenedores activos
- `docker logs nombre --tail 50` — últimas líneas de log
- `docker stats --no-stream` — consumo de recursos
```

---

## 4. WORKFLOWS (12)

Los workflows definen secuencias operacionales para tareas comunes.

| # | Workflow | Descripción |
|---|----------|-------------|
| 1 | **plan** | Planificación: analizar, diseñar, documentar |
| 2 | **create** | Creación: generar nuevo código/activos |
| 3 | **enhance** | Mejora: optimizar existente sin romper |
| 4 | **debug** | Depuración: diagnosticar y corregir errores |
| 5 | **test** | Testing: escribir y ejecutar pruebas |
| 6 | **deploy** | Despliegue: publicar cambios |
| 7 | **preview** | Vista previa: revisar antes de publicar |
| 8 | **status** | Estado: diagnosticar sistema actual |
| 9 | **brainstorm** | Ideación: generar ideas y soluciones |
| 10 | **orchestrate** | Orquestación: coordinar múltiples agentes |
| 11 | **ui-ux-pro-max** | UI/UX avanzada: diseño profesional |

### 4.1. Ejemplo de Workflow

```markdown
# .agent/workflows/debug.md
## Debug Workflow

### Fase 1: Diagnóstico
1. Identificar síntoma (error, caída, lentitud)
2. Revisar logs relevantes
3. Confirmar hipótesis

### Fase 2: Aislamiento
1. Aislar componente problemático
2. Verificar dependencias
3. Probar en entorno aislado

### Fase 3: Corrección
1. Implementar fix
2. Verificar que no rompe otras funcionalidades
3. Documentar la solución

### Fase 4: Validación
1. Test de regresión
2. Monitoreo post-fix (15 min)
3. Reporte final
```

---

## 5. CÓMO SE USA EL ECOSISTEMA

### 5.1. Carga de Contexto Selectivo

El `selective_context.py` determina qué agentes y skills cargar según la petición del usuario:

```python
def build_selective_context(request_text: str) -> str:
    route = route_request(request_text)

    # Cargar agente principal
    agent = load_agent_file(route["agent"])

    # Cargar skills relevantes
    skills = [load_skill_file(s) for s in route["skills"]]

    # Cargar workflow si aplica
    workflow = load_workflow(route["workflow"])

    return combine(agent, skills, workflow)
```

### 5.2. Enrutamiento por Keywords

El `router/router.py` clasifica la petición y asigna el agente:

```python
AGENT_RULES = {
    "debugger": ["debug", "error", "broken", "crash", "logs"],
    "devops-engineer": ["deploy", "docker", "traefik", "infra"],
    "security-auditor": ["security", "vulnerability", "audit"],
    "backend-specialist": ["api", "backend", "endpoint", "database"],
    "project-planner": ["plan", "roadmap", "architecture", "strategy"],
    "orchestrator": ["orchestrate", "multi-agent", "workflow"],
}
```

---

## 6. CÓMO EXTENDER EL ECOSISTEMA

### 6.1. Añadir un Nuevo Agente

```bash
# Crear archivo de agente
touch /opt/ai-lab/.agent/agents/mi-nuevo-agente.md

# Añadir reglas de enrutamiento
# Editar /opt/ai-lab/runtime/router/router.py
# Añadir a AGENT_RULES
```

### 6.2. Añadir una Nueva Skill

```bash
# Crear directorio y archivo
mkdir -p /opt/ai-lab/.agent/skills/mi-skill
touch /opt/ai-lab/.agent/skills/mi-skill/SKILL.md
```

### 6.3. Añadir un Nuevo Workflow

```bash
# Crear archivo de workflow
touch /opt/ai-lab/.agent/workflows/mi-workflow.md
```
