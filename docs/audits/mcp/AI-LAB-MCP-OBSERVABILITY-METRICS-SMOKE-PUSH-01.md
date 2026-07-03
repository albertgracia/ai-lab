# AI-LAB-MCP-OBSERVABILITY-METRICS-SMOKE-PUSH-01

## Resultado

PASS

## Objetivo

Publicar el smoke de observabilidad de metricas MCP tras aplicar `/metrics` al runtime real.

## Commit publicado

- `5ae00eca` ? `docs(audit): smoke mcp observability metrics`

## Estado publicado del smoke

La fase `AI-LAB-MCP-OBSERVABILITY-METRICS-SMOKE-01` quedo como `PARTIAL` no bloqueante.

## Validaciones correctas

- `ailab-mcp-semantic-gateway.service`: active/enabled.
- `ailab-mcp-lan-gateway.service`: active/enabled.
- `8091 /metrics`: OK.
- Formato Prometheus: OK.
- Labels detectadas:
  - `endpoint="8091"`
  - `bind="local"`
  - `service="semantic"`
- Metricas detectadas:
  - `ailab_mcp_up`
  - `ailab_mcp_requests_total`
  - `ailab_mcp_request_duration_seconds`
  - `ailab_mcp_clients_active`
  - `ailab_mcp_endpoint_info`
  - `ailab_mcp_build_info`
- `8092 /metrics` sin token: `401 Unauthorized`, proteccion correcta.
- Tests: PASS.
- Secret scan: limpio.
- Sudo: no usado, `SUDO_LOCKED`.
- Token: no leido/no mostrado.
- `/mnt/mcp_server`: no modificado durante smoke.
- Servicios: no reiniciados durante smoke.
- Prometheus/Grafana: no tocados.

## Motivos del PARTIAL

- `8092 /metrics` con token no se valido porque no habia `AILAB_MCP_TOKEN` exportado en entorno seguro.
- Persisten warnings LAN no criticos:
  - `ASGI callable returned without completing response`
  - `GET /mcp` `404` desde `192.168.1.50`

## Estado operativo preservado en esta fase de push

- No se uso sudo.
- No se reiniciaron servicios.
- No se modifico `/mnt/mcp_server`.
- No se toco token.
- No se toco UFW/firewall.
- No se toco Prometheus.
- No se toco Grafana.
- No se toco OpenCode.
- No se toco LM Studio.
- No se toco Astro.
- No se toco Docker.
- No hubo reboot.
- No se creo tag.

## Siguiente fase recomendada

Dos opciones:

1. `AI-LAB-MCP-PROMETHEUS-RULES-SPEC-01`
2. `AI-LAB-MCP-LAN-ASGI-404-TRIAGE-01` si se decide investigar antes el warning ASGI y el `GET /mcp` 404 LAN.
