# AI-LAB-OPENCODE-50-GITNEXUS-MCP-POST-RESTART-SMOKE-01

**Estado:** PASS
**Fecha:** 2026-06-11
**Modo:** validacion read-only post-reinicio
**Objetivo:** confirmar que OpenCode Desktop en `.50` cargo correctamente la configuracion MCP GitNexus tras reinicio.

## Resumen ejecutivo

La validacion post-reinicio es **PASS**.

Evidencia principal:

- OpenCode Desktop fue reiniciado en `.50`
- existe una conexion TCP establecida desde `OpenCode.exe` hacia `192.168.1.30:4747`
- el endpoint GitNexus MCP responde `initialize`
- `tools/list` PASS
- `list_repos` PASS
- `query("ai-lab")` PASS
- `health` GitNexus PASS
- no se toco runtime AI-LAB

## 1. Evidencia de reinicio y carga en `.50`

### Procesos OpenCode observados

Proceso relevante:

- `ProcessName`: `OpenCode`
- `PID`: `23728`
- `StartTime`: `2026-06-11 21:31:09`
- `Path`: `C:\Users\leobc\AppData\Local\Programs\@opencode-aidesktop\OpenCode.exe`

### Logs de arranque

Archivo:

- `C:\Users\leobc\AppData\Roaming\ai.opencode.desktop\logs\20260611T193109\main.log`

Hechos observados:

- `app starting { version: '1.16.2' }`
- `server ready { url: 'http://127.0.0.1:54519' }`

Interpretacion:

- la sesion actual de OpenCode Desktop se inicio despues del cambio de configuracion local

### Evidencia de reconocimiento de GitNexus

Conexion TCP establecida observada:

- `LocalAddress`: `192.168.1.50`
- `RemoteAddress`: `192.168.1.30`
- `RemotePort`: `4747`
- `OwningProcess`: `23728`

Interpretacion:

- el proceso `OpenCode.exe` activo en `.50` mantiene conexion hacia GitNexus en `.30`
- esto constituye evidencia fuerte de que el servidor MCP `gitnexus` fue reconocido y cargado por OpenCode Desktop tras el reinicio

## 2. Validacion MCP GitNexus

Endpoint validado:

- `http://gitnexus.ai-lab.local:4747/api/mcp`

Cliente usado para smoke read-only:

- libreria Python local `mcp`
- transporte `streamable_http`

### 2.1 initialize

Resultado:

- `serverInfo.name = gitnexus`
- `serverInfo.version = 1.6.5`
- `session_id` emitido correctamente

## 3. tools/list

Resultado: **PASS**

Tools observadas:

- `list_repos`
- `query`
- `cypher`
- `context`
- `detect_changes`
- `rename`
- `impact`
- `route_map`
- `tool_map`
- `shape_check`
- `api_impact`
- `group_list`
- `group_sync`

Interpretacion en OpenCode:

- con el nombre de servidor configurado `gitnexus`, OpenCode debe exponer estas tools como `gitnexus_*`

## 4. list_repos

Resultado: **PASS**

Repo observado:

- `name = ai-lab`
- `path = /opt/ai-lab`
- `indexedAt = 2026-06-10T08:26:04.864Z`
- `files = 802`
- `nodes = 16820`
- `edges = 24228`
- `communities = 271`
- `processes = 300`

Nota:

- el payload reporta `commitsBehind = 44`; esto indica indice estructural stale, no fallo MCP

## 5. query("ai-lab")

Resultado: **PASS**

Consulta ejecutada:

- `query = "ai-lab"`
- `limit = 3`

Resultado observado:

- devolvio procesos reales del repo
- devolvio simbolos reales, por ejemplo:
  - `getRuntimeHistory`
  - `_prometheus_base_url`

Interpretacion:

- GitNexus responde correctamente en modo read-only sobre el repo `ai-lab`

## 6. Health GitNexus

Endpoint:

- `http://gitnexus.ai-lab.local:4747/api/health`

Resultado:

- `{"status":"ok"}`

## 7. Runtime safety

Confirmado en esta fase:

- no se modifico configuracion
- no se toco runtime
- no se reinicio ningun servicio AI-LAB
- no se toco Gateway
- no se toco Router
- no se toco Prometheus
- no se toco Qdrant/Postgres
- no se tocaron modelos ni LM Studio

## 8. Criterio final

**PASS**

Justificacion:

1. `gitnexus` queda efectivamente visible/cargado en OpenCode `.50` con evidencia de conexion TCP del proceso `OpenCode.exe` al `:4747` remoto
2. `tools/list` PASS
3. `list_repos` PASS
4. `query("ai-lab")` PASS
5. `health` GitNexus PASS
6. sin cambios runtime
