# AI-LAB MCP LAN Controlled Mode Spec

## Resultado

SPEC / READ-ONLY

## Objetivo

Definir cómo exponer el servidor MCP actual de AI-LAB a clientes autorizados de la LAN sin comprometer seguridad ni gobernanza.

## Estado actual

- MCP activo: `/mnt/mcp_server/server.py`
- Servicio: `ailab-mcp-semantic-gateway.service`
- Bind actual: `127.0.0.1:8091`
- Transporte: Streamable HTTP
- Endpoint: `/mcp`
- Token actual: no
- Tools: 8 read-only
- Resources: no
- Prompts: no

## Principios de seguridad

1. LAN controlled mode no equivale a exposición abierta.
2. No exponer MCP a Internet.
3. No publicar MCP vía Cloudflare/NPM por ahora.
4. Token obligatorio antes de bind LAN.
5. Firewall allowlist obligatorio.
6. Solo tools read-only en la primera implementación.
7. Tools mutables/destructivas quedan en reserva.
8. Logging de llamadas MCP obligatorio.
9. Separar perfil OpenCode de perfil LM Studio.
10. Cualquier cambio de systemd/firewall requiere fase separada.

## Allowlist LAN

### Activas iniciales

| IP | Host | Uso |
|---|---|---|
| `192.168.1.50` | `X870EAORUSPRO` | Equipo Administrador |
| `192.168.1.60` | `X870AORUSELITE` | Equipo Albert |
| `192.168.1.250` | `NAS-N5` | LM Studio |

### Reserva / futuro

| IP | Host | Uso |
|---|---|---|
| `192.168.1.40` | `UBUNTU-OBSERVABILIDAD` | Futuro |
| `192.168.1.200` | `NAS-N5` | Futuro pendiente de confirmar rol |
| `192.168.1.100` | `WINDOWS2025SERV` | Futuro |
| `192.168.1.150` | `SERV2025-MARKET` | Futuro |

## Modo de exposición recomendado

### Fase 1 — Estado actual seguro

- Mantener `127.0.0.1:8091`
- Acceso por túnel SSH
- Sin exposición LAN directa

### Fase 2 — Token read-only

- Añadir `AILAB_MCP_TOKEN`
- Rechazar peticiones sin token
- Token nunca en repo
- Token vía environment/systemd drop-in

### Fase 3 — Bind LAN controlado

Opciones:
- bind a IP LAN específica del servidor AI-LAB
- o `0.0.0.0` solo si firewall está aplicado antes

### Fase 4 — Firewall allowlist

Permitir solo:
- `192.168.1.50`
- `192.168.1.60`
- `192.168.1.250`

Mantener en reserva:
- `192.168.1.40`
- `192.168.1.200`
- `192.168.1.100`
- `192.168.1.150`

### Fase 5 — LM Studio smoke

- Configurar LM Studio desde `192.168.1.250`
- Probar tools read-only
- Validar que no hay acceso desde IP no autorizada

## Tools permitidas para LAN inicial

Read-only:
- `ailab_status`
- `ailab_runtime_health`
- `ailab_route_preview`
- `ailab_operator_summary`
- `ailab_incidents_active`
- `ailab_slo_status`
- `ailab_health_latency`
- `ailab_memory_search`

No permitidas todavía:
- tools que escriban archivos
- tools que hagan git commit/push
- tools que reinicien servicios
- tools que modifiquen runtime
- tools que modifiquen Prometheus/Grafana
- shell remoto genérico

## Perfil OpenCode

OpenCode puede usar:
- tools read-only
- prompts futuros de fase
- resources futuros de contexto
- acciones mutables solo con aprobación humana en fases posteriores

## Perfil LM Studio

LM Studio debe usar inicialmente:
- solo tools read-only
- sin filesystem libre
- sin shell
- sin git write
- sin reinicios
- sin secretos en contexto
- sin acciones mutables

## Resources futuros recomendados

- `resource://ailab/runtime/health`
- `resource://ailab/models/inventory`
- `resource://ailab/router/policy-summary`
- `resource://ailab/audits/latest`
- `resource://ailab/roadmap/current`
- `resource://ailab/incidents/active`

## Prompts futuros recomendados

- `prompt://ailab/phase/read-only-audit`
- `prompt://ailab/phase/safe-commit`
- `prompt://ailab/phase/runtime-smoke`
- `prompt://ailab/report/spanish-final`
- `prompt://ailab/astro/no-redesign`

## Riesgos

- MCP activo vive fuera del repo en `/mnt/mcp_server`.
- Sin token actual.
- Bind LAN sin firewall sería inseguro.
- Duplicidad entre `/opt/ai-lab/mcp` y `/mnt/mcp_server`.
- LM Studio podría invocar tools automáticamente si se permite.
- Falta catálogo de resources/prompts.

## Fases posteriores

1. `AI-LAB-MCP-TOOLS-CATALOG-VALIDATION-01`
2. `AI-LAB-MCP-TOKEN-AUTH-READONLY-01`
3. `AI-LAB-MCP-FIREWALL-ALLOWLIST-01`
4. `AI-LAB-LMSTUDIO-MCP-LAN-SMOKE-01`
5. `AI-LAB-MCP-CONTROL-PLANE-REPO-UNIFICATION-01`

## Decisión

No exponer MCP a LAN hasta completar token + firewall allowlist.
