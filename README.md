# AI-LAB
## Local-First Distributed Cognitive Infrastructure

AI-LAB es una plataforma cognitiva operacional local-first disenada para homelab,
inferencia distribuida y automatizacion inteligente de infraestructura.

> Distributed Cognitive Runtime v3 — Production Ready

---

## Current Status — v3.0 Production Ready

### FASE 7 — Production Stabilization (Completada)
- 7 servicios systemd con autoarranque y restart automatico
- Gateway OpenAI-compatible con rate limiting y failover
- Router API con routing capability-aware
- 8 dashboards Grafana + 16 metricas Prometheus
- Monitorizacion GPU (temperatura, VRAM, load, power)
- Backup automatico diario
- Startup script + cron @reboot

### FASE 8 — Realtime Cognitive Mesh (Completada)
- SSE Event Bus con 9 tipos de eventos
- ClusterHealth, EventStream, TopologyGraph en vivo
- Runtime Analytics Engine (health score 0-100, metricas agregadas)
- Endpoint `/api/analytics` con health, metrics, sessions, routing
- 5 documentos de arquitectura Phase 8

### CI/CD — Self-Hosted Runner (Completado)
- GitHub Actions runner auto-hosted en 192.168.1.30
- Servicio systemd `ailab-runner.service`
- Build automatico en cada push a `main`
- Blog publico via Cloudflare Pages
- Blog privado via runner local
- Sudo NOPASSWD limitado a `systemctl restart ailab-docs.service`

### ASTRO Portal — Contenido (Completado)
| Pagina | Descripcion |
|---|---|
| `/ops` | AI Operations Center con analytics, health score, eventos |
| `/status/live` | ClusterHealth + EventStream en tiempo real |
| `/status/topology` | Topologia interactiva del cluster |
| `/status/history` | Metricas agregadas, health score, evolucion |
| `/status/gpus` | GPU live telemetry (VRAM, temp, power) |
| `/status/models` | Modelos LM Studio + tabla de routing |
| `/ai-infrastructure` | Arquitectura tecnica completa |
| `/docs/*` | 20+ documentos de documentacion tecnica |

---

## Core Architecture

```text
Open WebUI (:3000)
    |
Router API (:8083)  ← routing capability-aware
    |
Gateway (:8008)     ← sanitizacion, failover, rate limiting
    |
LM Studio (:1234)   ← RX9070 (16GB) / RX7900XT (20GB)
    |
GPU Nodes
```

---

## API Endpoints

| Endpoint | Puerto | Descripcion |
|---|---|---|
| **Gateway** | `:8008` | OpenAI-compatible, sanitizacion, failover |
| **Router API** | `:8083` | Routing cognitivo, CORS, streaming |
| **Live API** | `:8084` | `/api/status.json`, `/api/topology`, `/api/events` |
| **Analytics API** | `:8084` | `GET /api/analytics` (health, metrics, sessions, routing) |

## AI-LAB Router — Routing de Modelos

| Endpoint | Modelo | Nodo | VRAM | Roll |
|---|---|---|---|---|
| `ailab-router/fast` | Llama 3.1 8B | RX9070 (1.50) | 16 GB | Respuestas rapidas |
| `ailab-router/coding` | Qwen 2.5 Coder 14B/32B | RX9070 / RX7900XT | 16-20 GB | Programacion |
| `ailab-router/reasoning` | Qwen 2.5 Coder 32B | RX7900XT (1.60) | 20 GB | Razonamiento pesado |
| `ailab-router/auto` | Seleccion automatica | — | — | Routing inteligente |

## Metricas Prometheus

14+ metricas: requests, streams, errores, latencia, sesiones concurrentes,
failovers, routing decisions, memory writes, bloqueos governance, rate limit hits.

## Dashboards Grafana (8)

Cognitive Runtime Core, Cluster Topology, Event Bus, AI Sessions,
Episodic Memory, AI Governance, Energy/Thermal, Runtime Historical Analytics.

## Servicios Systemd (7)

| Servicio | Funcion |
|---|---|
| `ailab-traefik` | Proxy inverso Traefik |
| `ailab-gateway` | Gateway OpenAI-compatible |
| `ailab-router` | Router API cognitivo |
| `ailab-live-state` | Snapshots de estado |
| `ailab-heartbeat` | Heartbeat del cluster |
| `ailab-live-api` | Live API (status, topology, SSE, analytics) |
| `ailab-docs` | Portal de documentacion Astro |
| `ailab-runner` | GitHub Actions self-hosted runner |

## CI/CD — Flujo de Publicacion

```
git push origin main
    |
    +-- Cloudflare Pages     → ai-lab.labrazahome.com (1-2 min)
    |
    +-- Self-Hosted Runner   → npm run build + restart (20s)
                              → blog-ai-lab.labrazahome.com
```

---

## Pendiente / Proximos pasos

| Prioridad | Tarea | Estado |
|---|---|---|
| 🔴 | Pagina `/projects` con 8 proyectos detallados | Pendiente |
| 🟡 | Pagina `/experiments` con benchmarks GPU | Pendiente |
| 🟡 | Blog tecnico: 3+ articulos nuevos | Pendiente |
| 🟢 | Pagina `/status/events` - timeline de eventos | Pendiente |
| 🟢 | Pagina `/infra` - inventario de infraestructura | Pendiente |
| 🟢 | Contenido para landing page y SEO | Pendiente |
| 🟢 | Dark mode refinements | Pendiente |

---

## Infrastructure Map

```
Hyper-V Host (NAS-N5: 192.168.1.200)
  +-- ubuntu-ialab (1.30)    → Runtime + Gateway + Router + Docs + Runner
  +-- ubuntu-server (1.40)   → Prometheus + Grafana + Loki + Tunnel
GPU Nodes
  +-- RX9070 (1.50)          → 16GB VRAM — LM Studio (Llama, Qwen)
  +-- RX7900XT (1.60)        → 20GB VRAM — LM Studio (Qwen 32B)
Storage
  +-- NAS-N5                 → Modelos, backups, datos persistentes
```

---

## Philosophy

Local First: Todo el runtime disenado para ejecutarse local, privado,
self-hosted y soberano. Sin dependencia de APIs externas.
