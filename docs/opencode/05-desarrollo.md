# AI-LAB: GUÍA DE DESARROLLO Y EXTENSIÓN
## Cómo contribuir, añadir módulos y extender el sistema

---

## 1. ESTRUCTURA DEL REPOSITORIO

```
/opt/ai-lab/
├── runtime/                    # Código principal del runtime
│   ├── agent/                  # Enrutamiento de intenciones, contexto
│   ├── audit/                  # Sistema de auditoría
│   ├── distributed/            # Coordinación distribuida
│   ├── execution/              # Ejecución controlada
│   ├── llm/                    # Router API + invocación modelos
│   ├── memory/                 # Memoria semántica + episódica
│   ├── modes/                  # Modos operacionales
│   ├── nodes/                  # Registro y healthcheck de nodos
│   ├── planner/                # Planificador de tareas
│   ├── policies/               # Políticas de ejecución
│   ├── profiles/               # Perfiles de gobernanza
│   ├── prompt/                 # Constructor de prompts
│   ├── rag/                    # Pipeline RAG
│   ├── router/                 # Router de agentes
│   ├── search/                 # Búsqueda en Qdrant
│   ├── security/               # Guard de capacidades
│   ├── state/                  # Estado del sistema
│   ├── tools/                  # Herramientas shell seguras
│   └── workflows/              # Motor de workflows
├── .agent/                     # Ecosistema de agentes
│   ├── agents/                 # 21 prompts de agentes (.md)
│   ├── skills/                 # 39 skills (.md)
│   └── workflows/              # 12 workflows (.md)
├── stacks/                     # Docker compose stacks
├── config/                     # Configuración OpenCode
├── memory/                     # Archivos de memoria local
├── snapshots/                  # Snapshots del sistema
├── docs/                       # Documentación
│   └── opencode/               # Documentos generados aquí
├── data/                       # Datos persistentes Docker
├── scripts/                    # Scripts auxiliares
├── mcp/                        # MCP (Model Context Protocol)
└── README.md                   # Este archivo
```

---

## 2. CÓMO AÑADIR UN NUEVO MÓDULO

### 2.1. Crear la estructura básica

```python
# /opt/ai-lab/runtime/mimodulo/__init__.py
from runtime.mimodulo.core import mi_funcion

__all__ = ["mi_funcion"]
```

```python
# /opt/ai-lab/runtime/mimodulo/core.py
from runtime.memory.episodic_memory import write_episode
from runtime.audit.audit_logger import audit_event


def mi_funcion(parametro: str) -> dict:
    # Lógica aquí
    result = {"status": "ok", "param": parametro}

    # Registrar en memoria episódica
    write_episode(
        event_type="mimodulo_executed",
        summary=f"Ejecutado con parámetro: {parametro}",
        payload=result,
    )

    # Registrar en auditoría
    audit_event("mimodulo_action", {"param": parametro})

    return result
```

### 2.2. Registrar en el sistema

Para integrar el nuevo módulo con el runtime, añade la importación en los puntos apropiados según lo que haga el módulo.

---

## 3. CÓMO AÑADIR UN NUEVO NODO

### 3.1. Registrar en nodes.json

```json
// /opt/ai-lab/runtime/nodes/nodes.json
{
  "name": "nuevo-nodo",
  "host": "192.168.1.x",
  "port": 1234,
  "backend": "lmstudio",
  "gpu": "Nueva GPU",
  "vram_gb": XX,
  "priority": 5,
  "enabled": true,
  "capabilities": ["nueva-capacidad"],
  "models": ["modelo-ejemplo"]
}
```

### 3.2. Añadir ruta en el modelo de enrutamiento

En `runtime/llm/model_router.py`:

```python
DEFAULT_MODELS["nueva-capacidad"] = "modelo-ejemplo"
```

En `runtime/distributed/task_router.py`:

```python
TASK_CAPABILITY_MAP["nueva-tarea"] = ["nueva-capacidad"]
```

---

## 4. CÓMO AÑADIR UN NUEVO PERFIL

### 4.1. Crear archivo de perfil

```python
# /opt/ai-lab/runtime/profiles/nuevo_perfil.py
PROFILE = {
    "name": "nuevo_perfil",
    "description": "Descripción del nuevo perfil",
    "allow_shell": False,
    "allow_write": True,
    "allow_tools": False,
    "max_command_timeout": 60,
    "blocked_commands": ["rm", "shutdown", "reboot"],
    "audit_level": "strict",
}
```

### 4.2. Registrar en el cargador

En `runtime/profiles/loader.py`:

```python
VALID_PROFILES = {
    "sandbox",
    "pilot",
    "production",
    "nuevo_perfil",  # ← añadir aquí
}
```

---

## 5. CÓMO AÑADIR UN NUEVO MODO

### 5.1. Definir el modo

```python
# /opt/ai-lab/runtime/modes/nuevo_modo.py
MODE_NAME = "nuevo_modo"

ALLOWED_CAPABILITIES = {
    "read",
    "search",
    "rag",
    "analyze",
}

DESCRIPTION = "Descripción del nuevo modo."
```

### 5.2. Registrar en el registry

En `runtime/modes/registry.py`:

```python
MODES["nuevo_modo"] = {
    "name": "nuevo_modo",
    "description": "Descripción del nuevo modo.",
    "capabilities": ["read", "search", "rag", "analyze"],
}
```

---

## 6. CÓMO AÑADIR UN NUEVO AGENTE

Crear archivo en `/opt/ai-lab/.agent/agents/`:

```markdown
# /opt/ai-lab/.agent/agents/mi-agente.md
Eres un agente especializado en [propósito].

## Capacidades
- Capacidad 1
- Capacidad 2

## Contexto
[contexto relevante]

## Instrucciones
[instrucciones específicas]
```

### 6.1. Añadir reglas de enrutamiento

En `runtime/router/router.py`:

```python
AGENT_RULES["mi-agente"] = [
    "keyword1", "keyword2", "keyword3"
]
```

---

## 7. CÓMO AÑADIR UNA NUEVA SKILL

Crear archivo en `/opt/ai-lab/.agent/skills/`:

```markdown
# /opt/ai-lab/.agent/skills/mi-skill/SKILL.md
# Mi Skill

## Descripción
[descripción de la skill]

## Instrucciones
[instrucciones detalladas]

## Ejemplos
[ejemplos de uso]
```

---

## 8. CONVENCIONES DE CÓDIGO

### 8.1. Estilo

- Python 3.14+
- Type hints en todas las funciones
- Docstrings solo en funciones públicas
- Nombres de archivos en snake_case
- Clases en PascalCase
- Funciones en snake_case
- Constantes en UPPER_CASE

### 8.2. Estructura de un Módulo

```python
# 1. Imports de la stdlib
import json
import time
from pathlib import Path
from typing import Any

# 2. Imports de terceros
import requests

# 3. Imports del runtime
from runtime.memory.episodic_memory import write_episode
from runtime.audit.audit_logger import audit_event

# 4. Constantes
ARCHIVO_CONFIG = Path("/opt/ai-lab/runtime/state/config.json")

# 5. Funciones públicas
def funcion_principal(param: str) -> dict:
    ...

# 6. Funciones privadas
def _helper(param: str) -> str:
    ...

# 7. Entry point (si aplica)
if __name__ == "__main__":
    ...
```

### 8.3. Integración con Memoria y Auditoría

Todo módulo que ejecute acciones significativas debe:

1. **Registrar en auditoría**: `audit_event("event_type", {"key": "val"})`
2. **Registrar en memoria episódica**: `write_episode(event_type, summary, payload)`

---

## 9. GIT WORKFLOW

```bash
# Estado actual
git status

# Ver cambios sin commit
git diff

# Commits convencionales
git commit -m "Add: nueva funcionalidad"
git commit -m "Fix: corrección de error"
git commit -m "Update: mejora de módulo existente"
git commit -m "Docs: documentación de API"

# Ramas
git branch          # Ver ramas
git checkout -b feature/nueva-funcionalidad  # Crear rama

# Snapshot del estado actual
python3 /opt/ai-lab/runtime/state/system_state.py
```

---

## 10. TESTING

```bash
# Test de enrutamiento de intenciones
python3 /opt/ai-lab/runtime/agent/test_intent_router.py

# Test de gobernanza
python3 /opt/ai-lab/runtime/security/test_governance.py

# Validar sintaxis de todos los módulos
python3 -m py_compile /opt/ai-lab/runtime/agent/*.py
python3 -m py_compile /opt/ai-lab/runtime/audit/*.py
# ...etc para todos los módulos
```

---

## 11. PLANTILLA PARA NUEVO MÓDULO

```python
"""Módulo: [nombre]
Descripción: [descripción]
Dependencias: [módulos del runtime que importa]
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from runtime.memory.episodic_memory import write_episode
from runtime.audit.audit_logger import audit_event

# ── Constantes ──────────────────────────────────────────

ARCHIVO_ESTADO = Path("/opt/ai-lab/runtime/state/mi_modulo_state.json")

# ── Funciones Públicas ──────────────────────────────────

def mi_funcion(parametro: str) -> Dict[str, Any]:
    """Descripción de la función."""
    resultado = _logica_interna(parametro)

    write_episode(
        event_type="mi_modulo_executed",
        summary=f"Ejecutado con: {parametro}",
        payload=resultado,
    )

    audit_event("mi_modulo_action", {"param": parametro})

    return resultado

# ── Funciones Privadas ──────────────────────────────────

def _logica_interna(parametro: str) -> Dict[str, Any]:
    return {"status": "ok", "input": parametro}

# ── Entry Point ─────────────────────────────────────────

if __name__ == "__main__":
    resultado = mi_funcion("test")
    print(json.dumps(resultado, indent=2))
```
