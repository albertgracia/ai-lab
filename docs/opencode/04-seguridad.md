# AI-LAB: GUÍA DE SEGURIDAD Y GOBERNANZA
## Perfiles, políticas, capabilities y auditoría

---

## 1. MODELO DE SEGURIDAD EN 3 CAPAS

```
┌──────────────────────────────────────────────────────┐
│  CAPA 1: MODOS OPERACIONALES                          │
│  (readonly / plan / build / execute)                  │
│  Define qué capabilities tiene cada modo              │
├──────────────────────────────────────────────────────┤
│  CAPA 2: PERFILES DE GOBERNANZA                       │
│  (sandbox / pilot / production)                       │
│  Define restricciones de shell, escritura, timeout    │
├──────────────────────────────────────────────────────┤
│  CAPA 3: POLÍTICAS DE EJECUCIÓN                       │
│  (execution_policy.py)                                │
│  Clasifica riesgo de comandos (low/medium/high)       │
└──────────────────────────────────────────────────────┘
```

---

## 2. MODOS OPERACIONALES

| Modo | Capabilities | ¿Permite shell? | Caso de uso |
|------|-------------|-----------------|-------------|
| **readonly** | read, search, rag, analyze, logs, docker_ps, status | ❌ | Inspección, debugging |
| **plan** | read, search, rag, analyze, plan | ❌ | Análisis y planificación |
| **build** | read, search, rag, analyze, plan, write, generate, test, lint | ❌ | Desarrollo sin ejecución |
| **execute** | read, search, rag, analyze, plan, write, generate, test, lint, shell, docker, systemctl, deploy | ✅ | Operaciones privilegiadas |

### 2.1. Transiciones de Modo

```
readonly ──→ plan ──→ build ──→ execute
   ↑         ↑         ↑          ↑
   |         |         |          |
 solo      análisis  escritura  ejecución
 lectura            controlada  total
```

La transición requiere decisión explícita del operador (no automática).

### 2.2. Código: Definición de Modos

Ubicación: `runtime/modes/registry.py`

```python
MODES = {
    "plan": {
        "name": "plan",
        "description": "Modo planificación: solo análisis, lectura, RAG y plan.",
        "capabilities": ["analyze", "plan", "rag", "read", "search"],
    },
    "build": {
        "name": "build",
        "description": "Modo construcción: escritura controlada sin shell.",
        "capabilities": ["analyze", "plan", "rag", "read", "search", "write"],
    },
    "execute": {
        "name": "execute",
        "description": "Modo ejecución: shell y tools bajo governance y perfiles.",
        "capabilities": ["analyze", "plan", "rag", "read", "search", "write", "shell", "tools"],
    },
}
```

---

## 3. PERFILES DE GOBERNANZA

### 3.1. Comparativa

| Propiedad | Sandbox | Pilot | Production |
|-----------|---------|-------|------------|
| **allow_shell** | ✅ Sí | ✅ Sí | ❌ No |
| **allow_write** | ✅ Sí | ✅ Sí | ❌ No |
| **allow_tools** | ✅ Sí | ✅ Sí | ❌ No |
| **max_timeout** | 300s | 120s | 30s |
| **Comandos bloqueados** | rm -rf / | rm -rf, shutdown, reboot, docker compose down | rm, shutdown, reboot, systemctl restart, mkfs |
| **Audit level** | full | strict | paranoid |
| **Uso** | Experimental | Controlado | Producción |

### 3.2. Código de Perfiles

**sandbox.py:**
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

**pilot.py:**
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

**production.py:**
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

### 3.3. Cargador de Perfiles

Ubicación: `runtime/profiles/loader.py`

```python
def load_profile(name: str = "pilot") -> dict:
    module = import_module(f"runtime.profiles.{name}")
    return module.PROFILE
```

---

## 4. POLÍTICAS DE EJECUCIÓN

### 4.1. Clasificación de Riesgo

| Riesgo | Ejemplos | Modo Requerido |
|--------|----------|----------------|
| **low** | ls, cat, grep, df -h, free -h, docker ps, git status | readonly |
| **medium** | docker compose, systemctl, service, ufw | build |
| **high** | rm -rf, mkfs, shutdown, reboot, dd if=, docker system prune | execute |

### 4.2. Código de Clasificación

Ubicación: `runtime/policies/execution_policy.py`

```python
DANGEROUS_PATTERNS = [
    "rm -rf", "mkfs", "dd if=", "shutdown", "reboot", "poweroff",
    "docker compose down", "docker rm", "docker volume rm",
    "docker system prune", "systemctl restart", "systemctl stop",
]

REQUIRES_EXECUTE_MODE = [
    "docker ", "docker-compose ", "systemctl ", "service ",
    "ufw ", "iptables ", "nft ", "mount ", "umount ",
]
```

---

## 5. CAPABILITY GUARD

### 5.1. Validación en 3 Pasos

1. **Verificar modo** → `can_execute_shell(mode)`
2. **Verificar perfil** → `validate_profile_command(profile, command)`
3. **Ejecutar** → `run_safe_command(mode, command, profile_name)`

### 5.2. Código de Validación

Ubicación: `runtime/security/capability_guard.py`

```python
DANGEROUS_COMMANDS = [
    "rm -rf", "mkfs", "shutdown", "reboot", "poweroff",
    "sudo", "chmod 777", "dd if=", ":(){:|:&};:",
]

def can_execute_shell(mode: str) -> bool:
    cfg = get_mode(mode)
    return "shell" in cfg["capabilities"]

def validate_shell_command(mode: str, command: str):
    if not can_execute_shell(mode):
        raise PermissionError(f"Mode '{mode}' does not allow shell execution")
    lower = command.lower()
    for banned in DANGEROUS_COMMANDS:
        if banned in lower:
            raise PermissionError(f"Dangerous command blocked: {banned}")
    return True
```

---

## 6. AUDITORÍA

### 6.1. Audit Trail

| Archivo | Formato | Propósito |
|---------|---------|-----------|
| `runtime/state/governance_audit.jsonl` | JSONL | Eventos de gobernanza |
| `runtime/state/episodic_memory.jsonl` | JSONL | Memoria operacional |

### 6.2. Formato de Evento

```json
{
  "timestamp": 1747123456,
  "event_type": "execution_blocked",
  "payload": {
    "mode": "build",
    "profile": "pilot",
    "command": "rm -rf /tmp",
    "reason": "Blocked command in profile 'pilot': rm -rf"
  }
}
```

### 6.3. Tipos de Eventos

| event_type | Cuándo ocurre |
|------------|---------------|
| `orchestration_plan_created` | Se crea un plan de orquestación |
| `governance_test` | Test de gobernanza ejecutado |
| `sandbox_execution_blocked` | Comando bloqueado por perfil |
| `sandbox_execution_completed` | Comando ejecutado con éxito |

---

## 7. MATRIZ COMPLETA DE ACCESO

| Acción | readonly | plan | build | execute | Sandbox | Pilot | Production |
|--------|----------|------|-------|---------|---------|-------|------------|
| Leer archivos | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Buscar en Qdrant | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Analizar código | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Planificar | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Escribir archivos | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Generar código | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Ejecutar tests | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Shell (comandos) | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| Docker (gestión) | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| systemctl | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| shutdown/reboot | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |

---

## 8. SANDBOX RUNNER (EJECUCIÓN CONTROLADA)

Ubicación: `runtime/execution/sandbox_runner.py`

### 8.1. Flujo de Ejecución

```
run_safe_command(mode, command, profile)
    │
    ├─→ validate_shell_command(mode, command)     ← Capa 1: Modo
    │     └─→ can_execute_shell(mode)
    │
    ├─→ load_profile(profile_name)                ← Capa 2: Perfil
    │     └─→ validate_profile_command(profile, command)
    │
    ├─→ audit_event("execution_attempt", ...)
    │
    ├─→ subprocess.run(command, timeout=profile.timeout)
    │
    └─→ write_episode("execution_completed", ...)
```

---

## 9. BUENAS PRÁCTICAS

1. **Usar sandbox** para experimentación y desarrollo
2. **Usar pilot** para operaciones controladas con supervisión
3. **Usar production** solo cuando no se requieran cambios
4. **Revisar audit trail** periódicamente:
   ```bash
   cat runtime/state/governance_audit.jsonl | python3 -m json.tool
   ```
5. **Transicionar de modo** explícitamente (nunca automático)
6. **No ejecutar** comandos de alto riesgo en modo build
7. **Verificar capacidades** antes de ejecutar tareas nuevas
