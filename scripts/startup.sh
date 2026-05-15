#!/usr/bin/env bash
set -euo pipefail

# ============================================
# AI-LAB Post-Reboot Startup Script
# Verifies and starts all critical stacks
# ============================================

LOG_FILE="/opt/ai-lab/logs/startup.log"
mkdir -p /opt/ai-lab/logs

echo "=== AI-LAB STARTUP CHECK ===" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# 1. Check systemd services
echo "[1/4] Servicios systemd..." | tee -a "$LOG_FILE"
for svc in ailab-traefik ailab-gateway ailab-router ailab-live-state ailab-heartbeat ailab-live-api ailab-docs; do
    status=$(systemctl is-active "$svc" 2>/dev/null || echo "inactive")
    echo "  $svc: $status" | tee -a "$LOG_FILE"
done

# 2. Check Traefik (docker compose stack)
echo "" | tee -a "$LOG_FILE"
echo "[2/4] Verificando Traefik..." | tee -a "$LOG_FILE"
if docker ps --format '{{.Names}}' | grep -q '^traefik$' 2>/dev/null; then
    echo "  traefik: running" | tee -a "$LOG_FILE"
else
    echo "  traefik: DOWN - iniciando..." | tee -a "$LOG_FILE"
    cd /opt/ai-lab/stacks/traefik && docker compose up -d 2>&1 | tee -a "$LOG_FILE"
    echo "  traefik: started" | tee -a "$LOG_FILE"
fi

# 3. Check Prometheus (on 1.40 via SSH - if keyless auth available)
echo "" | tee -a "$LOG_FILE"
echo "[3/4] Verificando Prometheus..." | tee -a "$LOG_FILE"
if ssh -o BatchMode=yes -o ConnectTimeout=3 albert@192.168.1.40 "docker ps --format '{{.Names}}' | grep -q '^prometheus$'" 2>/dev/null; then
    echo "  prometheus: running (1.40)" | tee -a "$LOG_FILE"
elif ssh -o BatchMode=yes -o ConnectTimeout=3 albert@192.168.1.40 "docker start prometheus" 2>/dev/null; then
    echo "  prometheus: started (1.40)" | tee -a "$LOG_FILE"
else
    echo "  prometheus: SKIP (no passwordless SSH a 1.40)" | tee -a "$LOG_FILE"
fi

# 4. Health checks locales
echo "" | tee -a "$LOG_FILE"
echo "[4/4] Health checks locales..." | tee -a "$LOG_FILE"
for name in "Gateway:8008/health" "Router:8083/health" "Docs:4322"; do
    n="${name%%:*}"
    p="${name##*:}"
    if curl -sf "http://localhost:${p}" > /dev/null 2>&1; then
        echo "  $n: OK" | tee -a "$LOG_FILE"
    else
        echo "  $n: FAIL" | tee -a "$LOG_FILE"
    fi
done

echo "" | tee -a "$LOG_FILE"
echo "=== STARTUP COMPLETE ===" | tee -a "$LOG_FILE"
