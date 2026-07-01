# AI-LAB-MCP-TOOLS-RESOURCES-PROMPTS-SPEC-PUSH-01

## Resultado

PASS

## Objetivo

Publicar la especificación de resources y prompts MCP propuestos para AI-LAB.

## Estado publicado

Se publicó la especificación de diseño para:

### Resources MCP propuestos

Bajo riesgo:

- `ai-lab://status/current`
- `ai-lab://runtime/health`
- `ai-lab://runtime/latency`
- `ai-lab://slo/current`
- `ai-lab://tools/catalog`
- `ai-lab://clients/config-guide`
- `ai-lab://mcp/security-policy`

Medio / con cautela:

- `ai-lab://incidents/active`
- `ai-lab://operator/summary`
- `ai-lab://memory/search-policy`

Alto / prohibidos:

- 0 resources.

### Prompts MCP propuestos

- `ai-lab-diagnostico-rapido`
- `ai-lab-resumen-noc`
- `ai-lab-revisar-incidentes`
- `ai-lab-validar-routing`
- `ai-lab-health-latency-review`
- `ai-lab-mcp-client-troubleshooting`
- `ai-lab-no-placeholder-report`

## Reglas publicadas

- No inventar valores.
- No usar placeholders como `[Valor]`.
- No aceptar `TASK_COMPLETED` sin contenido como evidencia.
- Si una tool no devuelve un campo, responder `no disponible`.
- Citar qué tool/resource produjo cada bloque del informe.
- No delegar a agente secundario si se pide evidencia operativa.
- No mezclar histórico con estado actual sin marcarlo.
- No sugerir restart/deploy/sync salvo fase explícita.

## Estado operativo preservado

- `/mnt/mcp_server` no se modificó.
- `mcp/runtime-mcp` no se modificó.
- `/etc/ai-lab/mcp-lan.env` no se leyó ni modificó.
- No se implementaron resources/prompts.
- No se tocó OpenCode.
- No se tocó LM Studio.
- No se reiniciaron servicios.
- No se tocó runtime.
- No se tocó UFW/firewall.
- No se tocó Astro.
- No se tocó Docker.
- No hubo reboot.

## Siguiente fase

`AI-LAB-MCP-OBSERVABILITY-METRICS-SPEC-01`
