# AI-LAB-MCP-OBSERVABILITY-METRICS-SMOKE-01

- Resultado: PARTIAL
- HEAD/base: `849994d1`
- Smoke dir: `/tmp/ai-lab-mcp-metrics-smoke-20260606-212432`
- Git sync: `main...origin/main`

## Resumen ejecutivo

Se ejecuto el smoke read-only sobre el runtime MCP ya aplicado. El endpoint `8091 /metrics` responde correctamente con formato Prometheus y metricas MCP visibles. El endpoint `8092` protege correctamente tanto `/metrics` como `/mcp` sin token devolviendo `401`.

El resultado queda en `PARTIAL` no bloqueante por dos razones conocidas:

- no se valido `8092 /metrics` con token porque no habia `AILAB_MCP_TOKEN` exportado en entorno seguro para esta fase
- persisten warnings LAN conocidos (`ASGI callable returned without completing response`) y `GET /mcp` `404` desde `192.168.1.50`

## Estado 8091 y 8092

- `ailab-mcp-semantic-gateway.service`: `active`, `enabled`
- `ailab-mcp-lan-gateway.service`: `active`, `enabled`
- `127.0.0.1:8091`: LISTEN
- `0.0.0.0:8092`: LISTEN

## `/metrics` en 8091

Validacion:

- responde correctamente
- formato Prometheus basico presente (`# HELP`, `# TYPE`, series `ailab_mcp_*`)
- labels bounded detectadas:
  - `endpoint="8091"`
  - `bind="local"`
  - `service="semantic"`

Metricas detectadas en 8091:

- `ailab_mcp_up`
- `ailab_mcp_requests_total`
- `ailab_mcp_request_duration_seconds`
- `ailab_mcp_clients_active`
- `ailab_mcp_endpoint_info`
- `ailab_mcp_build_info`

Metricas esperadas visibles en la salida filtrada:

- `ailab_mcp_up`
- `ailab_mcp_requests_total`
- `ailab_mcp_build_info`
- `ailab_mcp_endpoint_info`

## Secret check de metricas 8091

Resultado: sin coincidencias sensibles.

No se observaron:

- `Authorization`
- `Bearer`
- `AILAB_MCP_TOKEN`
- `token=`
- `prompt=`
- `query=`
- `payload=`
- secretos reales

## `/metrics` en 8092 sin token

Resultado:

- `401 Unauthorized`

Interpretacion:

- proteccion correcta confirmada

## `/mcp` en 8092 sin token

Resultado:

- `401 Unauthorized`

Interpretacion:

- proteccion correcta confirmada

## `/metrics` en 8092 con token

Resultado:

- `SKIP`

Motivo:

- no habia `AILAB_MCP_TOKEN` exportado como variable de entorno segura en esta fase
- no se leyo `/etc/ai-lab/mcp-lan.env`
- no se mostro token en ningun momento

## `/mcp` en 8091 con curl simple

Resultado observado:

- `406 Not Acceptable`

Interpretacion:

- comportamiento aceptable con curl simple sin cliente MCP adecuado

## Logs

### Semantic gateway

- sin crashloop
- sin tracebacks criticos
- `GET /metrics` con `200 OK` observado
- `GET /mcp` con `406` esperado por curl simple

### LAN gateway

- sin crashloop
- sin traceback Python completo
- warning presente: `ASGI callable returned without completing response`
- `GET /mcp` `404` desde `192.168.1.50` persiste tras el apply
- `GET /metrics` sin token con `401` esperado
- `GET /mcp` sin token con `401` esperado

## Flags de logs

- ASGI warning: si
- 404 LAN: si
- crashloop: no
- traceback critico: no

## Tests

Ejecutados:

- `tests/test_mcp_runtime_snapshot_01.py`
- `tests/test_mcp_runtime_metrics_01.py`

Resultado:

- `10 passed`

## Secret scan repo

Resultado: limpio de secretos reales.

Aceptable:

- placeholders/patrones de test
- referencias documentales previas

## Confirmaciones de no intervencion

- no se uso sudo para cambios operativos
- no se reinicio ningun servicio
- no se modifico `/mnt/mcp_server`
- no se modifico `mcp/runtime-mcp`
- no se leyo ni mostro token real
- no se tocaron Prometheus ni Grafana
- no se toco UFW
- no se tocaron OpenCode ni LM Studio
- no se hizo push
- no se creo tag

## Evaluacion final

Resultado `PARTIAL` no bloqueante.

La smoke confirma que:

- `8091` expone metricas MCP reales
- `8092` mantiene proteccion correcta sin token
- no hay leakage de secretos en metricas observadas
- el runtime sigue estable

Lo pendiente es validar `8092 /metrics` con token en una fase controlada o asumir ese check como opcional de operador si la politica de token no permite inyectarlo en entorno seguro para smoke.

## Siguiente fase recomendada

- `AI-LAB-MCP-OBSERVABILITY-METRICS-SMOKE-PUSH-01`
- despues `AI-LAB-MCP-PROMETHEUS-RULES-SPEC-01`
- o fase correctiva LAN si se decide investigar los `404` y el warning ASGI
