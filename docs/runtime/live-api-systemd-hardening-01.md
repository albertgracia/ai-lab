# Live API Systemd Hardening

## Objective
Formalize the AI-LAB Live API (port 8084) as a systemd-managed service.

## Service
- **Name:** ailab-live-api.service
- **Port:** 8084
- **Script:** runtime/state/live_api.py
- **Bind:** 0.0.0.0:8084 (LAN accessible - documented risk)
- **User:** albert
- **WorkingDirectory:** /opt/ai-lab
- **Restart:** always
- **MemoryMax:** 128M

## Endpoints
| Endpoint | Description |
|----------|-------------|
| /api/status.json | Docker containers + GPU status |
| /api/events | Event bus stream |
| /api/topology | Cluster node topology and connectivity |
| /api/history | Episodic memory history (404 - pending) |

## Relationship
The Live API is consumed by:
- ailab-metrics.service (Next.js dashboard, port 3010)
- ailab-docs.service (Astro docs portal, port 4322 via api proxy)

## Validation
`ash
systemctl status ailab-live-api.service
curl -sS http://127.0.0.1:8084/api/status.json
curl -sS http://127.0.0.1:8084/api/topology
`

## Rollback
`ash
sudo systemctl disable --now ailab-live-api.service
sudo rm -f /etc/systemd/system/ailab-live-api.service
sudo systemctl daemon-reload
`

## Phase Reference
LIVE-API-SYSTEMD-HARDENING-01 (2026-05-29)
