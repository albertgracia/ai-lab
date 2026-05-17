---
title: "FASE 17 - Observabilidad y Gobernanza Prometheus"
summary: "Integracion de observabilidad nativa en el runtime: contadores prometheus_client para HARD_FACTS, peticiones al router y bloqueos de politica con desglose por razon. Endpoint /metrics en router, target en Prometheus y dashboard en Grafana."
order: 34
---

## Hito

Se integro `prometheus_client` en el runtime de AI-LAB para exponer metricas de gobernanza y actividad cognitiva. Prometheus scrapea tanto el gateway (`:8008`) como el router (`:8083`). Grafana muestra 3 paneles en tiempo real.

## Alcance implementado

- `runtime/telemetry/prometheus_metrics.py` — 4 contadores (2 sin labels, 1 con label `reason`)
- `runtime/llm/router_api.py` — endpoint `/metrics` (FastAPI) + instrumentacion de 3 contadores
- `runtime/gateway/openai_gateway.py` — instrumentacion de bloqueos con ambos contadores
- `runtime/state/runtime_state.py` — `get_runtime_state()` ahora lee `current_mode()` real

## Contadores

| Metrica | Labels | Se incrementa en |
|---|---|---|
| `ailab_router_chat_requests_total` | — | Cada peticion a `/v1/chat/completions` del router |
| `ailab_router_hard_facts_hits_total` | — | Cuando `build_system_context()` construye prompt con HARD_FACTS (modo `plan`/`build`/`execute`) |
| `ailab_governance_blocked_actions_total` | — | Cada comando peligroso interceptado (router + gateway) |
| `ailab_governance_blocked_actions_by_reason_total` | `reason` | Idem, con el marcador de peligro (`rm -rf`, `sudo`, `reboot`, etc.) |

## Por que dos contadores de bloqueo

`prometheus_client` no exporta contadores con labels hasta que se registra al menos un valor. El contador sin labels (`_total`) siempre esta visible (incluso en `0`), lo que permite que el stat panel de Grafana muestre `0` en verde en vez de "No data". El contador con labels (`_by_reason_total`) alimenta la grafica de desglose.

## Panel Grafana

Dashboard `AI-LAB · Panel de Gobernanza` (uid: `ailab-governance`, v6):

| Panel | Tipo | Query |
|---|---|---|
| Alertas de Seguridad Activas | stat | `sum(increase(ailab_governance_blocked_actions_total[1h]))` |
| Ratio de Trafico Hard Facts | stat (%) | `(sum(rate(ailab_router_hard_facts_hits_total[1m])) / sum(rate(ailab_router_chat_requests_total[1m])) * 100) or vector(0)` |
| Historico de Intercepciones | timeseries | `sum by (reason) (increase(ailab_governance_blocked_actions_by_reason_total[1m]))` |

El `or vector(0)` en el ratio evita "No data" cuando aun no hay suficientes scrapes en la ventana de 1 minuto.

## Infraestructura desplegada

| Componente | Detalle |
|---|---|
| Prometheus | `192.168.1.40:9090`, scrapea `192.168.1.30:8083/metrics` (job: `ai-lab-router`) y `:8008/metrics` (job: `ai-lab-gateway`) |
| Grafana | `192.168.1.40:3000`, datasource `Prometheus` (uid: `PBFA97CFB590B2093`) |
| Config Prometheus | `/home/albert/docker/monitorizacion/prometheus/config/prometheus.yml` en `.40` |
| Dashboard | importado via API con autenticacion basica |

## Pasos manuales ejecutados en .40

1. Anadido scrape target `ai-lab-router` en `prometheus.yml`
2. Recargado Prometheus: `docker exec prometheus kill -HUP 1`
3. Dashboard importado via `POST /api/dashboards/db` con `admin:19682507`

## Resultado

La gobernanza del runtime es observable en tiempo real. El panel muestra:
- `0` verde cuando no hay bloqueos, rojo cuando los hay
- Porcentaje de peticiones que activan HARD_FACTS
- Serie temporal con cada tipo de comando bloqueado
