#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/opt/ai-lab/backups/auto-$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR/runtime-states"

# Runtime state files
cp /opt/ai-lab/runtime/state/cluster_state.json "$BACKUP_DIR/runtime-states/" 2>/dev/null
cp /opt/ai-lab/runtime/state/episodic_memory.jsonl "$BACKUP_DIR/runtime-states/" 2>/dev/null
cp /opt/ai-lab/runtime/state/governance_audit.jsonl "$BACKUP_DIR/runtime-states/" 2>/dev/null
cp /opt/ai-lab/runtime/state/discovered_nodes.json "$BACKUP_DIR/runtime-states/" 2>/dev/null
cp /opt/ai-lab/runtime/state/gateway_metrics.json "$BACKUP_DIR/runtime-states/" 2>/dev/null
cp /opt/ai-lab/runtime/state/system_snapshot.json "$BACKUP_DIR/runtime-states/" 2>/dev/null

# Config
cp /opt/ai-lab/config/inference_nodes.json "$BACKUP_DIR/" 2>/dev/null

# Git status
cd /opt/ai-lab && git log --oneline -10 > "$BACKUP_DIR/git-log.txt" 2>/dev/null

# Size
echo "Backup: $(date)" > "$BACKUP_DIR/manifest.txt"
du -sh "$BACKUP_DIR" >> "$BACKUP_DIR/manifest.txt"

# Retain only last 7 backups
ls -dt /opt/ai-lab/backups/auto-* | tail -n +8 | xargs -r rm -rf

echo "Backup completed: $BACKUP_DIR"
