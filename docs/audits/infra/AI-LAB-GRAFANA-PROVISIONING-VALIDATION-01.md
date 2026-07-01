# AI-LAB-GRAFANA-PROVISIONING-VALIDATION-01

## Resultado: ✅ PASS (validación técnica)

---

## 1. Estado inicial Grafana

| Estado | Detalle |
|--------|---------|
| Container | `grafana` (grafana/grafana:12.0.2) |
| Estado inicial | **Exited (0) 13 days** |
| Puerto | **3001** (no 3000) |
| Admin password | `GF_SECURITY_ADMIN_PASSWORD` configurada |
| Volúmenes | `provisioning:/etc/grafana/provisioning:rw`, `data:/var/lib/grafana:rw` |

## 2. Acción tomada

`docker start grafana` — arrancó correctamente. No se modificó configuración.

## 3. Health Grafana

`GET /api/health` → 200 OK (database=ok, version=12.0.2). Web → 302 Found.

## 4. Datasource Prometheus

| Propiedad | Valor |
|-----------|-------|
| UID | PBFA97CFB590B2093 |
| URL | http://192.168.1.40:9090 |
| Access | proxy |

Test proxy Grafana→Prometheus: **OK** (18 series).

## 5. Prometheus ai-lab-gateway target

- `up{instance="192.168.1.30:8008"}` = **1** (UP) a las 00:50:17
- `scrape_duration_seconds` = **0.005s**
- `ailab_cognitive_health_score` = 0.0
- `ai_lab:runtime_health_score` = no existe como recording rule (pre-existente)

## 6. Dashboards cargados

5 dashboards sin errores de provisioning, JSON parse, datasource, duplicados o permisos.

## 7. Paneles nuevos

Overview (19 paneles): RHS Canónico, RHS Cross-check, Drift Indicator, Gateway Status, Routing Confidence, Nodes Online, Watchdog Triggers, SLO Gateway/LM Studio/Registry ✅

Runtime (15 paneles): RHS Historical, RHS Cross-check Historical, Drift Graph, Routing Confidence Historical, Nodes Online Historical, Latency p50/p95, Watchdog Rate, SLO Historical ✅

Cognitive Runtime (101 paneles): Todas las secciones (Federation, Evidence, Registry, LM Studio, SLO, Alerting, Triage, Graph Reasoning) ✅

## 8. Logs

Sin errores de dashboard/datasource/JSON. Solo warnings conocidos de Grafana 12.x (plugin table, directorios provisioning vacíos).

## 9. Validación visual

**Pendiente** — URL: http://192.168.1.30:3001 (admin / GF_SECURITY_ADMIN_PASSWORD)

## 10. Limitaciones

- `ai_lab:runtime_health_score` ausente en Prometheus (recording rule no desplegada).
- Alertas de `ai-lab-cognitive-alerts.yml` no cargadas por Prometheus.

## 11. Confirmaciones

No se modificó Gateway, Router, Prometheus, Loki, secretos, runtime/state, compose, ni dashboards.

## 12. Próxima fase

AI-LAB-HEALTH-SCORE-DRIFT-RULE-01
