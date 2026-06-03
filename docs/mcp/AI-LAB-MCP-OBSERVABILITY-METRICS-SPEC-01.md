# AI-LAB MCP — Spec de Observabilidad y Métricas

| Propiedad | Valor |
|---|---|
| Fase | `AI-LAB-MCP-OBSERVABILITY-METRICS-SPEC-01` |
| Fecha | 2026-06-03 |
| HEAD de referencia | `91a8070d` |
| Autor | Operador `albert@192.168.1.30` |
| Estado | Spec — solo documentación |
| Implementación | Futura — `AI-LAB-MCP-OBSERVABILITY-METRICS-IMPLEMENTATION-01` |

---

## 1. Estado actual

| Servicio | Puerto | Modo | Active | Enabled | Tools |
|---|---|---|---|---|---|
| Semantic Gateway | `127.0.0.1:8091` | Local, read-only, sin token | active | enabled | 8 tools |
| LAN Gateway | `0.0.0.0:8092` | LAN, read-only, token-auth | active | enabled | 8 tools |

**UFW:** inactive.
**Snapshot:** `mcp/runtime-mcp/` — 0 drift, tests 5/5 PASS.
**Tools:** 8 (5 bajo, 3 medio, 0 alto).
**Resources propuestos:** 10 (spec publicada).
**Prompts propuestos:** 7 (spec publicada).
**Métricas MCP actuales:** 0 — no existe endpoint `/metrics` ni instrumentación Prometheus en el código MCP.

---

## 2. Motivación

| Razón | Detalle |
|---|---|
| Visibilidad sin modificar tools existentes | Métricas separadas de tools, sin contaminar JSON de respuesta |
| Alertas tempranas | Detectar auth failures, tool errors, latencias altas antes de que afecten a clientes |
| SLOs medibles | Cuantificar disponibilidad y rendimiento de `8091` y `8092` |
| Diagnóstico de clientes | Saber qué clientes (OpenCode vs LM Studio) están usando el MCP |
| Seguridad | Detectar patrones anómalos de herramientas no esperadas o auth failures masivos |

---

## 3. Métricas Prometheus propuestas

Todas las métricas usan el prefijo `ailab_mcp_`.

### 3.1 `ailab_mcp_up`

| Propiedad | Valor |
|---|---|
| Tipo | gauge |
| Descripción | Indica si el endpoint MCP está operativo (1 = up, 0 = down) |
| Labels permitidas | `endpoint`, `bind`, `service` |
| Labels prohibidas | token, peer IP, prompt |
| Cardinalidad esperada | 2 (8091, 8092) |
| Fuente | Health check interno periódico |
| Riesgo | Bajo |
| Ejemplo PromQL | `ailab_mcp_up{endpoint="8092"} == 0` |
| Motivo | Saber al instante si algún endpoint está caído |

### 3.2 `ailab_mcp_requests_total`

| Propiedad | Valor |
|---|---|
| Tipo | counter |
| Descripción | Total de requests MCP recibidas |
| Labels permitidas | `endpoint`, `bind`, `method` (initialize, tools/list, resources/list, etc.) |
| Labels prohibidas | token, Authorization, prompt, peer IP |
| Cardinalidad esperada | ~10 métodos x 2 endpoints = 20 |
| Fuente | Middleware de request en server.py / lan_server.py |
| Riesgo | Bajo |
| Ejemplo PromQL | `rate(ailab_mcp_requests_total[5m])` |
| Motivo | Volumen de tráfico MCP |

### 3.3 `ailab_mcp_request_duration_seconds`

| Propiedad | Valor |
|---|---|
| Tipo | histogram |
| Descripción | Duración de requests MCP en segundos |
| Labels permitidas | `endpoint`, `bind`, `method` |
| Labels prohibidas | token, Authorization, prompt, peer IP |
| Cardinalidad esperada | ~10 buckets x 2 endpoints = 20 series |
| Fuente | Middleware de timing |
| Riesgo | Bajo |
| Ejemplo PromQL | `histogram_quantile(0.95, rate(ailab_mcp_request_duration_seconds_bucket[5m]))` |
| Motivo | Rendimiento y latencia por método |

### 3.4 `ailab_mcp_auth_failures_total`

| Propiedad | Valor |
|---|---|
| Tipo | counter |
| Descripción | Fallos de autenticación en endpoint 8092 |
| Labels permitidas | `endpoint`, `bind` |
| Labels prohibidas | token, IP exacta, Authorization |
| Cardinalidad esperada | 1 (8092) |
| Fuente | Middleware de auth en lan_server.py |
| Riesgo | Bajo |
| Ejemplo PromQL | `rate(ailab_mcp_auth_failures_total[10m]) > 0.1` |
| Motivo | Detectar ataques o clientes mal configurados |

### 3.5 `ailab_mcp_auth_success_total`

| Propiedad | Valor |
|---|---|
| Tipo | counter |
| Descripción | Autenticaciones exitosas en endpoint 8092 |
| Labels permitidas | `endpoint`, `bind` |
| Labels prohibidas | token, Authorization |
| Cardinalidad esperada | 1 (8092) |
| Fuente | Middleware de auth |
| Riesgo | Bajo |
| Ejemplo PromQL | `rate(ailab_mcp_auth_success_total[5m])` |
| Motivo | Ratio auth éxito/fallo |

### 3.6 `ailab_mcp_tool_calls_total`

| Propiedad | Valor |
|---|---|
| Tipo | counter |
| Descripción | Llamadas a tools MCP |
| Labels permitidas | `endpoint`, `bind`, `tool`, `status` |
| Labels prohibidas | token, prompt, arguments, resultado |
| Cardinalidad esperada | 8 tools x 2 status (success/error) x 2 endpoints = 32 |
| Fuente | Wrapper en `register_all` de tools |
| Riesgo | Bajo |
| Ejemplo PromQL | `rate(ailab_mcp_tool_calls_total{tool="ailab_status"}[5m])` |
| Motivo | Saber qué tools se usan más y si fallan |

### 3.7 `ailab_mcp_tool_errors_total`

| Propiedad | Valor |
|---|---|
| Tipo | counter |
| Descripción | Errores en ejecución de tools |
| Labels permitidas | `endpoint`, `bind`, `tool` |
| Labels prohibidas | stacktrace completo, error message largo |
| Cardinalidad esperada | 8 tools x 2 endpoints = 16 |
| Fuente | Wrapper de tools con try/except |
| Riesgo | Bajo |
| Ejemplo PromQL | `rate(ailab_mcp_tool_errors_total[10m])` |
| Motivo | Detectar tools rotas o backend caído |

### 3.8 `ailab_mcp_tool_duration_seconds`

| Propiedad | Valor |
|---|---|
| Tipo | histogram |
| Descripción | Duración de llamadas a tools |
| Labels permitidas | `endpoint`, `bind`, `tool` |
| Labels prohibidas | token, prompt, arguments |
| Cardinalidad esperada | 8 tools x 2 endpoints x ~5 buckets = 80 |
| Fuente | Wrapper de timing |
| Riesgo | Bajo |
| Ejemplo PromQL | `histogram_quantile(0.95, rate(ailab_mcp_tool_duration_seconds_bucket{tool="ailab_status"}[5m]))` |
| Motivo | Rendimiento por tool |

### 3.9 `ailab_mcp_initialize_total`

| Propiedad | Valor |
|---|---|
| Tipo | counter |
| Descripción | Conexiones initialize recibidas |
| Labels permitidas | `endpoint`, `bind` |
| Labels prohibidas | token, protocol version, client info |
| Cardinalidad esperada | 2 |
| Fuente | Handler de initialize |
| Riesgo | Bajo |
| Ejemplo PromQL | `rate(ailab_mcp_initialize_total[5m])` |
| Motivo | Cuántos clientes se conectan |

### 3.10 `ailab_mcp_clients_active`

| Propiedad | Valor |
|---|---|
| Tipo | gauge |
| Descripción | Clientes actualmente conectados (sesiones activas) |
| Labels permitidas | `endpoint`, `bind` |
| Labels prohibidas | IP, client_id, token |
| Cardinalidad esperada | 2 |
| Fuente | Contador de sesiones activas |
| Riesgo | Bajo |
| Ejemplo PromQL | `ailab_mcp_clients_active` |
| Motivo | Saber cuántos clientes están usando el MCP ahora |

### 3.11 `ailab_mcp_endpoint_info`

| Propiedad | Valor |
|---|---|
| Tipo | info |
| Descripción | Metadatos del endpoint MCP |
| Labels permitidas | `endpoint`, `bind`, `mode` (read-only), `auth` (token/none), `version` |
| Labels prohibidas | token, env |
| Cardinalidad esperada | 2 |
| Fuente | Constantes de configuración |
| Riesgo | Bajo |
| Ejemplo PromQL | `ailab_mcp_endpoint_info{mode="read-only"}` |
| Motivo | Saber qué endpoint tiene auth, qué modo, qué versión |

### 3.12 `ailab_mcp_build_info`

| Propiedad | Valor |
|---|---|
| Tipo | info |
| Descripción | Información de build del servidor MCP |
| Labels permitidas | `python_version`, `mcp_version`, `commit` (short hash) |
| Labels prohibidas | env, token, ruta |
| Cardinalidad esperada | 1 |
| Fuente | Constantes en código |
| Riesgo | Bajo |
| Ejemplo PromQL | `ailab_mcp_build_info` |
| Motivo | Saber qué versión del MCP está corriendo |

---

## 4. Labels permitidas y prohibidas

### Permitidas

| Label | Cardinalidad máxima | Uso |
|---|---|---|
| `endpoint` | 2 (`8091`, `8092`) | Identificar qué puerto |
| `bind` | 2 (`local`, `lan`) | Tipo de bind |
| `service` | 2 (`semantic`, `lan`) | Nombre del servicio |
| `method` | ~10 | Método MCP (initialize, tools/list, etc.) |
| `tool` | 8 | Nombre de la tool |
| `status` | 3 (`success`, `error`, `auth_failed`) | Resultado de la llamada |
| `mode` | 1 (`read-only`) | Modo del endpoint |
| `auth` | 2 (`token`, `none`) | Tipo de auth |
| `version` | 1 | Versión del endpoint |

### Prohibidas

| Label | Razón |
|---|---|
| `token` | Secreto |
| `authorization` | Header completo con Bearer |
| `peer_ip` | IP completa del cliente |
| `prompt` | Prompt del usuario |
| `query` | Query de búsqueda |
| `arguments` | Argumentos de tool |
| `result` | Resultado de tool |
| `stacktrace` | Stacktrace completo |
| `client_info` | Info del cliente |

---

## 5. Cardinalidad

- Total de series estimado: < 200
- Sin etiquetas por token, prompt, query, IP, resultado
- Label `tool` limitado a las 8 tools conocidas
- Label `endpoint` limitado a `8091` y `8092`
- Label `method` limitado a métodos MCP estándar

---

## 6. SLOs MCP propuestos

| SLO | Definición | PromQL sugerido | Warning | Critical | Acción | No acción automática |
|---|---|---|---|---|---|---|
| Disponibilidad 8091 | >= 99.5% en 30d | `(1 - sum(up{endpoint="8091"} == 0) / count(up{endpoint="8091"})) * 100` | < 99.5% | < 99.0% | Revisar systemd | No restart automático |
| Disponibilidad 8092 | >= 99.0% en 30d | Similar a 8091 | < 99.0% | < 98.5% | Revisar systemd y token | No restart automático |
| Auth Failure Ratio | < 5% en 10m | `rate(ailab_mcp_auth_failures_total[10m]) / (rate(ailab_mcp_auth_success_total[10m]) + rate(ailab_mcp_auth_failures_total[10m])) * 100` | > 5% | > 20% | Revisar clientes | No rotar token |
| Tool Error Ratio | < 2% en 10m | `rate(ailab_mcp_tool_errors_total[10m]) / rate(ailab_mcp_tool_calls_total[10m]) * 100` | > 2% | > 5% | Revisar tools y backends | No restart |
| p95 Tool Latency low-risk | < 2s en 10m | `histogram_quantile(0.95, rate(ailab_mcp_tool_duration_seconds_bucket[10m]))` | > 2s | > 5s | Revisar latencia Gateway | No restart |
| p95 Request Latency | < 1s en 10m | `histogram_quantile(0.95, rate(ailab_mcp_request_duration_seconds_bucket[10m]))` | > 1s | > 3s | Revisar runtime | No restart |

---

## 7. Alertas propuestas

### `MCP8091Down`

| Propiedad | Valor |
|---|---|
| Severidad | Critical |
| Expresión | `ailab_mcp_up{endpoint="8091"} == 0` |
| For | 30s |
| Descripción | MCP Semantic Gateway 8091 no responde |
| Runbook | Verificar systemd: `systemctl status ailab-mcp-semantic-gateway.service`. Revisar logs. |
| Acción prohibida | No restart automático |
| Acción permitida | Notificar, revisar logs |

### `MCP8092Down`

| Propiedad | Valor |
|---|---|
| Severidad | Critical |
| Expresión | `ailab_mcp_up{endpoint="8092"} == 0` |
| For | 30s |
| Descripción | MCP LAN Gateway 8092 no responde |
| Runbook | Verificar systemd: `systemctl status ailab-mcp-lan-gateway.service`. Revisar logs. |
| Acción prohibida | No restart automático |
| Acción permitida | Notificar, revisar logs |

### `MCPAuthFailuresHigh`

| Propiedad | Valor |
|---|---|
| Severidad | Warning |
| Expresión | `rate(ailab_mcp_auth_failures_total[5m]) > 0.5` |
| For | 2m |
| Descripción | Alta tasa de fallos de autenticación en 8092 |
| Runbook | Revisar clientes, posible ataque o token rotado. Verificar `/etc/ai-lab/mcp-lan.env`. |
| Acción prohibida | No rotar token automáticamente, no cambiar firewall |
| Acción permitida | Notificar, revisar clientes |

### `MCPToolErrorsHigh`

| Propiedad | Valor |
|---|---|
| Severidad | Warning |
| Expresión | `rate(ailab_mcp_tool_errors_total[5m]) > 0.2` |
| For | 2m |
| Descripción | Alta tasa de errores en tools MCP |
| Runbook | Verificar logs de tools, revisar Gateway/Router |
| Acción prohibida | No restart automático |
| Acción permitida | Notificar, revisar logs |

### `MCPToolLatencyHigh`

| Propiedad | Valor |
|---|---|
| Severidad | Warning |
| Expresión | `histogram_quantile(0.95, rate(ailab_mcp_tool_duration_seconds_bucket[5m])) > 2` |
| For | 2m |
| Descripción | Latencia p95 de tools superior a 2s |
| Runbook | Revisar Gateway/Router, verificar carga |
| Acción prohibida | No restart automático |
| Acción permitida | Notificar, revisar |

### `MCPNoToolCallsRecently`

| Propiedad | Valor |
|---|---|
| Severidad | Info |
| Expresión | `rate(ailab_mcp_tool_calls_total[30m]) == 0` |
| For | 5m |
| Descripción | No se han llamado tools MCP en los últimos 30 minutos |
| Runbook | Verificar que los clientes siguen conectados. Puede ser normal fuera de horario. |
| Acción prohibida | No restart, no deploy |
| Acción permitida | Notificar |

### `MCPUnexpectedToolName`

| Propiedad | Valor |
|---|---|
| Severidad | Warning |
| Expresión | `count(ailab_mcp_tool_calls_total{tool!~"ailab_status|ailab_runtime_health|ailab_route_preview|ailab_slo_status|ailab_health_latency|ailab_operator_summary|ailab_incidents_active|ailab_memory_search"}) > 0` |
| For | 1m |
| Descripción | Se detectó una llamada a una tool no registrada en el catálogo |
| Runbook | Revisar qué tool se llamó. Puede ser un cliente nuevo o un intento de acceso no autorizado. |
| Acción prohibida | No restart automático |
| Acción permitida | Notificar, revisar logs |

### `MCPClientMisconfigured`

| Propiedad | Valor |
|---|---|
| Severidad | Info |
| Expresión | `rate(ailab_mcp_auth_failures_total[5m]) > 0.1 AND rate(ailab_mcp_auth_success_total[5m]) == 0` |
| For | 5m |
| Descripción | Cliente intentando conectar sin éxito. Posible token incorrecto. |
| Runbook | Revisar configuración del cliente. Verificar `AILAB_MCP_TOKEN`. |
| Acción prohibida | No rotar token, no cambiar firewall |
| Acción permitida | Notificar, revisar cliente |

---

## 8. Dashboard Grafana futuro

**Nombre:** `AI-LAB MCP Control Plane`

### Paneles propuestos

| # | Panel | Métrica origen | Tipo |
|---|---|---|---|
| 1 | MCP endpoints up | `ailab_mcp_up` | Stat |
| 2 | Requests por endpoint | `rate(ailab_mcp_requests_total[5m])` | Time series |
| 3 | Auth failures 8092 | `rate(ailab_mcp_auth_failures_total[5m])` | Time series |
| 4 | Tool calls por tool | `rate(ailab_mcp_tool_calls_total[5m])` | Bar chart |
| 5 | Tool errors por tool | `rate(ailab_mcp_tool_errors_total[5m])` | Bar chart |
| 6 | Tool latency p50/p95 | `histogram_quantile(0.5/0.95, ...)` | Time series |
| 7 | Métodos MCP | `rate(ailab_mcp_requests_total[5m]) by (method)` | Pie chart |
| 8 | Initialize/list activity | `rate(ailab_mcp_initialize_total[5m])` | Stat |
| 9 | MCP SLO status | Resultado de SLOs | Table |
| 10 | Last successful calls | Max timestamp de tool calls | Table |
| 11 | Security posture | `ailab_mcp_endpoint_info` | Status grid |
| 12 | Runbook links | Enlaces a documentación | Markdown |

---

## 9. Logging seguro

### Permitido en logs

```
timestamp
endpoint (8091/8092)
service (semantic/lan)
tool_name
method
status (success/error/auth_failed)
duration_ms
error_class (genérica, sin stacktrace completo)
client_type (opencode/lmstudio/unknown) si se puede inferir sin datos personales
```

### Prohibido en logs

```
token
Authorization header
prompt completo
query completa de ailab_memory_search
payload completo
memory raw result
stacktrace completo con secretos
IP completa del cliente salvo diagnóstico explícito
```

---

## 10. Tests futuros obligatorios

| Test | Descripción |
|---|---|
| `test_mcp_metrics_endpoint_exists` | Verificar que `/metrics` responde 200 |
| `test_mcp_metrics_no_token_leak` | Métricas no contienen token |
| `test_mcp_metrics_labels_bounded` | Labels solo las permitidas |
| `test_mcp_tool_call_counter` | Tool call incrementa counter |
| `test_mcp_auth_failure_counter` | Auth failure incrementa counter |
| `test_mcp_latency_histogram` | Latencia registrada correctamente |
| `test_mcp_no_prompt_payload_in_metrics` | Prompt no aparece en métricas |
| `test_mcp_8091_8092_endpoint_labels` | Labels endpoint correctas |
| `test_mcp_dashboard_json_valid` | Dashboard JSON válido |
| `test_mcp_alert_rules_promtool_valid` | Reglas de alerta válidas con promtool |

---

## 11. No-go list

| Prohibición | Razón |
|---|---|
| Token en métricas o logs | Riesgo de seguridad crítico |
| Prompt completo en métricas o logs | Datos del usuario |
| IP completa sin agregación | Privacidad |
| Stacktrace completo con secretos | Exposición de código |
| Restart automático en alertas | Mutabilidad no permitida |
| Rotación automática de token | Riesgo de dejar a clientes sin acceso |
| Cambio automático de firewall | Bloquear clientes legítimos |
| Deploy automático | Sin CI/CD para MCP |
| Métricas con cardinalidad ilimitada | Proteger Prometheus |
| Labels dinámicas por tool name desconocido | Cardinalidad descontrolada |

---

## 12. Contrato de implementación futura

**Fase:** `AI-LAB-MCP-OBSERVABILITY-METRICS-IMPLEMENTATION-01`

### Condiciones

1. Modificar solo `mcp/runtime-mcp/`.
2. No tocar `/mnt/mcp_server`.
3. No cambiar systemd.
4. No reiniciar servicios.
5. Tests unitarios obligatorios.
6. Secret scan obligatorio.
7. `promtool` check si hay reglas de alerta.
8. Dashboard JSON validado si se crea.
9. Dry-run sync antes de tocar `/mnt/mcp_server`.
10. Rollback plan antes del sync.

### Archivos a modificar (estimado)

| Archivo | Cambio |
|---|---|
| `mcp/runtime-mcp/server.py` | Añadir endpoint `/metrics`, registrar métricas |
| `mcp/runtime-mcp/lan_server.py` | Añadir endpoint `/metrics`, auth wrapper |
| `mcp/runtime-mcp/tools/__init__.py` | Wrapper de métricas para tools |
| `mcp/runtime-mcp/tools/metrics.py` | (nuevo) Definición de métricas Prometheus |
| `tests/` | Tests de métricas |

### Fases futuras sugeridas

| Fase | Descripción |
|---|---|
| `AI-LAB-MCP-OBSERVABILITY-METRICS-IMPLEMENTATION-01` | Implementar métricas en `mcp/runtime-mcp/` |
| `AI-LAB-MCP-OBSERVABILITY-METRICS-PUSH-01` | Publicar implementación |
| `AI-LAB-MCP-RUNTIME-SNAPSHOT-SYNC-DRY-RUN-02` | Validar sync sin cambios |
| `AI-LAB-MCP-RUNTIME-SNAPSHOT-SYNC-APPLY-01` | Aplicar cambios a `/mnt/mcp_server` |
| `AI-LAB-MCP-GRAFANA-DASHBOARD-SPEC-01` | Spec específica de dashboard |
| `AI-LAB-MCP-PROMETHEUS-RULES-SPEC-01` | Spec específica de reglas Prometheus |

---

## 13. Siguientes fases recomendadas

| Fase | Descripción |
|---|---|
| `AI-LAB-MCP-OBSERVABILITY-METRICS-SPEC-PUSH-01` | Publicar esta spec |
| `AI-LAB-MCP-OBSERVABILITY-METRICS-IMPLEMENTATION-01` | Implementar métricas en `mcp/runtime-mcp/` |
| `AI-LAB-MCP-CONTRACT-TESTS-01` | Tests de contrato MCP (read-only) |
