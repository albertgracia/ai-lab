# AI-LAB Runtime MCP Snapshot

Este directorio contiene una copia versionada del servidor MCP real de AI-LAB.

## Estado

- Snapshot versionado del runtime activo ubicado en `/mnt/mcp_server`.
- No es todav?a el source of truth operativo.
- Los servicios systemd siguen apuntando a `/mnt/mcp_server`.
- No contiene tokens ni secretos.
- No contiene `/etc/ai-lab/mcp-lan.env`.

## Servicios actuales

- `ailab-mcp-semantic-gateway.service` usa el endpoint local `127.0.0.1:8091`.
- `ailab-mcp-lan-gateway.service` usa el endpoint LAN `0.0.0.0:8092`.
- El servicio LAN requiere `AILAB_MCP_TOKEN` desde `/etc/ai-lab/mcp-lan.env`.

## Herramientas MCP

Tools read-only validadas:

- `ailab_status`
- `ailab_runtime_health`
- `ailab_route_preview`
- `ailab_operator_summary`
- `ailab_incidents_active`
- `ailab_slo_status`
- `ailab_health_latency`
- `ailab_memory_search`

## Pol?tica

Este snapshot permite versionar, auditar y probar el MCP sin cambiar el runtime activo.
El despliegue repo ? `/mnt/mcp_server` debe hacerse solo mediante fase controlada.
