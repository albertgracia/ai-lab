# AI-LAB-MCP-OBSERVABILITY-METRICS-IMPLEMENTATION-01

## Objetivo

Implementar una primera version segura y minima de observabilidad MCP en el snapshot versionado `mcp/runtime-mcp/`, sin tocar `/mnt/mcp_server`, sin reiniciar servicios y sin modificar Prometheus o Grafana.

## Alcance

Esta implementacion es repo-only.

- Se modifica solo `mcp/runtime-mcp/**`.
- Se anade el test `tests/test_mcp_runtime_metrics_01.py`.
- No se aplica nada al runtime real.
- No se cambia auth, puertos, tools ni systemd.

## Archivos modificados

- `mcp/runtime-mcp/metrics.py`
- `mcp/runtime-mcp/server.py`
- `mcp/runtime-mcp/lan_server.py`
- `mcp/runtime-mcp/tools/__init__.py`
- `tests/test_mcp_runtime_metrics_01.py`

## Diseno aplicado

### Modulo nuevo `metrics.py`

Se crea un registro de metricas en memoria con render Prometheus texto via `render_prometheus_metrics()`.

Responsabilidades:

- counters, gauges e histogramas en memoria
- normalizacion de labels permitidas
- rechazo de labels prohibidas
- endpoint context fijo para `8091` y `8092`
- render Prometheus sin exponer secretos
- middleware HTTP para contar requests MCP y latencias

### Integracion en gateways del snapshot

Se anade integracion minima y segura en el snapshot:

- `server.py`
  - bootstrap de metricas para `8091`
  - middleware de requests MCP
  - ruta `GET /metrics`
- `lan_server.py`
  - bootstrap de metricas para `8092`
  - middleware de requests MCP
  - conteo de auth success/failure en el middleware existente
  - ruta `GET /metrics`

### Integracion de tool calls

`tools/__init__.py` instrumenta el registro de tools sin modificar cada tool individual:

- wrapper de `mcp.tool(...)`
- conteo de `ailab_mcp_tool_calls_total`
- conteo de `ailab_mcp_tool_errors_total`
- histograma `ailab_mcp_tool_duration_seconds`

## Metricas implementadas

Implementadas en esta fase:

- `ailab_mcp_up`
- `ailab_mcp_requests_total`
- `ailab_mcp_request_duration_seconds`
- `ailab_mcp_auth_failures_total`
- `ailab_mcp_auth_success_total`
- `ailab_mcp_tool_calls_total`
- `ailab_mcp_tool_errors_total`
- `ailab_mcp_tool_duration_seconds`
- `ailab_mcp_initialize_total`
- `ailab_mcp_clients_active`
- `ailab_mcp_endpoint_info`
- `ailab_mcp_build_info`

## Metricas con limitaciones conocidas

- `ailab_mcp_clients_active`
  - existe y se expone
  - en esta fase queda inicializada como gauge base `0`
  - no cuenta sesiones MCP reales todavia
  - refinamiento recomendado en una implementacion posterior si se decide instrumentar lifecycle de sesiones

## Labels permitidas

Labels usadas o aceptadas por esta implementacion:

- `endpoint`
- `bind`
- `service`
- `method`
- `tool`
- `status`
- `mode`
- `auth`
- `version`
- `python_version`
- `mcp_version`
- `commit`

## Labels prohibidas

Se rechazan o no se almacenan labels sensibles como:

- `token`
- `authorization`
- `prompt`
- `query`
- `payload`
- `arguments`
- `result`
- `peer_ip`
- `stacktrace`
- `client_info`
- `memory_result`

## Herramientas permitidas para label `tool`

- `ailab_status`
- `ailab_runtime_health`
- `ailab_route_preview`
- `ailab_operator_summary`
- `ailab_incidents_active`
- `ailab_slo_status`
- `ailab_health_latency`
- `ailab_memory_search`
- `unknown`

## Tests anadidos

Nuevo test:

- `tests/test_mcp_runtime_metrics_01.py`

Cobertura minima verificada:

- nombres de metricas esperadas
- render Prometheus texto basico
- labels permitidas
- ausencia de markers sensibles
- normalizacion de tool desconocida a `unknown`
- normalizacion segura de endpoint desconocido
- ausencia de IP completa como label por defecto
- histogramas basicos renderizados

## Limitaciones

- no se aplica a `/mnt/mcp_server`
- no se reinician servicios
- no se cambia Prometheus ni Grafana
- no se introduce scrape real en esta fase
- `clients_active` no representa sesiones reales todavia
- la ruta `/metrics` se integra solo en el snapshot repo-only y no en el runtime vivo actual

## Resultado esperado de despliegue posterior

Cuando esta implementacion se sincronice en una fase futura controlada, cada gateway del snapshot podra exponer:

- `GET /metrics`
- metricas de requests MCP
- metricas de auth LAN
- metricas de initialize
- metricas de tools y latencias

## No aplicacion al runtime real

Confirmado:

- no se modifica `/mnt/mcp_server`
- no se sincroniza repo -> runtime en esta fase
- no se toca token real
- no se reinician servicios

## Siguiente fase recomendada

- `AI-LAB-MCP-OBSERVABILITY-METRICS-IMPLEMENTATION-PUSH-01`
- despues `AI-LAB-MCP-RUNTIME-SNAPSHOT-SYNC-DRY-RUN-02`
