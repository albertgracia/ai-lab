# AI-LAB-MCP-RUNTIME-SNAPSHOT-SYNC-APPLY-01

## Resultado

PARTIAL

## Contexto

Aplicación controlada al runtime real `/mnt/mcp_server` de la implementación MCP de métricas previamente validada en el snapshot versionado del repo.

## HEAD / base

- HEAD de trabajo durante APPLY: `37139ffc` o superior
- Estado git previo: `main...origin/main [ahead 1]`

## Backup y rollback

- Backup dir: `/home/albert/backups/ai-lab/mcp-runtime-apply/20260606-210855`
- Rollback script: `/tmp/rollback-mcp-runtime-metrics-apply.sh`
- Apply dir: `/tmp/ai-lab-mcp-runtime-apply-20260606-210855`

## Archivos copiados

Aplicación por allowlist exacta:

- `mcp/runtime-mcp/server.py` -> `/mnt/mcp_server/server.py`
- `mcp/runtime-mcp/lan_server.py` -> `/mnt/mcp_server/lan_server.py`
- `mcp/runtime-mcp/metrics.py` -> `/mnt/mcp_server/metrics.py`
- `mcp/runtime-mcp/tools/__init__.py` -> `/mnt/mcp_server/tools/__init__.py`

## Confirmaciones de aplicación

- allowlist exacta: sí
- sync ciego: no
- `rsync --delete`: no usado
- `README.md` copiado: no
- `SYNC-POLICY.md` copiado: no
- `docs/` copiado: no

## Preservación runtime-only

- `/mnt/mcp_server/logs/`: preservado
- `/mnt/mcp_server/logs/.gitkeep`: preservado
- `__pycache__`: preservado
- `*.pyc`: preservado

## Checksums

Los checksums post-copia de runtime coincidieron con los del snapshot repo para:

- `server.py`
- `lan_server.py`
- `metrics.py`
- `tools/__init__.py`

## Reinicios realizados

Se reiniciaron únicamente:

- `ailab-mcp-semantic-gateway.service`
- `ailab-mcp-lan-gateway.service`

## Estado final de servicios

- `ailab-mcp-semantic-gateway.service`: `active`, `enabled`
- `ailab-mcp-lan-gateway.service`: `active`, `enabled`

## Estado final de puertos

- `127.0.0.1:8091` LISTEN
- `0.0.0.0:8092` LISTEN

## Endpoints MCP

### 8091

- `/mcp` con curl simple: `406 Not Acceptable`
- Interpretación: esperado para cliente sin `Accept: text/event-stream`

### 8092

- `/mcp` sin token: `401 Unauthorized`
- Interpretación: esperado para gateway LAN con token-auth

## Endpoint /metrics

### 8091

`/metrics` responde `200 OK` y expone métricas MCP.

Métricas detectadas en validación:

- `ailab_mcp_up`
- `ailab_mcp_requests_total`
- `ailab_mcp_request_duration_seconds`
- `ailab_mcp_clients_active`
- `ailab_mcp_endpoint_info`
- `ailab_mcp_build_info`

### 8092

`/metrics` sin token devuelve `401 Unauthorized`.

Interpretación:

- el endpoint existe dentro del runtime aplicado
- queda protegido por el middleware de autenticación LAN
- no se validó el contenido de métricas sin usar token, por política de no tocar token en esta fase

## Tests

Ejecutados:

- `tests/test_mcp_runtime_snapshot_01.py`
- `tests/test_mcp_runtime_metrics_01.py`

Resultado:

- pre-apply: `10 passed`
- post-apply: `10 passed`

## Secret scan

Resultado: limpio de secretos reales.

Aceptable:

- placeholders/patrones de test
- referencias documentales previas

No detectado:

- token real
- bearer real
- claves privadas reales

## Logs post-restart

### Semantic gateway

- sin crashloop
- sin traceback crítico
- restart limpio
- `/metrics` servido con `200 OK`

### LAN gateway

- servicio activo y estable tras restart
- se observaron warnings no críticos:
  - `ASGI callable returned without completing response.`
- se observaron `GET /mcp` desde `192.168.1.50` con `404 Not Found`
- se observó `401 Unauthorized` esperado en prueba local sin token
- se observó `GET /metrics` sin token con `401 Unauthorized`

## Token / seguridad

- token leído o mostrado: no
- filtración de secretos en métricas: no observada
- Prometheus tocado: no
- Grafana tocado: no
- UFW tocado: no
- OpenCode tocado: no
- LM Studio tocado: no
- Docker tocado: no
- Astro tocado: no

## Cambios operativos

- `/mnt/mcp_server` modificado: sí
- servicios MCP reiniciados: sí
- servicios no-MCP reiniciados: no
- rollback ejecutado: no

## Evaluación

Resultado `PARTIAL` por dos motivos:

1. `8092 /metrics` no quedó validado con contenido porque el endpoint LAN exige token y en esta fase no se usó token.
2. Los logs del gateway LAN muestran warnings no críticos y respuestas `404` para `GET /mcp` desde un cliente LAN tras el restart, lo que conviene revisar en smoke posterior.

## Siguiente fase recomendada

- `AI-LAB-MCP-RUNTIME-SNAPSHOT-SYNC-APPLY-PUSH-01`
- después `AI-LAB-MCP-OBSERVABILITY-METRICS-SMOKE-01`
