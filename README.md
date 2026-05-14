# AI-LAB
## Local-First Distributed Cognitive Infrastructure

AI-LAB es una plataforma cognitiva operacional local-first disenada para homelab, inferencia distribuida y automatizacion inteligente de infraestructura.

> Distributed Cognitive Runtime

Capaz de razonar sobre infraestructura, mantener memoria operacional, enrutar tareas cognitivas, coordinar workflows, ejecutar inferencia distribuida, aplicar governance y automatizar operaciones.

---

## Current Status — Phase 7: Production Stabilization

### System Services (systemd)

Todos los componentes del runtime se ejecutan como servicios systemd con autoarranque, restart automatico y limites de memoria:

| Service | Port | Description | Memory |
|---|---|---|---|
| `ailab-gateway` | 8008 | OpenAI-compatible Gateway con sanitizacion, rate limiting (30 req/min) y metricas Prometheus | 256M |
| `ailab-router` | 8083 | Cognitive Router API (FastAPI) con seleccion capability-aware | 256M |
| `ailab-live-state` | --- | Snapshots de estado del sistema cada 5s | 128M |
| `ailab-heartbeat` | --- | Cluster heartbeat cada 30s con exponential backoff | 128M |

**Failover:** El gateway prueba backends en orden: primario -> secundario -> terciario. Si un nodo falla, el trafico se redirige automaticamente al siguiente disponible.

**Exponential Backoff:** Nodos offline incrementan timeout progresivamente (5s -> 30s max). Tras 5 fallos consecutivos se saltan los checks.

### Health Monitoring

Sistema de monitorizacion de salud del cluster:

- Health checks HTTP contra cada nodo LM Studio
- Availability scoring basado en latencia y modelos disponibles
- Fallback chains por tipo de tarea (reasoning -> memory -> fast)
- Descubrimiento automatico de nodos y capacidades
- Heartbeat persistente con registro en memoria episodica

---

## GPU Inference Cluster

### Nodos Activos

| Node | VRAM | Role | Status |
|---|---|---|---|
| RX9070 | 16 GB | Multimodal + Fast Inference | Online |
| RX7900XT | 20 GB | Reasoning + Coding + Orchestration | Online |

### Observabilidad GPU

Cada nodo GPU expone metricas en tiempo real mediante:

- **windows_exporter** (puerto 9182): metricas WMI de GPU (memoria dedicada, compartida, committed, engine time)
- **GPU Metrics API** (puerto 9183): servidor HTTP PowerShell que lee sensores AMD via LibreHardwareMonitorLib

**Metricas disponibles:**

| Metrica | Descripcion |
|---|---|
| `gpu_temperature_celsius` | Temperatura GPU Core / Memory / HotSpot |
| `gpu_fan_speed_rpm` | Velocidad del ventilador |
| `gpu_clock_mhz` | Frecuencia Core / Memoria |
| `gpu_load_percent` | Carga 3D, Compute 0, Copy, GPU Core, GPU Memory |
| `gpu_power_watts` | Consumo energetico GPU Package |

---

## Observability Stack

Stack centralizado de observabilidad:

| Service | Port | Description |
|---|---|---|
| Prometheus | 9090 | Metricas y scraping de todos los nodos |
| Grafana | 3000 | Dashboards unificados (migrados desde nodo runtime) |
| Loki | 3100 | Logs centralizados |
| Promtail | --- | Log shipping desde contenedores y sistema |
| Cloudflare Tunnel | --- | Acceso seguro sin abrir puertos |

### Dashboards

| Dashboard | Source | Data |
|---|---|---|
| GPU AI Metrics | Prometheus | VRAM, temperatura, clocks, load, procesos, engine time de ambas GPUs |
| Node Exporter Full | Prometheus | Sistema Ubuntu (CPU, RAM, disco, red) |
| Cadvisor exporter | Prometheus | Contenedores Docker |
| Labrazahome - Logs | Loki | Logs centralizados |
| Labrazahome - Time-Series | Prometheus | Series temporales de infraestructura |
| UniFi | UniFi Poller | Access Points, Gateway, Switch |

---

## Persistence & Backup

- **Backup automatico:** Script `scripts/backup-runtime.sh` via cron diario a las 3AM
- **Archivos respaldados:** cluster state, memoria episodica, auditoria, metrica gateway, configuracion nodos
- **Retencion:** 7 dias rotativos
- **Snapshot historico:** Cada hito importante preserva runtime + config + systemd files

---

## Core Architecture

```text
User Request
    |
Intent Router (keyword-based intent classification)
    |
Context Loader (RAG + semantic memory + archivos core)
    |
Orchestrator (plan de orquestacion)
    |
Workflow Planner (blueprint de 5 pasos)
    |
Distributed Task Router (capability matching + fallback chains)
    |
Execution Coordinator (token-aware model selection)
    |
Inference Nodes (LM Studio en nodos GPU remotos)
    |
Memory + Audit + Governance
```

---

## Runtime Components

### Governance Runtime

| Profile | Purpose |
|---|---|
| sandbox | entorno experimental permisivo |
| pilot | governance reforzada |
| production | maxima seguridad (read-only, sin shell) |

### Distributed Workflow Engine

- Workflow planning en 5 pasos
- Distributed routing con capability matching
- Node scoring por disponibilidad y capacidad
- Fallback chains por tipo de tarea
- Execution trace persistence en memoria episodica

### Memory Architecture

- **Semantic Memory**: RAG con Qdrant + sentence-transformers + embeddings locales
- **Episodic Memory**: JSONL append-log de eventos cognitivos (routing, orchestration, governance, execution)

---

## Infrastructure Map (High-Level)

```
Hyper-V Host
  +-- ubuntu-ialab    (AI-LAB Runtime: gateway, router, heartbeat, live-state + 16 Docker containers)
  +-- ubuntu-server   (Observabilidad central: Prometheus, Loki, Grafana, Cloudflare Tunnel)
  +-- Windows Server  (Servicios auxiliares)

GPU Nodes (Windows)
  +-- RX9070          (16GB VRAM - Inferencia multimodal + rapida)
  +-- RX7900XT        (20GB VRAM - Razonamiento pesado + coding + orquestracion)

NAS / Storage
  +-- Storage server  (Modelos, backups, datos persistentes)
```

---

## CI/CD

Workflow GitHub Actions (`.github/workflows/deploy.yml`):

- **Trigger:** push a main
- **Jobs:** validate (syntax check) -> deploy (rsync + restart servicios)
- **Systemd files versionados** en `.github/systemd/`

---

## Hardening

| Medida | Detalle |
|---|---|
| Rate limiting | 30 requests/minuto por IP en gateway |
| Limite memoria | MemoryMax en cada servicio systemd |
| Ulimit | `fs.file-max = 65535` |
| Capability Guard | Bloqueo de comandos destructivos (rm -rf, mkfs, shutdown) |

---

## Git Infrastructure

Repository: `github.com/albertgracia/ai-lab`

Incluye:
- `runtime/` — codigo fuente del runtime cognitivo
- `config/` — configuracion de nodos y politicas
- `stacks/` — docker-compose de infraestructura
- `memory/` — ADRs, memoria semantica, roadmap
- `.agent/` — Antigravity Kit (20 agents, 38 skills, 11 workflows)
- `apps/` — Documentacion Astro + Starlight

---

## Philosophy

### Local First
Todo el runtime disenado para ejecutarse local, privado, self-hosted y soberano.

### Modular Architecture
Separacion explicita entre cognicion, memoria, ejecucion, governance, workflows y orquestracion.

### Incremental Cognitive Growth

```text
Infrastructure
    |
Knowledge
    |
Memory
    |
Governance
    |
Workflows
    |
Distributed Cognition
    |
Autonomous Operations
```

---

## Roadmap

### Phase 7 (Complete) — Production Stabilization
- Systemd services con autoarranque y watchdog
- Failover dinamico entre nodos de inferencia
- Observabilidad centralizada (Prometheus + Grafana + Loki)
- Monitorizacion GPU con temperatura, VRAM, load, procesos
- Backup automatico y persistencia
- Hardening: rate limiting, limites de memoria, ulimit
- CI/CD GitHub Actions

### Phase 8 — Autonomous Operations
- Autonomous remediation
- Operational reasoning
- Infrastructure cognition
- Adaptive workflows

### Phase 9 — Multi-Agent Coordination
- Specialized agents
- Distributed cognition mesh
- Cooperative reasoning
- Autonomous planning

---

## Final Objective

Construir una Local-First Operational Cognitive Platform capaz de razonar sobre infraestructura, mantener memoria persistente, coordinar agentes, ejecutar workflows, automatizar operaciones y operar como un verdadero AI Operations Brain.
