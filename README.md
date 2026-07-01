# AI-LAB
## Local-First Distributed Cognitive Infrastructure

AI-LAB es una plataforma cognitiva operacional local-first diseñada para homelab,
inferencia distribuida y automatización inteligente de infraestructura.

> **Checkpoint:** CP-40A-POST-RELEASE-SLO-DRIFT-WATCH-01-STABLE
> **HEAD:** 0f5e3ab8
> **Estado:** OPERATIVO Y ESTABLE
> **Runtime Generation:** FASE 40A
> **Tags:** 113 (Blocks 21-40 completados)

---

## Identidad del Runtime

| Campo | Valor |
|-------|-------|
| Host principal | 192.168.1.30 |
| Hostname lógico | ubuntu-ialab |
| Runtime | AI-LAB Cognitive Runtime |
| Arquitectura | Gateway + Router + MCP LAN + Observabilidad |
| Modelos activos | 3 (llama-3.1-8b, qwen2.5-coder-14b, nomic-embed) |
| GitNexus | 26728 símbolos, 42257 relaciones |

---

## Arquitectura

```
Cliente (OpenCode / OpenWebUI)
  ↓
Gateway (:8008)    ← OpenAI-compatible, routing, SLO, governance
  ↓
Router (:8083)     ← Routing cognitivo, perfiles, replay
  ↓
MCP LAN (:8084)    ← Estado runtime, herramientas read-only
  ↓
LM Studio (:1234)  ← RX9070 (16GB)
  ├── llama-3.1-8b-instruct       → primary operational
  ├── qwen2.5-coder-14b-instruct  → primary coding
  └── nomic-embed-text-v1.5       → embeddings
```

**Modelo desactivado:** qwen3.6-27b (disponible en inventario, no rut cable).

---

## Servicios Core

| Servicio | Puerto | Función |
|----------|--------|---------|
| `ailab-gateway` | 8008 | API OpenAI-compatible (único entrypoint de chat) |
| `ailab-router` | 8083 | Routing cognitivo, perfiles, replay |
| `ailab-live-api` | 8084 | Estado runtime, topología, herramientas MCP |
| `ailab-docs` | 4322 | Portal documentación Astro |
| `ailab-metrics` | 3010 | Dashboard público Next.js SSR |
| `ailab-live-state` | — | Snapshot periódico de estado |
| `ailab-heartbeat` | — | Health signaling del cluster |
| `ailab-runner` | — | GitHub Actions self-hosted runner |

---

## GPU

| GPU | Host | VRAM | Estado | Rol |
|-----|------|------|--------|-----|
| AMD Radeon RX9070 | 192.168.1.50 | 16 GB | ✅ ONLINE | Active inference backend |
| RX7900XT | 192.168.1.60 | 20 GB | 📦 INVENTORY | Offline (nodo apagado) |

---

## Observabilidad

| Componente | Host | Puerto |
|------------|------|--------|
| Prometheus | 192.168.1.40 | 9090 |
| Grafana | 192.168.1.40 | 3000 |
| Loki | 192.168.1.40 | — |

- **100+** métricas `ailab_*` (perfiles, latencia TTFB, tools, memoria, calidad, streaming, GPU, SLO, planner, report grounding, lifecycle)
- **15** dashboards Grafana (AI Governance, Cognitive Profiles, Runtime Protection, GPU Telemetry, Memory, Streaming, Quality, Cold Starts, SLO Enforcement)
- **19** reglas de alerta activas (health=ok)

---

## Infrastructure Map

```
Hyper-V Host (NAS-N5: 192.168.1.200)
  +-- ubuntu-ialab (1.30)    → Runtime + Gateway + Router + Docs + Runner + Live API
  +-- ubuntu-server (1.40)   → Prometheus + Grafana + Loki + Cloudflare Tunnel
GPU Nodes
  +-- RX9070 (1.50)          → 16GB VRAM — Active Runtime (llama, qwen, nomic, qwen3.6)
  +-- RX7900XT (1.60)        → 20GB VRAM — Inventory (offline)
Storage
  +-- NAS-N5                 → Modelos, backups, datos persistentes
```

---

## API Endpoints

| Endpoint | Puerto | Descripción |
|----------|--------|-------------|
| Gateway | `:8008` | OpenAI-compatible, routing, SLO, governance |
| Router API | `:8083` | Routing cognitivo, perfiles, replay |
| Live API | `:8084` | Estado runtime, topología, herramientas MCP |
| SLO Health | `:8008/slo/health` | Estado SLO + violaciones |
| Runtime Maturity | `:8008/runtime/maturity` | Descriptor completo de madurez |
| Runtime Governance | `:8008/runtime/governance` | Estado de gobernanza |
| Runtime Topology | `:8008/runtime/topology` | Topología con failure domains |
| Runtime Precision | `:8008/runtime/precision` | Precisión operacional + confidence |

---

## Routing Cognitivo

| Route Family | Estado | Modelo |
|--------------|--------|--------|
| minimal | ✅ | llama-3.1-8b |
| observe | ✅ | llama-3.1-8b |
| cognitive | ✅ | qwen2.5-coder-14b |
| report | ✅ | qwen2.5-coder-14b |
| embeddings | ✅ | nomic-embed |

Routing 100% determinista: 48 greeting markers + heurística lightweight → llama fastpath.
9 QWEN_ESCALATION_REASONS → qwen. Sin leakage de `lmstudio-community`.

---

## Documentation

| Nivel | Documento | Descripción |
|-------|-----------|-------------|
| Level 1 | `AGENTS.md` | Runtime constitution, governance, estado actual, reglas operacionales |
| Level 2 | `docs/ARCHITECTURE.md` | Arquitectura del sistema, decisiones técnicas, ADRs |
| Level 3 | `docs/ROADMAP-2026.md` | Roadmap anual, fases planificadas, dependencias |
| Level 4 | `conversation-history.md` | Historial completo de sesiones, decisiones, next steps |

Ver `docs/DOCUMENTATION-HIERARCHY.md` para la jerarquía completa.

---

## Philosophy

**Local First:** Todo el runtime diseñado para ejecutarse local, privado, self-hosted y soberano. Sin dependencia de APIs externas.
