# AI-LAB-MCP-CLIENT-CONFIG-DOCS-PUSH-01

## Resultado

PASS

## Objetivo

Publicar la guía de configuración de clientes MCP de AI-LAB.

## Estado publicado

Se publicó la documentación de clientes MCP para:

- OpenCode local Ubuntu AI-LAB usando `127.0.0.1:8091/mcp`.
- OpenCode Desktop Windows `.50` usando `192.168.1.30:8092/mcp`.
- OpenCode Desktop Windows `.250` usando `192.168.1.30:8092/mcp`.
- LM Studio `.50` usando `192.168.1.30:8092/mcp`.
- LM Studio `.250` usando `192.168.1.30:8092/mcp`.

## Puntos cubiertos

- Diferencia crítica entre `127.0.0.1` local y endpoint LAN.
- Uso obligatorio de `Authorization: Bearer <AILAB_MCP_TOKEN>` en clientes LAN.
- No usar fingerprint como token.
- No usar placeholders como token real.
- No usar WSL para configurar OpenCode Desktop Windows.
- Errores típicos: `401`, `404`, `406`.
- Checklist de validación.
- Seguridad y no exposición de token.

## Estado operativo preservado

- `/mnt/mcp_server` no se modificó.
- `/etc/ai-lab/mcp-lan.env` no se leyó ni modificó.
- No se tocó OpenCode.
- No se tocó LM Studio.
- No se reiniciaron servicios.
- No se tocó runtime.
- No se tocó UFW/firewall.
- No se tocó Astro.
- No se tocó Docker.
- No hubo reboot.

## Siguiente fase

`AI-LAB-MCP-TOOLS-CATALOG-FINAL-01`
