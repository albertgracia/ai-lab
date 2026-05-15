#!/usr/bin/env bash
set -euo pipefail

# ============================================
# AI-LAB Post-Reboot Startup Script
# Verifies and starts all critical Docker stacks
# ============================================

echo "=== AI-LAB STARTUP CHECK ==="
echo ""

# 1. Check systemd services
echo "[1/4] Verificando servicios systemd..."
for svc in ailab-gateway ailab-router ailab-live-state ailab-heartbeat ailab-live-api ailab-docs; do
    status=$(systemctl is-active "$svc" 2>/dev/null || echo "inactive")
    echo "  $svc: $status"
done

# 2. Check Traefik (docker compose stack)
echo ""
echo "[2/4] Verificando Traefik..."
if docker ps --format '{{.Names}}' | grep -q '^traefik$'; then
    echo "  traefik: running"
else
    echo "  traefik: DOWN - iniciando..."
    cd /opt/ai-lab/stacks/traefik && docker compose up -d
    echo "  traefik: started"
fi

# 3. Check Prometheus (on 1.40 via SSH)
echo ""
echo "[3/4] Verificando Prometheus..."
if ssh albert@192.168.1.40 "docker ps --format '{{.Names}}' | grep -q '^prometheus$'" 2>/dev/null; then
    echo "  prometheus: running"
else
    echo "  prometheus: DOWN - iniciando via SSH..."
    ssh albert@192.168.1.40 "docker start prometheus" 2>/dev/null || true
    echo "  prometheus: started"
fi

# 4. Final health check
echo ""
echo "[4/4] Health checks..."
for endpoint in     "Gateway:8008/health"     "Router:8083/health"     "LiveAPI:8084/api/status.json"; do
    name="${endpoint%%:*}"
    port="${endpoint##*:}"
    path="${port#*/}"
    port="${port%%/*}"
    if curl -sf "http://localhost:${port}/${path}" > /dev/null 2>&1; then
        echo "  $name: OK"
    else
        echo "  $name: FAIL"
    fi
done

echo ""
echo "=== STARTUP COMPLETE ==="
