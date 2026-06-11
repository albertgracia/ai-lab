# AI-LAB-OPENCODE-50-GITNEXUS-MCP-CONFIG-01

**Estado:** PASS
**Fecha:** 2026-06-11
**Modo:** configuracion local controlada
**Objetivo:** habilitar acceso GitNexus MCP en OpenCode local de `.50` sin tocar runtime AI-LAB.

## Resumen ejecutivo

Se ha configurado OpenCode local de `.50` para anadir un servidor MCP remoto `gitnexus` apuntando al endpoint LAN estable de GitNexus en `.30`.

Resultado:

- GitNexus health en `.30` verificado
- endpoint MCP de GitNexus verificado con cliente MCP real
- listado de tools MCP verificado
- consulta read-only simple al repo `ai-lab` verificada
- runtime AI-LAB no tocado
- Gateway/Router/Prometheus/Qdrant/Postgres no tocados
- backup local del config realizado
- rollback documentado

## 1. Inventario de referencia `.30`

### Fuente de verdad usada

No se accedio al fichero de config de OpenCode dentro de `.30`.

La referencia se construyo con evidencia verificable:

1. documentacion oficial en `docs/mcp/AI-LAB-MCP-CLIENT-CONFIG-DOCS-01.md`
2. runbooks GitNexus del repo
3. validacion HTTP/MCP directa contra `192.168.1.30`

### GitNexus observado en `.30`

- Health endpoint: `http://192.168.1.30:4747/api/health` -> `{"status":"ok"}`
- Hostname LAN estable: `gitnexus.ai-lab.local`
- Health por hostname: `http://gitnexus.ai-lab.local:4747/api/health` -> `{"status":"ok"}`
- MCP endpoint: `http://gitnexus.ai-lab.local:4747/api/mcp`
- Modo de conexion observado: **LAN directa por HTTP**, sin token observable en la validacion realizada

### Repo indexado observado en `.30`

- repo: `ai-lab`
- path: `/opt/ai-lab`
- indexedAt: `2026-06-10T08:26:04.864Z`
- stats: `files=802`, `nodes=16820`, `edges=24228`, `communities=271`, `processes=300`

## 2. Inventario `.50`

### Config OpenCode local encontrada

Rutas encontradas:

- `C:\Users\leobc\.config\opencode\opencode.json`
- `C:\Users\leobc\.config\opencode\opencode.jsonc`

Evidencia documental existente:

- `docs/mcp/AI-LAB-MCP-CLIENT-CONFIG-DOCS-01.md` indica que OpenCode puede leer ambos y recomienda `opencode.jsonc`

### Estado previo en `.50`

- ya existia `ailab-runtime-mcp`
- no existia entrada `gitnexus`
- habia header `Authorization` para `ailab-runtime-mcp`
- no se imprimio el secreto en esta fase

## 3. Diseño minimo aplicado

### Decision

Se anade solo una entrada MCP nueva en el config recomendado de `.50`:

```jsonc
"gitnexus": {
  "type": "remote",
  "url": "http://gitnexus.ai-lab.local:4747/api/mcp",
  "enabled": true,
  "timeout": 20000
}
```

### Motivos

1. `gitnexus.ai-lab.local` ya responde correctamente en LAN
2. evita fijar una IP si el hostname local ya existe
3. no requiere token observable en la validacion actual
4. mantiene el cambio local, pequeno y reversible

### Nombre de servidor MCP

- nombre configurado: `gitnexus`

Con este nombre, OpenCode deberia exponer tools prefijadas como:

- `gitnexus_list_repos`
- `gitnexus_query`
- `gitnexus_context`
- `gitnexus_impact`
- `gitnexus_detect_changes`

## 4. Cambios aplicados en `.50`

### Backup

Backup creado:

- `C:\Users\leobc\.config\opencode\opencode.jsonc.bak.pre-gitnexus-mcp-20260611-2115`

### Config modificada

Archivo modificado:

- `C:\Users\leobc\.config\opencode\opencode.jsonc`

### Procedimiento oficial actualizado

Archivo actualizado:

- `docs/mcp/AI-LAB-MCP-CLIENT-CONFIG-DOCS-01.md`

Se anadio una subseccion especifica para GitNexus MCP en OpenCode Desktop Windows `.50`.

## 5. Validacion

### 5.1 Sintaxis del config local

Validacion:

- `json.load(opencode.jsonc)` -> `ok`

### 5.2 Validacion MCP GitNexus con cliente real

Cliente usado:

- libreria Python local `mcp`
- transporte `streamable_http`

Resultado `initialize`:

- `serverInfo.name = gitnexus`
- `serverInfo.version = 1.6.5`
- `protocolVersion = 2025-11-25`

### 5.3 Tools MCP listadas

Tools verificadas por `list_tools()`:

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

### 5.4 Smoke read-only

1. `list_repos`:
   - repo `ai-lab` visible
   - stats del indice presentes

2. `query`:
   - consulta: `ai-lab`
   - resultado: PASS
   - devolvio procesos y simbolos del repo real

### 5.5 OpenCode Desktop local

Hechos verificables:

- OpenCode Desktop esta instalado en `.50`
- proceso observado: `C:\Users\leobc\AppData\Local\Programs\@opencode-aidesktop\OpenCode.exe`
- app entry observada: `ai.opencode.desktop`

Limite de esta fase:

- no se forzo cierre/reinicio de OpenCode Desktop para no interrumpir la sesion del usuario

Conclusion operativa:

- la configuracion quedo escrita correctamente
- el endpoint MCP remoto esta funcional y validado con cliente real
- para que la app cargue la nueva entrada `gitnexus`, el cliente OpenCode debe cerrarse y abrirse de nuevo

## 6. Runtime safety

Confirmado en esta fase:

- no se toco Gateway
- no se toco Router
- no se toco runtime AI-LAB
- no se reinicio ningun servicio AI-LAB
- no se toco Prometheus
- no se toco Qdrant/Postgres
- no se tocaron modelos ni LM Studio

## 7. Rollback

Si la nueva entrada MCP causara problemas en OpenCode Desktop `.50`:

1. cerrar OpenCode Desktop
2. restaurar backup:
   - copiar `opencode.jsonc.bak.pre-gitnexus-mcp-20260611-2115` sobre `opencode.jsonc`
3. abrir OpenCode de nuevo

Rollback logico equivalente:

- eliminar solo la clave `mcp.gitnexus` del `opencode.jsonc`

## 8. Criterio final

**PASS**

Justificacion:

1. `.50` ya tiene configuracion GitNexus MCP escrita localmente
2. el endpoint GitNexus MCP responde y completa `initialize`
3. `tools/list` PASS
4. `list_repos` PASS
5. `query` read-only PASS
6. `.30` no se ha modificado
7. runtime AI-LAB no se ha tocado
8. no se han expuesto secretos en la documentacion de la fase
