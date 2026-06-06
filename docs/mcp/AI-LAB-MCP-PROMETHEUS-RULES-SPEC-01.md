# AI-LAB-MCP-PROMETHEUS-RULES-SPEC-01

## Objetivo

Definir una especificacion segura y minima para integrar las metricas MCP de AI-LAB en Prometheus mediante scraping, recording rules y alert rules, sin tocar todavia Prometheus real, Grafana, dashboards ni servicios.

## Estado actual

- Runtime MCP activo:
  - `8091` -> `127.0.0.1:8091`, `active`, `enabled`
  - `8092` -> `0.0.0.0:8092`, `active`, `enabled`
- `8091 /metrics` responde correctamente en formato Prometheus.
- `8092 /metrics` sin token devuelve `401 Unauthorized`.
- `8092 /metrics` con token no se valida en esta fase por disciplina de seguridad.
- `ailab_mcp_clients_active` existe pero hoy queda inicializada a `0`.
- Persisten warnings LAN conocidos:
  - `ASGI callable returned without completing response`
  - `GET /mcp` `404` desde `192.168.1.50`

## Metricas MCP disponibles

Metricas implementadas en runtime MCP:

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

## Evidencia observada en smoke

Validado en `8091 /metrics`:

- `ailab_mcp_up`
- `ailab_mcp_requests_total`
- `ailab_mcp_request_duration_seconds`
- `ailab_mcp_clients_active`
- `ailab_mcp_endpoint_info`
- `ailab_mcp_build_info`

Tambien se confirmo la presencia de histogram buckets en `ailab_mcp_request_duration_seconds_bucket`, por lo que las recording rules de latencia pueden proponerse como reglas activas y no como placeholders.

## Decision de scraping

### Decision principal

Scrape inicial solo para `127.0.0.1:8091`.

Motivos:

- evita introducir token en Prometheus en la primera iteracion
- reduce complejidad de seguridad
- permite observar disponibilidad y trafico MCP local sin tocar el gateway LAN protegido
- es coherente con el estado smoke ya validado

### Decision sobre `8092`

No hacer scrape directo de `8092` en esta primera implementacion de Prometheus.

Opciones futuras documentadas:

1. Mantener scrape solo de `8091` y dejar `8092` como endpoint protegido sin scraping directo.
2. Definir token file controlado para Prometheus si se decide observar el gateway LAN directamente.
3. Exponer metricas LAN agregadas desde `8091` sin token, pero solo mediante implementacion explicita posterior.

### No-go de seguridad

- no exponer `8092 /metrics` sin token
- no copiar token en YAML de reglas o scrape configs versionados
- no documentar ni mostrar el valor real del token

## Scrape config propuesto

```yaml
scrape_configs:
  - job_name: "ai-lab-mcp-semantic"
    metrics_path: /metrics
    static_configs:
      - targets: ["127.0.0.1:8091"]
        labels:
          service: "semantic"
          endpoint: "8091"
          bind: "local"
```

## Recording rules propuestas

```yaml
groups:
  - name: ai_lab_mcp_recording_rules
    rules:
      - record: ailab_mcp:requests_rate5m
        expr: sum by (endpoint, service, bind) (rate(ailab_mcp_requests_total[5m]))

      - record: ailab_mcp:tool_calls_rate5m
        expr: sum by (endpoint, service, tool, status) (rate(ailab_mcp_tool_calls_total[5m]))

      - record: ailab_mcp:tool_errors_rate5m
        expr: sum by (endpoint, service, tool) (rate(ailab_mcp_tool_errors_total[5m]))

      - record: ailab_mcp:auth_failures_rate5m
        expr: sum by (endpoint, service) (rate(ailab_mcp_auth_failures_total[5m]))

      - record: ailab_mcp:auth_success_rate5m
        expr: sum by (endpoint, service) (rate(ailab_mcp_auth_success_total[5m]))

      - record: ailab_mcp:request_latency_p95_5m
        expr: histogram_quantile(0.95, sum by (le, endpoint, service) (rate(ailab_mcp_request_duration_seconds_bucket[5m])))

      - record: ailab_mcp:tool_latency_p95_5m
        expr: histogram_quantile(0.95, sum by (le, endpoint, service, tool) (rate(ailab_mcp_tool_duration_seconds_bucket[5m])))
```

## Alert rules propuestas

```yaml
groups:
  - name: ai_lab_mcp_alerts
    rules:
      - alert: MCPSemanticDown
        expr: ailab_mcp_up{endpoint="8091",service="semantic"} == 0
        for: 2m
        labels:
          severity: critical
          domain: mcp
        annotations:
          summary: "AI-LAB MCP semantic gateway down"
          description: "8091 MCP semantic metrics report down."

      - alert: MCPMetricsMissing
        expr: absent(ailab_mcp_up{endpoint="8091",service="semantic"})
        for: 5m
        labels:
          severity: warning
          domain: mcp
        annotations:
          summary: "AI-LAB MCP metrics missing"
          description: "Prometheus is not receiving MCP metrics from 8091."

      - alert: MCPAuthFailuresHigh
        expr: sum(rate(ailab_mcp_auth_failures_total[10m])) > 0.2
        for: 10m
        labels:
          severity: warning
          domain: mcp
        annotations:
          summary: "AI-LAB MCP auth failures high"
          description: "MCP LAN/auth failures are above expected baseline."

      - alert: MCPToolErrorsHigh
        expr: sum(rate(ailab_mcp_tool_errors_total[10m])) > 0.05
        for: 10m
        labels:
          severity: warning
          domain: mcp
        annotations:
          summary: "AI-LAB MCP tool errors high"
          description: "MCP tool error rate is elevated."

      - alert: MCPRequestLatencyHigh
        expr: ailab_mcp:request_latency_p95_5m > 1
        for: 10m
        labels:
          severity: warning
          domain: mcp
        annotations:
          summary: "AI-LAB MCP request latency high"
          description: "MCP request p95 latency is above 1s."

      - alert: MCPToolLatencyHigh
        expr: ailab_mcp:tool_latency_p95_5m > 2
        for: 10m
        labels:
          severity: warning
          domain: mcp
        annotations:
          summary: "AI-LAB MCP tool latency high"
          description: "MCP tool p95 latency is above 2s."

      - alert: MCPUnexpectedNoTraffic
        expr: sum(rate(ailab_mcp_requests_total[30m])) == 0
        for: 30m
        labels:
          severity: info
          domain: mcp
        annotations:
          summary: "AI-LAB MCP no recent traffic"
          description: "No MCP requests observed recently. This can be normal outside active use."

      - alert: MCPBuildInfoMissing
        expr: absent(ailab_mcp_build_info)
        for: 10m
        labels:
          severity: info
          domain: mcp
        annotations:
          summary: "AI-LAB MCP build info missing"
          description: "MCP build info metric is absent."
```

## Severidades propuestas

- `critical`
  - `MCPSemanticDown`
- `warning`
  - `MCPMetricsMissing`
  - `MCPAuthFailuresHigh`
  - `MCPToolErrorsHigh`
  - `MCPRequestLatencyHigh`
  - `MCPToolLatencyHigh`
- `info`
  - `MCPUnexpectedNoTraffic`
  - `MCPBuildInfoMissing`

## Runbook por alerta

### `MCPSemanticDown`

- Significado: `8091` no expone estado `up`.
- Impacto: observabilidad MCP local y herramientas remotas pueden quedar degradadas o caidas.
- Primeras comprobaciones:
  - `systemctl status ailab-mcp-semantic-gateway.service --no-pager`
  - `ss -ltnp | grep -E "8091|8092"`
  - `curl -sS http://127.0.0.1:8091/metrics | grep ailab_mcp_up`
  - `journalctl -u ailab-mcp-semantic-gateway.service -n 100 --no-pager`
- No hacer automaticamente:
  - no reiniciar servicios desde la alerta
  - no tocar token
  - no tocar firewall

### `MCPMetricsMissing`

- Significado: Prometheus no recibe `ailab_mcp_up` desde `8091`.
- Impacto: scraping roto, endpoint `/metrics` no visible o config Prometheus ausente.
- Primeras comprobaciones:
  - `curl -sS http://127.0.0.1:8091/metrics | head`
  - revisar job `ai-lab-mcp-semantic` en configuracion propuesta
  - `journalctl -u ailab-mcp-semantic-gateway.service -n 100 --no-pager`
- No hacer automaticamente:
  - no modificar Prometheus runtime en caliente fuera de fase dedicada

### `MCPAuthFailuresHigh`

- Significado: la tasa de fallos de autenticacion MCP LAN supera baseline.
- Impacto: clientes LAN mal configurados, intentos indebidos o ruido operativo.
- Primeras comprobaciones:
  - `journalctl -u ailab-mcp-lan-gateway.service -n 100 --no-pager`
  - revisar patrones `401 Unauthorized`
  - confirmar si el origen es `127.0.0.1` por checks internos o un cliente LAN legitimo
- No hacer automaticamente:
  - no rotar token
  - no abrir `8092` sin auth

### `MCPToolErrorsHigh`

- Significado: herramientas MCP estan fallando por encima de baseline.
- Impacto: degradacion funcional parcial del MCP.
- Primeras comprobaciones:
  - `journalctl -u ailab-mcp-semantic-gateway.service -n 100 --no-pager`
  - `journalctl -u ailab-mcp-lan-gateway.service -n 100 --no-pager`
  - `curl -sS http://127.0.0.1:8091/metrics | grep ailab_mcp_tool_errors_total`
- No hacer automaticamente:
  - no reiniciar servicios por defecto

### `MCPRequestLatencyHigh`

- Significado: p95 de requests MCP elevado.
- Impacto: experiencia lenta de herramientas MCP o backend AI-LAB degradado.
- Primeras comprobaciones:
  - `curl -sS http://127.0.0.1:8091/metrics | grep ailab_mcp_request_duration_seconds`
  - correlacionar con estado gateway/router/live-api
  - revisar si hay contencion o timeouts en logs
- No hacer automaticamente:
  - no tocar SLOs del runtime general

### `MCPToolLatencyHigh`

- Significado: p95 de ejecucion de tools elevado.
- Impacto: una o varias tools tardan demasiado.
- Primeras comprobaciones:
  - `curl -sS http://127.0.0.1:8091/metrics | grep ailab_mcp_tool_duration_seconds`
  - revisar dependencias de la tool afectada
- No hacer automaticamente:
  - no desactivar tools

### `MCPUnexpectedNoTraffic`

- Significado: no hay trafico MCP reciente.
- Impacto: normalmente informativo; puede ser inactividad legitima.
- Primeras comprobaciones:
  - `curl -sS http://127.0.0.1:8091/metrics | grep ailab_mcp_requests_total`
  - correlacionar con uso real del operador o clientes
- No hacer automaticamente:
  - no considerar fallo por si solo

### `MCPBuildInfoMissing`

- Significado: falta `ailab_mcp_build_info`.
- Impacto: perdida de trazabilidad de version.
- Primeras comprobaciones:
  - `curl -sS http://127.0.0.1:8091/metrics | grep ailab_mcp_build_info`
  - revisar si hubo drift del runtime MCP
- No hacer automaticamente:
  - no reescribir build metadata manualmente en caliente

## Comandos read-only recomendados

```bash
systemctl status ailab-mcp-semantic-gateway.service --no-pager
systemctl status ailab-mcp-lan-gateway.service --no-pager
ss -ltnp | grep -E "8091|8092"
curl -sS http://127.0.0.1:8091/metrics | grep ailab_mcp_up
journalctl -u ailab-mcp-semantic-gateway.service -n 100 --no-pager
journalctl -u ailab-mcp-lan-gateway.service -n 100 --no-pager
```

## Seguridad

- No hacer scrape directo de `8092` mientras requiera token y no exista mecanismo seguro aprobado.
- No poner token en `scrape_configs` versionados.
- No documentar el valor del token.
- No usar alertas que reinicien servicios o cambien configuracion.

## No-go list

- no reiniciar MCP desde alertas
- no rotar token desde alertas
- no abrir `8092` sin autenticacion
- no modificar firewall automaticamente
- no tocar Prometheus o Grafana reales fuera de fase de implementacion explicita

## Plan de implementacion futura

Fase futura sugerida:

1. Crear archivo de scrape config o integrarlo en el job adecuado de Prometheus.
2. Crear archivo de recording/alert rules MCP separado.
3. Validar con `promtool check rules`.
4. Aplicar en Prometheus solo en fase dedicada de implementation/apply.
5. Verificar que aparecen en Prometheus:
   - `ailab_mcp_up`
   - `ailab_mcp_build_info`
   - `ailab_mcp_requests_total`
6. Verificar que no disparan alertas criticas falsas.
7. Documentar rollback de rules.

## Validaciones futuras obligatorias

- `promtool check rules` si `promtool` esta disponible
- `promtool check config` si se modifica config asociada
- no tocar Grafana en la primera fase de implementacion
- no tocar runtime MCP
- validar carga de reglas y ausencia de errores PromQL
- validar que `8092` siga protegido sin token

## Siguiente fase recomendada

- `AI-LAB-MCP-PROMETHEUS-RULES-SPEC-PUSH-01`
- despues `AI-LAB-MCP-PROMETHEUS-RULES-IMPLEMENTATION-01` si se aprueba
