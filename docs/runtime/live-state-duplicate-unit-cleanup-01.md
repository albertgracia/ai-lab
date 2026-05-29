# Live State Duplicate Unit Cleanup

## Problem
Two systemd services were running the same script (runtime/state/live_state.py)
simultaneously, creating duplicate workloads and wasting system resources.

## Services
| Service | Status | Details |
|---------|--------|---------|
| ailab-live-state.service | KEPT | Official, MemoryMax=128M, absolute path |
| ialab-live-state.service | REMOVED | Legacy, no MemoryMax, relative path |

## Cleanup Date
2026-05-29

## Backup
/mnt/ai-models/ai-lab/backups/systemd-units/ialab-live-state.service.20260529-132802.bak

## Validation
- Single live_state.py process confirmed
- All core services healthy
- 0 failed units

## Rollback
sudo cp /mnt/ai-models/ai-lab/backups/systemd-units/ialab-live-state.service.20260529-132802.bak /etc/systemd/system/ialab-live-state.service
sudo systemctl daemon-reload
