---
title: "FASE 18 — Professional Operations Runtime & Control Plane"
summary: "Evolucion de AI-LAB hacia una plataforma operacional profesional con control plane centralizado, health scoring, tool reliability, memory usefulness, governance v2, explainability y recovery."
order: 35
---

## FASE 18.1 — Runtime Control Plane

### Hito

Se creo el modulo `runtime/control/` que agrega estado operacional desde los modulos existentes (routing_history, cluster_state, mode_manager, health_score, Qdrant) sin duplicar logica. Se expone via 6 nuevos endpoints en la Live API (`:8084`).

### Endpoints nuevos

| Endpoint | Descripcion |
|---|---|
| `GET /api/control/runtime` | Status ultra-compacto (mode, health, nodes, latency, governance) |
| `GET /api/control/status` | Estado completo (runtime + uptime + Qdrant + nodos offline) |
| `GET /api/control/nodes` | Estado por nodo (online, modelos, latencia, tool_use) |
| `GET /api/control/routes` | Ultimas decisiones del router (modelo, nodo, task, latency, failover) |
| `GET /api/control/policies` | Politicas activas (execute_policy, observe_policy, tool_fastpath) |
| `GET /api/control/explain/last-route` | Explica la ultima decision de ruta (reason_codes, fallback) |

### Governance state

El endpoint `/api/control/runtime` incluye el campo `governance` con valores:

| Estado | Condicion |
|---|---|
| `NORMAL` | Sin bloqueos, Qdrant healthy, fallback_rate bajo |
| `ELEVATED` | >0 bloqueos en 1h o fallback_rate > 10% |
| `DEGRADED` | Qdrant degraded o tool parser failures > 5 |
| `LOCKDOWN` | >5 bloqueos en 1h + fallback_rate alto + Qdrant caido |

### Archivos

| Archivo | Accion |
|---|---|
| `runtime/control/__init__.py` | Nuevo |
| `runtime/control/control_plane.py` | Nuevo (~180 lineas) |
| `runtime/state/live_api.py` | Modificado (6 endpoints + handlers) |

### Verificacion

```bash
# Runtime compacto
curl -s http://192.168.1.30:8084/api/control/runtime

# Estado completo
curl -s http://192.168.1.30:8084/api/control/status

# Nodos
curl -s http://192.168.1.30:8084/api/control/nodes

# Ultimas rutas
curl -s http://192.168.1.30:8084/api/control/routes

# Politicas
curl -s http://192.168.1.30:8084/api/control/policies

# Explicacion de ultima ruta
curl -s http://192.168.1.30:8084/api/control/explain/last-route
```

### Proximas subfases

| # | Subfase | Estado |
|---|---|---|
| 18.2 | Model & Node Health Scoring | Pendiente |
| 18.3 | Tool Reliability Metrics | Pendiente |
| 18.4 | Memory Usefulness Engine | Pendiente |
| 18.5 | Governance Audit v2 | Pendiente |
| 18.7 | Recovery Manager | Pendiente |
| 18.8 | Professional Ops Dashboard `/ops/control` | Pendiente |
| 18.9 | Stability Validation Criteria | Pendiente |
