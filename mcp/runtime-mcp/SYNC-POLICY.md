# AI-LAB Runtime MCP Sync Policy

## Objetivo

Definir c?mo sincronizar de forma segura el MCP versionado en repo hacia `/mnt/mcp_server`.

## Regla principal

No sincronizar autom?ticamente.
No cambiar systemd en esta fase.
No reiniciar servicios sin fase expl?cita.

## Flujo futuro recomendado

1. Editar c?digo en `mcp/runtime-mcp/`.
2. Ejecutar tests est?ticos y de contrato.
3. Crear backup de `/mnt/mcp_server`.
4. Ejecutar sync controlado repo ? `/mnt/mcp_server`.
5. Reiniciar solo el servicio afectado si la fase lo autoriza.
6. Validar:
   - `127.0.0.1:8091`
   - `0.0.0.0:8092`
   - OpenCode local
   - LM Studio/OpenCode LAN
7. Rollback desde backup si falla.

## Exclusiones obligatorias

Nunca sincronizar ni versionar:

- tokens
- `.env`
- `/etc/ai-lab/mcp-lan.env`
- logs
- backups
- `__pycache__`
- `.pyc`
- bases de datos locales
- dumps
- archivos temporales

## Servicios

El cambio de systemd para apuntar al repo queda prohibido hasta una fase posterior espec?fica.
