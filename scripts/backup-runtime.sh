#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/opt/ai-lab"
ARCHIVE_ROOT="/mnt/opencode/ai-lab-archives"
EXCLUDES_FILE="$ROOT_DIR/.backup-excludes"
BACKUP_DIR="$ARCHIVE_ROOT/runtime-history/auto-$(date +%Y-%m-%d-%H%M%S)"
export BACKUP_DIR

python3 - <<'PY'
from runtime.storage.archive_manager import create_archive_layout, validate_backup_targets

create_archive_layout()
result = validate_backup_targets(["/opt/ai-lab/runtime/state", "/opt/ai-lab/config"], "/mnt/opencode/ai-lab-archives/runtime-history")
if not result.valid:
    raise SystemExit("storage policy validation failed: " + "; ".join(result.errors))
PY

mkdir -p "$BACKUP_DIR/runtime-states"

# Runtime state files
cp "$ROOT_DIR/runtime/state/cluster_state.json" "$BACKUP_DIR/runtime-states/" 2>/dev/null || true
cp "$ROOT_DIR/runtime/state/episodic_memory.jsonl" "$BACKUP_DIR/runtime-states/" 2>/dev/null || true
cp "$ROOT_DIR/runtime/state/governance_audit.jsonl" "$BACKUP_DIR/runtime-states/" 2>/dev/null || true
cp "$ROOT_DIR/runtime/state/discovered_nodes.json" "$BACKUP_DIR/runtime-states/" 2>/dev/null || true
cp "$ROOT_DIR/runtime/state/gateway_metrics.json" "$BACKUP_DIR/runtime-states/" 2>/dev/null || true
cp "$ROOT_DIR/runtime/state/system_snapshot.json" "$BACKUP_DIR/runtime-states/" 2>/dev/null || true

# Config
cp "$ROOT_DIR/config/inference_nodes.json" "$BACKUP_DIR/" 2>/dev/null || true

# Git status
cd "$ROOT_DIR" && git log --oneline -10 > "$BACKUP_DIR/git-log.txt" 2>/dev/null || true

# Size
echo "Backup: $(date)" > "$BACKUP_DIR/manifest.txt"
du -sh "$BACKUP_DIR" >> "$BACKUP_DIR/manifest.txt"
printf "Excludes: %s\n" "$EXCLUDES_FILE" >> "$BACKUP_DIR/manifest.txt"
printf "Deprecated local backup dir: /opt/ai-lab/backups\n" >> "$BACKUP_DIR/manifest.txt"

python3 - <<'PY'
from runtime.storage.archive_manager import build_archive_manifest, estimate_backup_size, load_backup_excludes, write_archive_manifest
import os

backup_dir = os.environ["BACKUP_DIR"]
excludes = load_backup_excludes()
size_report = estimate_backup_size([backup_dir], excludes)
manifest = build_archive_manifest(
    source_paths=[backup_dir],
    excluded_paths=size_report["excluded_matches"],
    size_before_bytes=size_report["size_before_bytes"],
    size_after_bytes=size_report["estimated_archive_bytes"],
    recursive_detected=False,
    moved_to=backup_dir,
)
write_archive_manifest(manifest)
PY

echo "Backup completed: $BACKUP_DIR"
