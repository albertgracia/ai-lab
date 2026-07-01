# AI-LAB-MCP-SYSTEMD-PERSISTENCE-PUSH-01

## Resultado

PASS

## Objetivo

Publicar la auditoría de recuperación de persistencia systemd de los servicios MCP de AI-LAB.

## Estado publicado

- `ailab-mcp-semantic-gateway.service`: active/enabled en `127.0.0.1:8091`.
- `ailab-mcp-lan-gateway.service`: active/enabled en `0.0.0.0:8092`.
- MCP initialize con token en `8092`: OK.
- Sin token en `8092`: `401`, esperado.
- UFW: inactive/no modificado.
- Token: no mostrado, no modificado en la fase.
- Código MCP: no modificado.
- Rollback documentado en `/tmp/rollback-mcp-systemd-persistence.sh`.

## Nota de token

El fingerprint documentado durante la recuperación fue `01896ebfed567192`, diferente al histórico `ff4f2df5ea199879`.  
Se interpreta como rotación externa previa. No se modificó token durante la fase.

## Estado operativo preservado

- `/mnt/mcp_server` no se modificó.
- `/etc/ai-lab/mcp-lan.env` no se modificó.
- No se tocó runtime.
- No se tocó UFW/firewall.
- No se tocó OpenCode.
- No se tocó LM Studio.
- No se tocó Astro.
- No se tocó Docker.
- No hubo reboot.

## Siguiente fase

`AI-LAB-MCP-PERSISTENCE-REBOOT-SMOKE-01`, solo cuando el operador decida reiniciar la VM.
