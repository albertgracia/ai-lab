---
title: Heartbeat Persistente AI-LAB
summary: Servicio persistente de monitorización distribuida del cluster AI-LAB
description: Servicio persistente de monitorización distribuida del cluster AI-LAB
pubDate: 2026-05-14
---

# Heartbeat Persistente AI-LAB

## Objetivo

Mantener estado vivo persistente del cluster distribuido AI-LAB.

---

# Servicio systemd

## Estado

```bash
sudo systemctl status ailab-heartbeat.service
```

## Arrancar

```bash
sudo systemctl start ailab-heartbeat.service
```

## Parar

```bash
sudo systemctl stop ailab-heartbeat.service
```

## Reiniciar

```bash
sudo systemctl restart ailab-heartbeat.service
```

---

# Logs

```bash
journalctl -u ailab-heartbeat.service -f
```

---

# Estado Persistente

Archivo principal:

```text
runtime/state/cluster_state.json
```

Memoria episódica:

```text
runtime/state/episodic_memory.jsonl
```

---

# Cluster Health States

| Estado | Significado |
|---|---|
| healthy | Todos los nodos online |
| degraded | Cluster parcialmente operativo |
| offline | Cluster no disponible |

---

# Funcionalidades

- Health checks reales
- Heartbeat persistente
- Availability scoring
- Failover routing
- Live rerouting
- Workflow degradation awareness
- Episodic memory logging
- Runtime state persistence

---

# Estado Actual

Phase 6 — Distributed Execution Coordination (in progress)
