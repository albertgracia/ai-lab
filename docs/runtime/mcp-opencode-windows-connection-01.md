# MCP-OPENCODE-WINDOWS-CONNECTION-01 — Conexión segura de OpenCode Windows al MCP Gateway

## Objetivo

Conectar OpenCode en Windows al AI-LAB MCP Semantic Gateway mediante SSH tunnel,
sin exponer el servicio MCP a la LAN.

## Arquitectura elegida

```
OpenCode (Windows)
  → localhost:8091
  → SSH tunnel (-L 8091:127.0.0.1:8091)
  → Ubuntu AI-LAB (127.0.0.1:8091)
  → ailab-mcp-semantic-gateway (systemd)
    → ailab-gateway (:8008)
    → ailab-router (:8083)
```

### Por qué SSH tunnel y NO 0.0.0.0

- **Seguridad**: el MCP Gateway no tiene auth configurada aún (modo dev).
- **Aislamiento**: 8091 solo escucha en 127.0.0.1 en Ubuntu → solo accesible
  mediante túnel SSH.
- **Sin firewall**: no se abren puertos en la red local.
- **Futuro**: cuando se implemente `AILAB_MCP_TOKEN` se podrá bindear a 0.0.0.0
  de forma segura.

## Prerrequisitos

- OpenCode instalado en Windows
- SSH key-based auth configurada para `albert@192.168.1.30`
- Túnel SSH activo durante toda la sesión de OpenCode

## Comandos de túnel

### Desde PowerShell o Windows Terminal

```powershell
ssh -N -L 8091:127.0.0.1:8091 albert@192.168.1.30
```

Mantener la terminal abierta. No cerrar hasta terminar la sesión de OpenCode.

### Si el puerto 8091 local está ocupado (alternativa)

```powershell
ssh -N -L 18091:127.0.0.1:8091 albert@192.168.1.30
```

En ese caso usar `http://127.0.0.1:18091/mcp` como URL MCP.

### Verificar conectividad

```powershell
Test-NetConnection 127.0.0.1 -Port 8091
```

Resultado esperado: `TcpTestSucceeded: True`

## Configuración de OpenCode

### Ruta detectada

```
C:\Users\leobc\.config\opencode\opencode.jsonc
```

### Backup creado

```
opencode.jsonc.bak.20260528-014248
```

### Bloque MCP añadido

```jsonc
"mcp": {
    "ailab": {
        "type": "remote",
        "url": "http://127.0.0.1:8091/mcp",
        "enabled": true,
        "timeout": 15000
    }
}
```

**Nota**: esta configuración requiere reiniciar OpenCode para que cargue el MCP server.
OpenCode no hot-reloads MCP servers en sesión activa.

## Tools validadas (3)

| Tool | Descripción | Read-only |
|---|---|---|
| `ailab_status` | Estado gateway + router | ✅ |
| `ailab_runtime_health` | Salud runtime (nodos, scores, watchdog) | ✅ |
| `ailab_route_preview` | Clasificación heurística de ruta (sin LLM) | ✅ |

### Resultados de validación

| Tool | Resultado esperado | Resultado obtenido |
|---|---|---|
| `ailab_status` | gateway + router OK | ✅ PASS (ambos OK) |
| `ailab_runtime_health` | runtime health, nodos online | ✅ PASS (2 nodos online) |
| `ailab_route_preview` | `executed_model_call: false` | ✅ PASS |

## Estado de servicios (Ubuntu post-check)

| Servicio | Estado | Puerto | Bind |
|---|---|---|---|
| `ailab-mcp-semantic-gateway` | active (running), enabled | 8091 | 127.0.0.1 🔒 |
| `ailab-gateway` | active (running), enabled | 8008 | 0.0.0.0 |
| `ailab-router` | active (running), enabled | 8083 | 0.0.0.0 |

## Logs MCP

- Sin tracebacks
- Sin secretos
- Sin prompts completos
- Session manager crea transportes correctamente

## Limitaciones

1. **Requiere túnel SSH activo** — el túnel debe estar abierto antes de arrancar OpenCode.
2. **No hay hot-reload** — OpenCode necesita reiniciarse para detectar el MCP server.
3. **Sin auth** en el MCP server — solo accesible por túnel (127.0.0.1).
4. **Sin validación desde OpenCode aún** — la validación funcional (FASE 3)
   requiere que el usuario reinicie su sesión de OpenCode con el túnel activo.

## Rollback

### Windows

1. Cerrar terminal SSH del túnel (`Ctrl+C` o cerrar ventana).
2. Restaurar backup de configuración OpenCode:
   ```powershell
   Copy-Item "$env:USERPROFILE\.config\opencode\opencode.jsonc.bak.20260528-014248" "$env:USERPROFILE\.config\opencode\opencode.jsonc"
   ```
   O eliminar manualmente el bloque `mcp` del JSON.

### Ubuntu

No hay cambios en servicios. Si se requiere rollback de documentación:
```bash
rm -f /opt/ai-lab/docs/runtime/mcp-opencode-windows-connection-01.md
```

## Próximos pasos (fuera de esta fase)

1. El usuario debe **reiniciar OpenCode** con el túnel activo para validar tools.
2. Implementar `AILAB_MCP_TOKEN` para auth segura.
3. Evaluar bind a 0.0.0.0 con token para evitar túnel SSH.
4. Integración con herramientas semánticas: `sommelier`, `analyze_label`, `price_estimate`.
