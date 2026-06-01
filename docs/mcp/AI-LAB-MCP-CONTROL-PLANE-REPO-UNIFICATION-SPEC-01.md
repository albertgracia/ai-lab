# AI-LAB MCP Control Plane ??? Repo Unification Spec

**Fase:** `AI-LAB-MCP-CONTROL-PLANE-REPO-UNIFICATION-SPEC-01`
**Estado:** SPEC (solo documentaci??n)
**HEAD base:** `be0c4f6c`
**Rama:** `main`

---

## 1. Objetivo

Dise??ar un plan seguro para versionar y gobernar el MCP real de AI-LAB dentro del repositorio `/opt/ai-lab`, sin romper el servidor MCP actualmente operativo en `/mnt/mcp_server`. Esta fase es ??nicamente de especificaci??n: no mueve archivos, no modifica systemd, no reinicia servicios.

---

## 2. Estado actual

### Servicios MCP

| Componente | Puerto | Endpoint | Estado | Systemd |
|---|---|---|---|---|
| Semantic Gateway | `127.0.0.1:8091` | `/mcp` | active/enabled | `ailab-mcp-semantic-gateway.service` |
| LAN Gateway | `0.0.0.0:8092` | `/mcp` | active/disabled | `ailab-mcp-lan-gateway.service` |

### Dependencias

- Ambos servicios ejecutan desde `/opt/ai-lab/.venv/bin/python`
- Ambos usan `WorkingDirectory=/mnt/mcp_server`
- Token LAN: `AILAB_MCP_TOKEN` en `/etc/ai-lab/mcp-lan.env`
- UFW: `inactive` (no modificado)
- Runtime Gateway: `127.0.0.1:8008`
- Runtime Router: `127.0.0.1:8083`

### Clientes validados

| Cliente | IP | LM Studio | OpenCode Desktop |
|---|---|---|---|
| X870EAORUSPRO | `192.168.1.50` | ??? | ??? |
| NAS-N5 | `192.168.1.250` | ??? | ??? |

---

## 3. Inventario `/mnt/mcp_server` (MCP real activo)

```
/mnt/mcp_server/
????????? config/
???   ????????? ailab_semantic_gateway.mcp.json
????????? logs/
???   ????????? .gitkeep
????????? tools/
???   ????????? __init__.py          # register_all() ??? 8 tools
???   ????????? client.py            # HTTP client compartido
???   ????????? incidents.py
???   ????????? latency.py
???   ????????? memory.py
???   ????????? operator.py
???   ????????? route_preview.py
???   ????????? runtime_health.py
???   ????????? slo.py
???   ????????? status.py
????????? server.py                # 74 l??neas ??? semantic gateway 8091
????????? lan_server.py            # 117 l??neas ??? LAN gateway 8092 + token auth
```

**Archivos:** 11 archivos Python + 1 JSON + 1 .gitkeep = 13 archivos funcionales.

### Herramientas registradas (8)

V??a `tools/__init__.py` ??? `register_all(mcp)`:

| Tool | M??dulo | Riesgo |
|---|---|---|
| `ailab_status` | `tools/status.py` | Bajo |
| `ailab_runtime_health` | `tools/runtime_health.py` | Bajo |
| `ailab_route_preview` | `tools/route_preview.py` | Bajo |
| `ailab_operator_summary` | `tools/operator.py` | Cautela |
| `ailab_incidents_active` | `tools/incidents.py` | Cautela |
| `ailab_slo_status` | `tools/slo.py` | Bajo |
| `ailab_health_latency` | `tools/latency.py` | Bajo |
| `ailab_memory_search` | `tools/memory.py` | Cautela |

### An??lisis de duplicaci??n

`server.py` y `lan_server.py` comparten:
- Misma estructura FastMCP
- Mismo `register_all()` desde `tools/`
- Misma dependencia de `tools/client.py`
- Misma l??gica de logging

Diferencias:
- `server.py`: solo 74 l??neas, bind en `127.0.0.1:8091`, sin token
- `lan_server.py`: 117 l??neas, bind en `0.0.0.0:8092`, token auth v??a middleware Starlette, `TransportSecuritySettings`

El c??digo duplicado es la inicializaci??n FastMCP + tool registration. Podr??a unificarse con un factory pattern.

---

## 4. Inventario `/opt/ai-lab/mcp` (repo, obsoleto)

```
/opt/ai-lab/mcp/
????????? config/
???   ????????? ailab_semantic_gateway.mcp.json
???   ????????? filesystem.mcp.json
???   ????????? git.mcp.json
????????? logs/
???   ????????? semantic_gateway.log
????????? servers/
    ????????? ailab_semantic_gateway.py   # Obsoleto, no coincide con /mnt/mcp_server/server.py
    ????????? docker-safe/
    ???   ????????? docker-safe.sh
    ????????? terminal-safe/
        ????????? terminal-safe.sh
```

**Conclusi??n:** El contenido de `/opt/ai-lab/mcp/` es irrelevante para el MCP real. `ailab_semantic_gateway.py` es una versi??n antigua. No hay tools, no hay `lan_server.py`, no hay nada del runtime actual.

---

## 5. Systemd unit pointers

### Semantic Gateway
```
ExecStart=/opt/ai-lab/.venv/bin/python /mnt/mcp_server/server.py
WorkingDirectory=/mnt/mcp_server
User=albert
```

### LAN Gateway
```
ExecStart=/opt/ai-lab/.venv/bin/python /mnt/mcp_server/lan_server.py
WorkingDirectory=/mnt/mcp_server
EnvironmentFile=/etc/ai-lab/mcp-lan.env
User=albert
```

Ambos apuntan a `/mnt/mcp_server/`. Ninguno apunta a `/opt/ai-lab/mcp/`.

---

## 6. Opciones de unificaci??n

### Opci??n A (RECOMENDADA) ??? Copia versionada + sync controlado

**Descripci??n:** Copiar `/mnt/mcp_server` dentro del repo como `/opt/ai-lab/mcp/runtime-mcp/`, mantener el despliegue real en `/mnt/mcp_server`, y establecer un proceso de sync repo ??? `/mnt`.

| Aspecto | Detalle |
|---|---|
| Riesgo | Bajo ??? no cambia systemd, no toca servicios |
| Source of truth | Dual temporal: repo para versionado, `/mnt` para ejecuci??n |
| Proceso | `rsync` controlado con backup previo |
| Systemd | No se modifica |
| Rollback | Backup en `/mnt/mcp_server.bak.$(date +%s)` |

**Ventajas:**
- Reproducible: un clon del repo tiene el MCP real
- Bajo riesgo inicial: servicios siguen funcionando desde `/mnt`
- Permite a??adir tests antes de migrar systemd

**Riesgos:**
- Doble ubicaci??n temporal ??? hay que evitar drift entre repo y `/mnt`
- Requiere disciplina: editar en repo, sync a `/mnt`
- Si alguien edita en `/mnt` directamente, el repo queda desactualizado

### Opci??n B ??? Mover runtime al repo + cambiar systemd

**Descripci??n:** Mover el c??digo a `/opt/ai-lab/mcp/runtime-mcp/`, cambiar systemd para ejecutar desde ah??, eliminar `/mnt` como source of truth.

| Aspecto | Detalle |
|---|---|
| Riesgo | Alto ??? puede romper servicios |
| Source of truth | ??nica: el repo |
| Proceso | Requiere parada de servicios, cambio de units, reinicio |
| Rollback | Revertir units y restaurar `/mnt` |

**Ventajas:**
- Source of truth ??nica
- Elimina confusi??n `/mnt` vs `/opt`

**Riesgos:**
- Si algo falla, los clientes LAN/LM Studio/OpenCode pierden conectividad
- No recomendado como primera implementaci??n

### Opci??n C ??? No versionar, solo documentar

**Descripci??n:** Mantener `/mnt/mcp_server` como source of truth y no versionar el c??digo real.

| Aspecto | Detalle |
|---|---|
| Riesgo | Cero operacional |
| Source of truth | Solo `/mnt` |
| Reproducibilidad | ??? No |

**Ventajas:**
- Riesgo operacional cero

**Riesgos:**
- Un clon del repo no contiene el MCP real
- Mala gobernanza
- Si `/mnt` se pierde, no hay copia versionada

---

## 7. Recomendaci??n

**Opci??n A** como fase de implementaci??n inicial: `AI-LAB-MCP-CONTROL-PLANE-REPO-UNIFICATION-IMPLEMENTATION-01`.

No cambiar systemd a??n. No cambiar servicios a??n. A??adir tests y documentaci??n antes de cualquier migraci??n de systemd.

---

## 8. Layout del repo propuesto

```
/opt/ai-lab/mcp/runtime-mcp/
????????? server.py                # Copia de /mnt/mcp_server/server.py
????????? lan_server.py            # Copia de /mnt/mcp_server/lan_server.py
????????? tools/
???   ????????? __init__.py
???   ????????? client.py
???   ????????? incidents.py
???   ????????? latency.py
???   ????????? memory.py
???   ????????? operator.py
???   ????????? route_preview.py
???   ????????? runtime_health.py
???   ????????? slo.py
???   ????????? status.py
????????? config/
???   ????????? ailab_semantic_gateway.mcp.json
????????? logs/
???   ????????? .gitkeep
????????? tests/
???   ????????? test_import.py
???   ????????? test_tools.py
???   ????????? test_auth.py
????????? docs/
???   ????????? ARCHITECTURE.md
????????? README.md
????????? requirements.txt
```

**Fase incremental:**
1. Primero: copiar snapshot versionado (Implementation-01)
2. Despu??s: refactor modular en fase separada

---

## 9. Pol??tica de despliegue futura

```
1. Editar c??digo en repo (/opt/ai-lab/mcp/runtime-mcp/).
2. Ejecutar tests en repo.
3. Hacer backup de /mnt/mcp_server:
   cp -a /mnt/mcp_server /mnt/mcp_server.bak.$(date +%s)
4. Sincronizar repo ??? /mnt/mcp_server:
   rsync -av --delete /opt/ai-lab/mcp/runtime-mcp/ /mnt/mcp_server/
5. Reiniciar solo servicio afectado SI la fase lo autoriza.
6. Validar 8091:
   curl -s http://127.0.0.1:8091/health (esperar 405/404 OK)
7. Validar 8092 LAN:
   curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8092/health
8. Rollback desde backup si falla:
   rm -rf /mnt/mcp_server && cp -a /mnt/mcp_server.bak.<ts> /mnt/mcp_server
```

> **Nota:** Esta fase NO implementa nada del flujo anterior. Es solo dise??o.

---

## 10. Tests m??nimos futuros

| Test | Descripci??n |
|---|---|
| `test_import.py` | Validar que `server.py` y `lan_server.py` importan sin error |
| `test_tools_registered.py` | Validar que las 8 tools est??n registradas en FastMCP |
| `test_no_shell.py` | Validar que no hay `subprocess`, `os.system`, `open(..., 'w')` |
| `test_auth_lan.py` | Validar que lan_server rechaza requests sin token |
| `test_health_endpoint.py` | Validar que `/health` responde 404 (comportamiento esperado) |
| `test_coexistence.py` | Validar que 8091 y 8092 pueden correr simult??neamente |

---

## 11. Gobernanza de tools

### Read-only ??? bajo riesgo
Aprobadas sin restricciones:
- `ailab_status`
- `ailab_runtime_health`
- `ailab_route_preview`
- `ailab_slo_status`
- `ailab_health_latency`

### Read-only ??? cautela
Requieren supervisi??n, no forzar en producci??n sin necesidad:
- `ailab_operator_summary`
- `ailab_incidents_active`
- `ailab_memory_search`

### Mutables
Prohibidas por ahora. Ninguna tool MCP actual modifica estado.

---

## 12. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigaci??n |
|---|---|---|---|
| Drift repo vs `/mnt` | Media | Medio | Sync disciplinado, CI check |
| Error en sync | Baja | Alto | Backup autom??tico pre-sync |
| Modificaci??n directa en `/mnt` | Media | Medio | Educar al equipo, audit trail |
| Rotura de tool | Baja | Alto | Tests antes de sync |
| Fuga de token | Baja | Cr??tico | No versionar `.env`, solo `.env.example` |

---

## 13. Rollback conceptual

Si la implementaci??n falla:
1. Verificar que existe backup en `/mnt/mcp_server.bak.<ts>`
2. Restaurar: `rm -rf /mnt/mcp_server && cp -a /mnt/mcp_server.bak.<ts> /mnt/mcp_server`
3. Reiniciar servicio afectado
4. Verificar 8091 y 8092

---

## 14. Siguientes fases

1. **`AI-LAB-MCP-CONTROL-PLANE-REPO-UNIFICATION-IMPLEMENTATION-01`** ??? Copiar `/mnt/mcp_server` al repo como snapshot versionado, a??adir tests, establecer proceso de sync
2. **`AI-LAB-MCP-CONTROL-PLANE-REPO-UNIFICATION-OPTIMIZATION-01`** ??? Refactor modular, factory pattern para server.py/lan_server.py
3. **`AI-LAB-MCP-CONTROL-PLANE-REPO-UNIFICATION-SYSTEMD-01`** ??? Migrar systemd al repo (solo si las fases previas son estables)

