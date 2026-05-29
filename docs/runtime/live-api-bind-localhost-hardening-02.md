# Live API Bind Localhost Hardening

## Status
**PARTIAL** — bind change to 127.0.0.1 deferred.

## Current State
ailab-live-api.service binds on 0.0.0.0:8084 (all interfaces).

## Why Not Changed
- The bind address (HOST = " 0.0.0.0\) is hardcoded in runtime/state/live_api.py:12
- Traefik (Docker) proxies status/topology endpoints via http://192.168.1.30:8084
- Docker containers cannot reach host services on 127.0.0.1
- Changing to 127.0.0.1 without updating Traefik would break docs + metrics dashboards

## Consumers
| Consumer | How it reaches :8084 |
|----------|---------------------|
| Metrics dashboard (Next.js, local) | 127.0.0.1:8084 (local, safe) |
| Traefik proxy (Docker) | 192.168.1.30:8084 (LAN, would break) |

## Future Phase (LIVE-API-BIND-LOCALHOST-HARDENING-03)
1. Add environment variable support for HOST in live_api.py
2. Update Traefik dynamic configs to use host.docker.internal:8084 or 127.0.0.1:8084
3. Set HOST=127.0.0.1 via systemd environment
4. Validate all routes

## Risk
Private LAN only (192.168.1.0/24). Acceptable for current operational scope.
