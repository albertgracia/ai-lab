# AI-LAB-MCP-CONTROL-PLANE-REPO-UNIFICATION-SPEC-01 ??? Auditor??a

**Resultado:** PASS
**HEAD base:** `be0c4f6c`
**HEAD final:** `<pendiente commit>`
**Rama:** `main`
**Fecha:** 2026-06-01

---

## 1. Resumen

Fase de especificaci??n para la unificaci??n del control plane MCP de AI-LAB. Se inspeccion?? el MCP real en `/mnt/mcp_server`, el contenido obsoleto del repo en `/opt/ai-lab/mcp`, y se dise??aron tres opciones de unificaci??n. No se modific?? ning??n archivo operativo.

---

## 2. Estado operativo inicial (verificado)

| Componente | Puerto | Estado |
|---|---|---|
| `ailab-mcp-semantic-gateway` | `127.0.0.1:8091` | ??? active/enabled |
| `ailab-mcp-lan-gateway` | `0.0.0.0:8092` | ??? active/disabled |
| UFW | ??? | ??? inactive |
| Token fingerprint | `ff4f2df5ea199879` | ??? no mostrado |

---

## 3. Git inicial

| M??trica | Valor |
|---|---|
| Rama | `main` |
| HEAD | `be0c4f6c` |
| Sync | ??? sincronizado con `origin/main` |
| Working tree | ??? limpio |

---

## 4. Inventario `/mnt/mcp_server` (resumen)

| Categor??a | Detalle |
|---|---|
| Archivos Python | 11 (server.py + lan_server.py + 9 tools) |
| Archivos config | 1 (ailab_semantic_gateway.mcp.json) |
| Tools registradas | 8 (v??a `tools/__init__.py` ??? `register_all()`) |
| L??neas server.py | 74 |
| L??neas lan_server.py | 117 |
| C??digo duplicado | Inicializaci??n FastMCP + tool registration (compartido) |

---

## 5. Inventario `/opt/ai-lab/mcp` (resumen)

| Aspecto | Detalle |
|---|---|
| Contenido | `ailab_semantic_gateway.py` obsoleto, docker-safe.sh, terminal-safe.sh |
| Tools | ??? No contiene tools del MCP real |
| Relevancia | ??? Ninguna ??? no coincide con `/mnt/mcp_server` |

---

## 6. Systemd pointers

Ambos servicios (`semantic-gateway` y `lan-gateway`) apuntan a:
```
ExecStart=... /mnt/mcp_server/server.py   # o lan_server.py
WorkingDirectory=/mnt/mcp_server
```

Ninguno apunta a `/opt/ai-lab/mcp/`.

---

## 7. Opciones analizadas

| Opci??n | Descripci??n | Riesgo | Recomendada |
|---|---|---|---|
| **A** | Copia versionada + sync controlado | Bajo | ??? S?? |
| B | Mover al repo + cambiar systemd | Alto | ??? No (futuro) |
| C | No versionar, solo documentar | Cero | ??? No (mala gobernanza) |

---

## 8. Opci??n recomendada

**Opci??n A** ??? Copiar `/mnt/mcp_server` a `/opt/ai-lab/mcp/runtime-mcp/`, mantener systemd apuntando a `/mnt`, sync controlado con rsync + backup.

---

## 9. Archivos creados

| Archivo | Acci??n |
|---|---|
| `docs/mcp/AI-LAB-MCP-CONTROL-PLANE-REPO-UNIFICATION-SPEC-01.md` | Creado |
| `docs/audits/AI-LAB-MCP-CONTROL-PLANE-REPO-UNIFICATION-SPEC-01.md` | Creado |

---

## 10. Confirmaciones

| Confirmaci??n | S??/No |
|---|---|
| Servicios MCP modificados | ??? No |
| `/mnt/mcp_server` modificado | ??? No |
| Systemd modificado | ??? No |
| Servicios reiniciados | ??? No |
| Token le??do/mostrado | ??? No |
| UFW modificado | ??? No |
| Runtime tocado | ??? No |
| OpenCode/LM Studio modificado | ??? No |
| Push realizado | ??? No |
| Tag creado | ??? No |
| Rebase/force push | ??? No |

---

## 11. Siguiente fase recomendada

`AI-LAB-MCP-CONTROL-PLANE-REPO-UNIFICATION-IMPLEMENTATION-01`

Copiar `/mnt/mcp_server` al repo como snapshot versionado, a??adir tests unitarios, establecer proceso de sync. Sin cambiar systemd.

