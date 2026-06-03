# AI-LAB MCP — Configuración de Clientes

**Fase:** `AI-LAB-MCP-CLIENT-CONFIG-DOCS-01`
**Estado operativo de referencia:** Persistencia systemd validada tras reboot (HEAD `3a7b7b0c`)

---

## 1. Resumen de endpoints

| Endpoint | Ámbito | Acceso |
|---|---|---|
| `http://127.0.0.1:8091/mcp` | Solo dentro de Ubuntu AI-LAB (`192.168.1.30`) | Sin token (localhost) |
| `http://192.168.1.30:8092/mcp` | Clientes LAN (`.50`, `.250`) | `Authorization: Bearer <TOKEN>` |

## 2. Regla crítica: `127.0.0.1` ≠ AI-LAB desde Windows

`127.0.0.1` desde un equipo **Windows** apunta al propio Windows, **no a la VM AI-LAB**.

- Windows `.50` → `127.0.0.1` = X870EAORUSPRO (localhost de `.50`)
- Windows `.250` → `127.0.0.1` = NAS-N5 (localhost de `.250`)
- Ubuntu AI-LAB → `127.0.0.1` = `192.168.1.30` (localhost del servidor)

**Por tanto:** los clientes Windows `.50` y `.250` deben usar **siempre** `http://192.168.1.30:8092/mcp`.

## 3. OpenCode local en Ubuntu AI-LAB

Configuración en `/opt/ai-lab` (o `~/.config/opencode/opencode.jsonc` dentro del servidor):

```json
{
  "mcp": {
    "ailab": {
      "type": "remote",
      "url": "http://127.0.0.1:8091/mcp",
      "enabled": true,
      "timeout": 15000
    }
  }
}
```

- **Autenticación:** no requiere token (bound a `127.0.0.1`)
- **Timeout recomendado:** 15000 ms (15 segundos)

## 4. OpenCode Desktop Windows `.50`

**Ruta del archivo de configuración:**

```
C:\Users\leobc\.config\opencode\opencode.jsonc
```

> También puede existir `C:\Users\leobc\.config\opencode\opencode.json`. OpenCode lee ambos, pero la extensión recomendada es `.jsonc`.

**Configuración (sin token real — reemplazar `<AILAB_MCP_TOKEN>`):**

```jsonc
{
  "mcp": {
    "ailab-runtime-mcp": {
      "type": "remote",
      "url": "http://192.168.1.30:8092/mcp",
      "enabled": true,
      "headers": {
        "Authorization": "Bearer <AILAB_MCP_TOKEN>"
      },
      "timeout": 15000
    }
  }
}
```

**Notas importantes:**

| Aspecto | Detalle |
|---|---|
| Archivo | Usar `opencode.jsonc` (no `opencode.json`) |
| `Authorization` | Debe incluir `Bearer ` (con espacio) seguido del token real |
| `<AILAB_MCP_TOKEN>` | Reemplazar por el token real sin las `< >` |
| Fingerprint | `ff4f2df5ea199879` — **no** usar como token |
| Timeout | 15000 ms recomendado (operaciones de runtime pueden tomar varios segundos) |
| Recarga | Si OpenCode no muestra las tools nuevas, cerrar completamente y volver a abrir |
| PowerShell | Usar PowerShell, **no** WSL, para editar archivos de Windows |

## 5. OpenCode Desktop Windows `.250`

Misma configuración que `.50`:

```jsonc
{
  "mcp": {
    "ailab-runtime-mcp": {
      "type": "remote",
      "url": "http://192.168.1.30:8092/mcp",
      "enabled": true,
      "headers": {
        "Authorization": "Bearer <AILAB_MCP_TOKEN>"
      },
      "timeout": 15000
    }
  }
}
```

Ruta del archivo en `.250`:

```
C:\Users\leobc\.config\opencode\opencode.jsonc
```

(Reemplazar `leobc` si el usuario del equipo `.250` es distinto.)

## 6. LM Studio `.50` y `.250`

**Ruta del archivo de configuración:**

```
%USERPROFILE%\.lmstudio\mcp.json
```

Ejemplo completo:

```json
{
  "mcpServers": {
    "ailab-runtime-mcp": {
      "url": "http://192.168.1.30:8092/mcp",
      "headers": {
        "Authorization": "Bearer <AILAB_MCP_TOKEN>"
      }
    }
  }
}
```

**Requisitos en LM Studio:**

| Requisito | Detalle |
|---|---|
| Habilitar MCP | Settings → Tools → activar "Enable MCP Servers" |
| Usar `mcp.json` | Asegurar que LM Studio lee `mcp.json`, no otro archivo |
| Bearer token | El header `Authorization` debe incluir `Bearer ` (espacio incluido) |
| Token real | Reemplazar `<AILAB_MCP_TOKEN>` por el valor real, sin `< >` |
| Fingerprint | `ff4f2df5ea199879` sirve solo para verificar integridad — no es el token |

## 7. Validación rápida desde PowerShell (Windows `.50` / `.250`)

```powershell
# ESTABLECER TOKEN (solo en sesión actual, nunca guardarlo en script)
$env:AILAB_MCP_TOKEN = "PEGAR_TOKEN_REAL_AQUI"

# Probar endpoint LAN (debe dar 404/406 si auth es correcta)
Invoke-WebRequest -UseBasicParsing -TimeoutSec 8 `
  -Headers @{Authorization = "Bearer $env:AILAB_MCP_TOKEN"} `
  -Uri "http://192.168.1.30:8092/mcp"

# Limpiar variable de entorno (importante)
Remove-Item Env:\AILAB_MCP_TOKEN
```

**Interpretación de respuestas:**

| Código | Significado |
|---|---|
| `401 Unauthorized` | Token incorrecto, falta `Bearer ` o token no coincide. Revisar header. |
| `404 Not Found` o `406 Not Acceptable` | **Auth OK.** El servidor MCP responde pero PowerShell no habla MCP completo. Esto es esperado. |
| Timeout / Connection refused | Puerto no accesible. Verificar que el servicio LAN esté activo (`8092`). |
| Sin token | Debe dar `401 Unauthorized`. |

## 8. Validación funcional desde OpenCode

Una vez configurado, probar con estos prompts:

**Prompt 1 — Listar herramientas:**
```
Lista las herramientas MCP disponibles.
```

**Prompt 2 — Estado del gateway:**
```
Usa ailab-runtime-mcp_ailab_status y resume el resultado en español.
```

**Prompt 3 — Health check:**
```
Usa ailab-runtime-mcp_ailab_runtime_health y dime health score, nodes online y routing confidence.
```

**Prompt 4 — Incidencias activas:**
```
Usa ailab-runtime-mcp_ailab_incidents_active y traduce el resultado a español.
```

## 9. Validación funcional desde LM Studio

Prompt recomendado para pruebas:

```
No delegues esta tarea a un agente secundario.
Usa directamente ailab_status y ailab_runtime_health.
No uses placeholders.
No inventes valores.
Devuelve solo datos reales.
```

**Criterio de aceptación:** La respuesta debe contener datos reales (health score, nodos, estado de servicios). Si el modelo responde con `TASK_COMPLETED` sin datos, `[Valor]` o `[Placeholder]`, **no es evidencia válida**.

## 10. Errores típicos

| Error | Causa probable | Solución |
|---|---|---|
| `401 Unauthorized` | Falta `Bearer ` en el header | Asegurar formato exacto: `Bearer <token>` |
| `401 Unauthorized` | Token incorrecto | Copiar token real desde `/etc/ai-lab/mcp-lan.env` (solo en servidor) |
| `401 Unauthorized` | Se pegó el fingerprint como token | El fingerprint (`ff4f2df5ea199879`) **no** es el token |
| `401 Unauthorized` | Se dejó `<AILAB_MCP_TOKEN>` literal | Reemplazar por el valor real, sin `< >` |
| `404` / `406` | Auth correcta pero cliente HTTP simple no habla MCP | Es normal con curl/PowerShell básico. Solo OpenCode/LM Studio hablan MCP completo. |
| Timeout | Puerto 8092 no accesible desde el cliente | Verificar conectividad de red y que el servicio esté activo |
| No aparecen tools en OpenCode | OpenCode está leyendo otro archivo | Verificar `opencode.jsonc` (no `opencode.json`), reiniciar OpenCode Desktop |
| No aparecen tools en LM Studio | MCP no habilitado en Settings | Activar "Enable MCP Servers" en LM Studio Settings > Tools |
| `127.0.0.1:8092` no funciona desde Windows | Esperado — `127.0.0.1` es el propio Windows | Usar `192.168.1.30:8092` |
| WSL no funciona para configurar OpenCode | WSL tiene su propio filesystem | Usar PowerShell o el Explorador de archivos de Windows |

## 11. Seguridad

| Principio | Detalle |
|---|---|
| Token único | Cada cliente usa el mismo token del `EnvironmentFile` del servidor |
| No compartir | El token permite acceso **read-only** a herramientas de runtime |
| No subir a git | El token **nunca** debe aparecer en commits |
| Sin capturas | No adjuntar capturas de pantalla que muestren el token |
| Sin Cloudflare/NPM | El endpoint LAN no está expuesto a Internet |
| Sin Internet | Solo accesible desde la red interna (`192.168.1.0/24`) |
| UFW | `inactive` por decisión operativa; la seguridad del endpoint se basa en token |
| Tools read-only | Todas las herramientas MCP actuales son de solo lectura |
| Fingerprint público | `ff4f2df5ea199879` — sirve para verificar que el token no ha cambiado |

## 12. Checklist por cliente

| Cliente | Endpoint | Token | Estado |
|---|---|---|---|
| OpenCode Ubuntu AI-LAB | `127.0.0.1:8091/mcp` | No requiere | ✅ |
| OpenCode Desktop `.50` (X870EAORUSPRO) | `192.168.1.30:8092/mcp` | Requerido | ✅ |
| OpenCode Desktop `.250` (NAS-N5) | `192.168.1.30:8092/mcp` | Requerido | ✅ |
| LM Studio `.50` (X870EAORUSPRO) | `192.168.1.30:8092/mcp` | Requerido | ✅ |
| LM Studio `.250` (NAS-N5) | `192.168.1.30:8092/mcp` | Requerido | ✅ |

---

## Herramientas MCP disponibles (8)

| Tool | Descripción |
|---|---|
| `ailab_status` | Health del gateway + router |
| `ailab_runtime_health` | Resumen de salud del runtime (health score, nodos) |
| `ailab_route_preview` | Clasificación heurística de prompts (sin LLM) |
| `ailab_operator_summary` | Resumen operativo tipo NOC |
| `ailab_incidents_active` | Reporte de incidencias activas |
| `ailab_slo_status` | Estado de SLOs + violaciones históricas |
| `ailab_health_latency` | Estadísticas de latencia + health score |
| `ailab_memory_search` | Búsqueda semántica en colecciones Qdrant |
