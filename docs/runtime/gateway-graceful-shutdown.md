# Gateway Graceful Shutdown

## Problem

During `systemctl restart ailab-gateway` or `systemctl stop ailab-gateway`, systemd sends SIGTERM to the gateway process. Previously:

- New requests arriving during the shutdown window were accepted and processed, potentially being interrupted mid-flight.
- No signal in the `/health` endpoint indicated that the server was shutting down, so load balancers and monitoring had no visibility.
- No metric tracked rejected requests during shutdown.

## Solution

Implementación mínima sobre la infraestructura existente de FASE 29.0 (PID lock, signal handler, clean shutdown metric).

### Changes

**`runtime/gateway/openai_gateway.py`:**
- Added `_reject_if_shutting_down()` helper that returns 503 `{"error": "shutting_down", "message": "Server is shutting down. Retry later."}` when `_shutting_down` is `True`.
- `do_GET`: rejects all paths except `/health` during shutdown.
- `do_POST`: rejects all requests during shutdown.
- `do_OPTIONS`: rejects during shutdown.
- `/health`: reports `"status": "shutting_down"` and `"shutting_down": true` when flag is set (still returns HTTP 200 for monitoring accessibility).

**`runtime/telemetry/prometheus_metrics.py`:**
- New counter: `ailab_gateway_shutdown_rejections_total` — requests rejected during shutdown window.
- New function: `record_shutdown_rejection()`.

### Signals

| Signal | Handler | Behavior |
|--------|---------|----------|
| `SIGTERM` | `_handle_sigterm` | Sets `_shutting_down=true`, releases PID lock, records clean shutdown metric, calls `server.shutdown()`, exits with code 0 |
| `SIGINT` | `_handle_sigterm` | Same as SIGTERM |

### Expected Behavior During Shutdown

1. Systemd sends SIGTERM.
2. Signal handler sets `_shutting_down = True`.
3. New requests (GET except /health, POST, OPTIONS) receive HTTP 503.
4. `/health` responds with HTTP 200 and `"status": "shutting_down"`.
5. In-flight requests complete normally (ThreadingHTTPServer.shutdown waits for handler threads).
6. PID lock file is released.
7. Clean shutdown metric is recorded.
8. Process exits with code 0.
9. Systemd restarts the gateway (Restart=always).

### Validation

```bash
# Restart gateway
sudo systemctl restart ailab-gateway
sleep 3

# Verify health
curl -s http://127.0.0.1:8008/health | jq .

# Verify models
curl -s http://127.0.0.1:8008/v1/models | jq .

# Verify chat
curl -s http://127.0.0.1:8008/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "ailab-router/coding", "messages": [{"role": "user", "content": "Responde solo OK"}], "temperature": 0, "stream": false}' | jq .

# Verify shutdown rejection metric
curl -s http://127.0.0.1:8008/metrics | grep "ailab_gateway_shutdown_rejections"

# Verify shutdown logs
journalctl -u ailab-gateway -n 120 --no-pager | grep -i shutdown
```

### Test

```bash
cd /opt/ai-lab
.venv/bin/python tests/test_gateway_graceful_shutdown_38b.py
```

### Rollback

```bash
cd /opt/ai-lab
git checkout -- runtime/gateway/openai_gateway.py
git checkout -- runtime/telemetry/prometheus_metrics.py
git checkout -- tests/test_gateway_graceful_shutdown_38b.py
sudo systemctl restart ailab-gateway
```
