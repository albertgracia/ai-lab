# AI-LAB-NOC-CRITICAL-DEGRADED-TRIAGE-01

## Resultado: PARTIAL
## Clasificacion: B + D

Degradacion real parcial, esperada en la capa de inferencia porque el backend no esta iniciado, pero con una capa adicional de diagnostico incompleto por divergencia entre snapshot/sensores/grounding.

---

## 1) Preflight git y estado base

- HEAD: `6cc8570d`
- Branch: `main...origin/main`
- Working tree: limpio antes de crear este informe
- Sync con origin/main: si, alineado
- Log reciente:
  - `6cc8570d docs(audit): record ci metrics sync`
  - `ef9a9efb merge: integrate remote public metrics after post-astro smoke`
  - `471e6c1a docs(audit): record post-astro runtime smoke`
  - `f386ac98 chore: update public metrics [skip ci]`
  - `bbc71bb3 docs(audit): record sr-only css fix push`

---

## 2) Servicios systemd

### Failed units

- `systemctl --failed`: ninguno

### Servicios AI-LAB activos

- `ailab-docs.service` active/running
- `ailab-gateway.service` active/running
- `ailab-heartbeat.service` active/running
- `ailab-live-api.service` active/running
- `ailab-live-state.service` active/running
- `ailab-mcp-semantic-gateway.service` active/running
- `ailab-metrics.service` active/running
- `ailab-router.service` active/running
- `ailab-runner.service` active/running
- `gitnexus.service` active/running

### Lectura

No hay unidades failed. La base de servicios esta sana.

---

## 3) Docker y contenedores relevantes

### Activos

- `traefik` -> `80/443/8080`
- `promtail` -> `1514`
- `grafana` -> `3001->3000` (healthy)
- `qdrant` -> `6333-6334`
- `portainer` -> `9000`

### Observacion

No se arrancaron ni detuvieron contenedores. Los servicios AI-LAB principales son systemd, no contenedores.

---

## 4) Health HTTP read-only

| Endpoint | Resultado |
|---|---|
| `http://127.0.0.1:8008/health` | `200` |
| `http://127.0.0.1:8083/health` | `200` |
| `http://127.0.0.1:8084/health` | `404` |
| `http://127.0.0.1:4322/` | `200` |
| `http://127.0.0.1:4747/` | `200` |
| `http://127.0.0.1:6333/collections` | `200` |
| `http://127.0.0.1:8091/health` | `404` |
| `http://127.0.0.1:9090/-/ready` | no responde localmente |
| `http://127.0.0.1:3001/api/health` | `200` |

### Lectura

- Gateway y router estan vivos.
- Live-API existe y responde por endpoints de estado/memoria, pero no expone `GET /health`.
- MCP semantic gateway esta activo, pero `GET /health` no esta expuesto.
- GitNexus responde en `:4747`.
- Qdrant responde `200`.
- Grafana esta activo en `:3001`, no en `:3000` local.

---

## 5) Runtime unavailable / timeout

### Gateway y router

- `GET /v1/models` en gateway: timeout al proxy hacia `192.168.1.50:1234/v1/models`
- `GET /v1/models` en router: devuelve `200` con modelos del router (`auto`, `fast`, `reasoning`, `coding`)
- `GET /runtime/health/summary` en gateway: `404` / no disponible
- `GET /runtime/health/summary` en router: `404`
- `GET /runtime/health/summary` en live-api: `404`

### Conclusion operativa

El timeout de runtime no viene de una caida del gateway ni del router. El gateway esta levantado, pero el proxy al backend de inferencia expira.

---

## 6) Backend de inferencia

### Evidencia de apagado/ausencia

- `ss -ltnp` no muestra escucha en `192.168.1.50:1234` desde este host.
- `ps aux` no muestra procesos tipo `lm studio`, `ollama`, `llama`, `vllm`, `kobold` o `text-generation` ejecutandose localmente.
- `gateway /v1/models` devuelve timeout conectando a `192.168.1.50:1234`.

### Interpretacion

El backend de inferencia esta efectivamente **no iniciado** desde la perspectiva del runtime consultado. Esto cuadra con la operacion esperada del operador: no arrancarlo hasta que haga falta.

---

## 7) Snapshot / sensores / operador unknown

### Evidencia de snapshot vivo

- `runtime/state/snapshots/snap-1779055575/` existe.
- `_meta.json` indica snapshot manual con `current_mode.json`, `cluster_state.json` y `routing_history.jsonl`.
- `runtime/sensors` responde `200` y entrega snapshot fresco.

### Datos clave del snapshot vivo

- `topology_mode`: `degraded_single_gpu`
- `active_gpus`: `RX9070` online
- `inventory_gpus`: `RX7900XT` offline esperado
- `missing_sources`: `lmstudio_models`
- `unexpected_down_targets`: `ai-lab-gateway`
- `freshness`: `0.0s ago` para gateway/router/live_api/control_plane/containers/docker/system_node/smartctl/windows_exporters/unifi/cloudflare_tunnel

### Problema detectado

- `GET /runtime/grounding` falla con:
  - `name 'UNKNOWN_STATE_TOKENS' is not defined`

### Lectura

El estado `unknown` del operador no se explica por falta de snapshot. El snapshot existe y esta fresco. La causa mas probable es una combinacion de:

- bug en la ruta de grounding/reporting
- falta del source `lmstudio_models`
- discrepancia entre fuentes de salud (`runtime.health` vs `runtime.sensors` vs Prometheus)

---

## 8) Prometheus y metricas

### Disponibilidad

- Prometheus local `127.0.0.1:9090`: no disponible
- Prometheus de observabilidad `192.168.1.40:9090`: disponible

### Metricas vivas consultadas

| Metrica | Valor |
|---|---:|
| `ailab_runtime_errors_total` | `1` (`UPSTREAM_TIMEOUT`) |
| `ailab_runtime_timeout_total` | `1` (`connect`) |
| `ailab_cognitive_health_score` | `0` |
| `ai_lab:runtime_health_score` | `1` |
| `ailab_runtime_slo_state` | `0` |
| `ailab_slo_violations_total` | `102` |
| `ailab_runtime_degradation_level` | `0` |

### Lectura

- El score cognitivo/runtime del gateway esta en `0`.
- El recording rule de infraestructura `ai_lab:runtime_health_score` sigue en `1` (salud infra correcta).
- La degradacion que ve el NOC es **real** para la capa cognitiva/runtime, pero **no** representa una caida infra global.

---

## 9) Incidentes

### Activos

- **Crítico**: `codebase`
- **Altos**: `validation`, `authority`
- **Medio**: `infrastructure`

### Lectura operativa

- `codebase`: riesgo estructural alto y blast radius amplio.
- `validation`: gates bloqueados e invariantes fallidas.
- `authority`: freshness unavailable y gaps de prometheus targets.
- `infrastructure`: nodo discoverable huérfano.

### Conclusión

Los incidentes son coherentes con un runtime degradado parcial y con una capa de autoridad/validacion no completamente estable.

---

## 10) Clasificacion operativa

### Categoria final

- **B) Degradacion real parcial**
- con un componente **D) Diagnostico incompleto** por bug de grounding/reporting

### Por que no es C (incidente real infra)

- gateway activo
- router activo
- live-api activo
- docs activo
- metrics activo
- MCP y GitNexus activos
- Qdrant activo
- no hay failed units
- no hay caida general de infraestructura

### Por que no es A puro (solo esperado/controlado)

- el runtime ya registra timeout y SLO critical actuales
- `runtime.health` y `ailab_runtime_slo_state` estan en estado degradado real
- hay incidentes activos en authority/validation/codebase

---

## 11) Riesgo real actual

1. Capa cognitiva/runtime degradada (score 0)
2. Inference backend no iniciado (esperado, pero impacta el estado NOC)
3. Validation bloqueada
4. Authority con freshness unavailable
5. Codebase con riesgo estructural alto
6. Observabilidad con salud 53.6/100 y target alignment 50%

---

## 12) Acciones recomendadas

1. Mantener la inferencia parada si no hace falta operarla.
2. Revisar y corregir `runtime/grounding` (`UNKNOWN_STATE_TOKENS` no definido).
3. Revisar la discrepancia entre `runtime.health`, `runtime.sensors` y Prometheus.
4. Seguir el incidente de `validation` antes de cualquier cambio mayor.
5. Seguir el incidente de `authority` para restaurar freshness completa.
6. Tratar `codebase` como riesgo estructural, no como outage.

---

## 13) Que no se hizo

- No se inicio backend de inferencia.
- No se reinicio Gateway.
- No se reinicio Router.
- No se reinicio Live API.
- No se reinicio GitNexus.
- No se reinicio Qdrant.
- No se reinicio Prometheus/Grafana.
- No se toco Docker.
- No se modifico configuracion.
- No se modifico codigo.
- No se hizo `git add`.
- No se hizo `push`.
- No se creo tag.

---

## 14) Conclusion

AI-LAB esta vivo y los servicios base estan arriba. La degradacion que ve el NOC es real para la capa cognitiva/runtime, pero es en gran parte compatible con el backend de inferencia apagado de forma esperada. El estado `unknown` del operador no viene de ausencia de snapshot: el snapshot existe y esta fresco. El problema mas claro adicional es un bug en la ruta de grounding/reporting que impide consolidar el estado operacional con precision.

*Fin del informe - 31/05/2026*
