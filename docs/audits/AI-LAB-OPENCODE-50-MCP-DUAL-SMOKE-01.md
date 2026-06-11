# AI-LAB-OPENCODE-50-MCP-DUAL-SMOKE-01

**Estado:** PASS
**Fecha:** 2026-06-11
**Modo:** validacion read-only de MCPs en OpenCode `.50`
**Objetivo:** comprobar que los dos MCPs cargados en OpenCode Desktop `.50` responden correctamente y mantienen separacion de roles.

## MCP_SERVERS

### Discovery observado

Configuracion activa en `.50`:

- `ailab-runtime-mcp` -> `http://192.168.1.30:8092/mcp`
- `gitnexus` -> `http://gitnexus.ai-lab.local:4747/api/mcp`

Evidencia de carga en OpenCode Desktop:

- proceso `OpenCode.exe` observado tras reinicio
- conexion TCP establecida a `192.168.1.30:4747`
- conexion TCP establecida a `192.168.1.30:8092`

Conclusion:

- ambos MCPs aparecen efectivamente cargados y utilizados por OpenCode `.50`

## GITNEXUS_RESULT

### tools/list

Resultado: PASS

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

### list_repos

Resultado: PASS

Repo observado:

- `name = ai-lab`
- `path = /opt/ai-lab`
- `files = 802`
- `nodes = 16820`
- `edges = 24228`
- `communities = 271`
- `processes = 300`

### query("ai-lab")

Resultado: PASS

Salida observada:

- procesos reales del repo
- simbolos reales como `getRuntimeHistory` y `_prometheus_base_url`

### context read-only

Resultado: PASS

Consulta usada:

- `context(name="_compute_score", file_path="runtime/codebase/gitnexus_memory.py", kind="Function", repo="ai-lab")`

Salida observada:

- simbolo encontrado en `runtime/codebase/gitnexus_memory.py`
- callers detectados:
  - `load_codebase_memory`
  - `test_compute_score_returns_dict`
  - `test_compute_score_deterministic`

### Hallazgo GitNexus

- `commitsBehind = 44`

Clasificacion:

- indice stale
- no bloquea esta fase
- requiere fase separada de refresh/reindex

## RUNTIME_MCP_RESULT

### tools/list

Resultado: PASS

Tools observadas:

- `ailab_status`
- `ailab_runtime_health`
- `ailab_route_preview`
- `ailab_operator_summary`
- `ailab_incidents_active`
- `ailab_slo_status`
- `ailab_health_latency`
- `ailab_memory_search`

### status/health

Resultado: PASS

`ailab_status`:

- gateway -> `ok`, `200`
- router -> `ok`, `200`

`ailab_runtime_health`:

- `score = 79.6`
- `overall_health.status = warning`
- `nodes_online = 1`
- `routing_confidence = 0.64`
- `watchdog_state = enabled`

`ailab_slo_status`:

- `overall_status = healthy`
- `violations_total = 0`
- `degraded_total = 0`
- `safe_mode_total = 0`

## CROSS_CHECK

### Separacion de roles confirmada

**GitNexus**:

- responde sobre codebase, grafo y simbolos
- expone repo indexado, procesos, contexto estructural e impacto
- evidencia: `list_repos`, `query`, `context`

**ailab-runtime-mcp**:

- responde sobre runtime, gateway/router, health score y SLO
- no devuelve grafo de codigo ni contexto estructural
- evidencia: `ailab_status`, `ailab_runtime_health`, `ailab_slo_status`

### Lectura comparativa

- GitNexus dice **como esta construido** `ai-lab`
- ailab-runtime-mcp dice **como esta operando** el runtime AI-LAB

No hay mezcla de semanticas entre ambos MCPs.

## RISKS

1. GitNexus index stale: `commitsBehind=44`
2. El stale index puede degradar precision estructural en queries/context/impact
3. No hay evidencia de fallo MCP ni de fallo OpenCode por este motivo

## NEXT_PHASE

### Propuesta

`AI-LAB-GITNEXUS-INDEX-REFRESH-01`

Objetivo:

- refrescar/reindexar GitNexus
- reducir `commitsBehind`
- repetir smoke basico `list_repos` + `query` + `context`

## Criterio final

**PASS**

Justificacion:

1. ambos MCPs aparecen cargados en OpenCode `.50`
2. GitNexus responde `tools/list`, `list_repos`, `query` y `context`
3. `ailab-runtime-mcp` responde `tools/list` y tools de `status/health`
4. no se realizaron cambios
5. no se expusieron secretos
