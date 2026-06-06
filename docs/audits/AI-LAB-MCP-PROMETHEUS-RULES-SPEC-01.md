# AI-LAB-MCP-PROMETHEUS-RULES-SPEC-01

- Resultado: PASS
- HEAD/base: `2495706f`
- Git sync: `main...origin/main`

## Resumen

Se definio una especificacion documental para integrar metricas MCP en Prometheus sin modificar Prometheus real, Grafana, dashboards, rules activas ni runtime MCP.

La especificacion propone scraping inicial solo sobre `8091`, deja `8092` fuera de scrape por seguridad de token y documenta recording rules, alert rules y runbook operativo para una futura fase de implementacion.

## Estado MCP read-only

- `ailab-mcp-semantic-gateway.service`: `active`, `enabled`
- `ailab-mcp-lan-gateway.service`: `active`, `enabled`
- `127.0.0.1:8091`: LISTEN
- `0.0.0.0:8092`: LISTEN

## `/metrics` validado

- `8091 /metrics`: responde correctamente
- `8092 /metrics` sin token: `401 Unauthorized`

## Tests

Ejecutados:

- `tests/test_mcp_runtime_snapshot_01.py`
- `tests/test_mcp_runtime_metrics_01.py`

Resultado:

- `10 passed`

## Secret scan

Resultado: limpio de secretos reales.

Aceptable:

- placeholders/patrones de test
- referencias documentales existentes

No detectado:

- token real
- bearer real
- claves privadas reales

## Scrape propuesto

Propuesta inicial documentada:

- scrape solo `127.0.0.1:8091`
- labels fijas:
  - `service="semantic"`
  - `endpoint="8091"`
  - `bind="local"`

## Decision sobre 8092/token

Decision documentada:

- no scrape directo de `8092` en la primera implementacion Prometheus
- `8092` permanece protegido por token
- futuras opciones documentadas sin tocar token real

## Recording rules propuestas

Documentadas:

- `ailab_mcp:requests_rate5m`
- `ailab_mcp:tool_calls_rate5m`
- `ailab_mcp:tool_errors_rate5m`
- `ailab_mcp:auth_failures_rate5m`
- `ailab_mcp:auth_success_rate5m`
- `ailab_mcp:request_latency_p95_5m`
- `ailab_mcp:tool_latency_p95_5m`

## Alertas propuestas

Documentadas:

- `MCPSemanticDown`
- `MCPMetricsMissing`
- `MCPAuthFailuresHigh`
- `MCPToolErrorsHigh`
- `MCPRequestLatencyHigh`
- `MCPToolLatencyHigh`
- `MCPUnexpectedNoTraffic`
- `MCPBuildInfoMissing`

## Runbook

La spec incluye runbook por alerta con:

- significado
- impacto
- primeras comprobaciones
- lista explicita de acciones que no deben automatizarse
- comandos read-only recomendados

## Prometheus/Grafana real

- Prometheus real tocado: no
- Grafana real tocado: no
- reglas reales tocadas: no
- dashboards reales tocados: no

## Runtime y servicios

- MCP runtime tocado: no
- `/mnt/mcp_server` tocado: no
- servicios reiniciados: no
- sudo usado: no
- token leido/mostrado: no

## Siguiente fase

- `AI-LAB-MCP-PROMETHEUS-RULES-SPEC-PUSH-01`
- despues `AI-LAB-MCP-PROMETHEUS-RULES-IMPLEMENTATION-01` si se aprueba
