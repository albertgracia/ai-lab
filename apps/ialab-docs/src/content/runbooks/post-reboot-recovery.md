---
title: "Post-Reboot Recovery"
summary: "Procedimiento de recuperacion tras reinicio del Hyper-V host."
order: 20
---

## Servicios Systemd (arrancan solos)

Los 6 servicios systemd arrancan automaticamente al iniciar la VM:
- ailab-gateway
- ailab-router
- ailab-live-state
- ailab-heartbeat
- ailab-live-api
- ailab-docs

## Stacks Docker (requieren verificacion)

```bash
# Verificar estado
docker ps --format "{{.Names}}\t{{.Status}}"

# Si Traefik no arranco:
cd /opt/ai-lab/stacks/traefik && docker compose up -d

# Si Prometheus no arranco (1.40):
ssh albert@192.168.1.40 "docker start prometheus"
```

## Verificacion Post-Reboot

```bash
# 1. Services
echo '19682507' | sudo -S systemctl is-active ailab-gateway ailab-router ailab-live-state ailab-heartbeat ailab-live-api ailab-docs

# 2. APIs
curl -s http://localhost:8008/health
curl -s http://localhost:8083/health

# 3. Traefik
docker ps --filter name=traefik --format "{{.Status}}"

# 4. Prometheus
curl -s http://192.168.1.40:9090/api/v1/targets | head -5
```
